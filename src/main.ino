// Inclusão de bibliotecas necessárias
#include <WiFi.h>        
#include <PubSubClient.h> 
#include <ArduinoJson.h> // Para formatar a mensagem MQTT como JSON
#include <DHT.h>
#include <stdlib.h>
#include <time.h>
#include "esp_timer.h"

// --- Configurações de Rede e MQTT ---
const char* SSID_WIFI = "Wokwi-GUEST"; 
const char* SENHA_WIFI = "";           

const char* BROKER_MQTT = "broker.hivemq.com"; 
const int PORTA_MQTT = 1883;
const char* ID_CLIENTE_MQTT = "agroirriga_esp32_rm562839"; 
const char* TOPICO_MQTT_SENSORES = "agroirriga/rm562839/sensores";

WiFiClient espClient;
PubSubClient clientMQTT(espClient);

// --- Definições dos Pinos ---
const int P_SENSOR_PIN = 13; 
const int K_SENSOR_PIN = 12; 
// LDR_PIN não é mais usado para leitura direta, pH é simulado a partir de ldr_valor_raw gerado
const int DHT_PIN = 18;      
#define DHTTYPE DHT22        
const int RELAY_PIN = 5;     

DHT dht(DHT_PIN, DHTTYPE);

// Variáveis globais dos sensores
bool fosforo_presente = false;
bool potassio_presente = false;
int ldr_valor_raw = 0; 
float ph_estimado = 7.0; 
float umidade_solo = 0.0; // Agora será explicitamente do DHT22
bool bomba_ligada = false; 

// Variáveis para simulação automática de P e K
bool sim_fosforo_state = false;
unsigned long sim_fosforo_last_eval_time = 0;
unsigned long sim_fosforo_current_state_duration = 0;

bool sim_potassio_state = false;
unsigned long sim_potassio_last_eval_time = 0;
unsigned long sim_potassio_current_state_duration = 0;

#define SIM_STATE_MIN_DURATION_MS 10000 
#define SIM_STATE_MAX_DURATION_MS 30000 

String comando_serial_recebido = ""; 

unsigned long getRandomDuration() {
  return random(SIM_STATE_MAX_DURATION_MS - SIM_STATE_MIN_DURATION_MS + 1) + SIM_STATE_MIN_DURATION_MS;
}

void conectarWiFi() {
  Serial.print("A ligar-se ao Wi-Fi: ");
  Serial.println(SSID_WIFI);
  WiFi.begin(SSID_WIFI, SENHA_WIFI);
  int tentativas = 0;
  while (WiFi.status() != WL_CONNECTED && tentativas < 20) {
    delay(500);
    Serial.print(".");
    tentativas++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWi-Fi ligado!");
    Serial.print("Endereço IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFalha ao ligar ao Wi-Fi.");
  }
}

void reconectarMQTT() {
  while (!clientMQTT.connected()) {
    Serial.print("A tentar ligação MQTT...");
    if (clientMQTT.connect(ID_CLIENTE_MQTT)) {
      Serial.println("MQTT ligado!");
    } else {
      Serial.print("falhou, rc=");
      Serial.print(clientMQTT.state());
      Serial.println(" Tentar novamente em 5 segundos");
      delay(5000);
    }
  }
}

void setupMQTT() {
  clientMQTT.setServer(BROKER_MQTT, PORTA_MQTT);
}

void setup() {
  Serial.begin(115200);
  Serial.println("AgroIrriga - v3.1 (MQTT com Umidade do Solo)");

  pinMode(P_SENSOR_PIN, INPUT); 
  pinMode(K_SENSOR_PIN, INPUT); 
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); 

  dht.begin();
  srand((unsigned int)esp_timer_get_time());

  sim_fosforo_state = random(2); 
  sim_fosforo_last_eval_time = millis();
  sim_fosforo_current_state_duration = getRandomDuration();

  sim_potassio_state = random(2); 
  sim_potassio_last_eval_time = millis();
  sim_potassio_current_state_duration = getRandomDuration();

  conectarWiFi(); 
  setupMQTT();    

  Serial.println("Sistema inicializado.");
  Serial.println("----------------------------------------------------");
}

void processarComandoSerial() {
  if (comando_serial_recebido.length() > 0) {
    Serial.print("Comando serial recebido: "); 
    Serial.println(comando_serial_recebido);
    if (comando_serial_recebido.equalsIgnoreCase("LIGAR_BOMBA")) {
      bomba_ligada = true;
      Serial.println("INFO: Comando Serial -> LIGAR BOMBA");
    } else if (comando_serial_recebido.equalsIgnoreCase("DESLIGAR_BOMBA")) {
      bomba_ligada = false;
      Serial.println("INFO: Comando Serial -> DESLIGAR BOMBA");
    } else {
      Serial.print("Comando serial desconhecido: ");
      Serial.println(comando_serial_recebido);
    }
    digitalWrite(RELAY_PIN, bomba_ligada ? HIGH : LOW);
    comando_serial_recebido = ""; 
  }
}

void publicarDadosMQTT() {
  if (!clientMQTT.connected()) {
    return; 
  }

  JsonDocument docJson; 
                        
  
  docJson["cod_sensor_ph"] = "PH_SIM_WOKWI_01"; 
  docJson["ph_estimado"] = ph_estimado;
  docJson["cod_sensor_nutri"] = "NUTRI_SIM_WOKWI_01"; 
  docJson["fosforo_presente"] = fosforo_presente;
  docJson["potassio_presente"] = potassio_presente;
  
  if (umidade_solo >= 0) { // Envia umidade do solo se a leitura for válida
    docJson["cod_sensor_umidade"] = "UMID_DHT22_WOKWI_01"; // Novo identificador
    docJson["umidade_solo"] = umidade_solo;
  } else {
    docJson["umidade_solo"] = nullptr; 
  }
  // docJson["bomba_ligada"] = bomba_ligada; // Opcional: enviar estado da bomba também

  char bufferJson[256]; // Aumentar se o JSON for maior
  size_t n = serializeJson(docJson, bufferJson);

  if (clientMQTT.publish(TOPICO_MQTT_SENSORES, bufferJson, n)) {
    Serial.print("Dados dos sensores publicados via MQTT no topico: ");
    Serial.println(TOPICO_MQTT_SENSORES);
    Serial.println(bufferJson);
  } else {
    Serial.println("Falha ao publicar dados via MQTT.");
  }
}

void loop() {
  unsigned long current_time = millis();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi desligado. A tentar reconectar...");
    conectarWiFi(); 
  }

  if (!clientMQTT.connected() && WiFi.status() == WL_CONNECTED) {
    reconectarMQTT(); 
  }
  clientMQTT.loop(); 

  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') { 
      processarComandoSerial();
    } else {
      comando_serial_recebido += c;
    }
  }

  if (current_time - sim_fosforo_last_eval_time >= sim_fosforo_current_state_duration) {
    sim_fosforo_state = random(2); 
    sim_fosforo_last_eval_time = current_time;
    sim_fosforo_current_state_duration = getRandomDuration();
  }
  if (current_time - sim_potassio_last_eval_time >= sim_potassio_current_state_duration) {
    sim_potassio_state = random(2); 
    sim_potassio_last_eval_time = current_time;
    sim_potassio_current_state_duration = getRandomDuration();
  }
  
  bool p_botao_pressionado = (digitalRead(P_SENSOR_PIN) == LOW);
  bool k_botao_pressionado = (digitalRead(K_SENSOR_PIN) == LOW);

  fosforo_presente = sim_fosforo_state || p_botao_pressionado;
  potassio_presente = sim_potassio_state || k_botao_pressionado;

  ldr_valor_raw = random(3001) + 500; 
  ph_estimado = map(ldr_valor_raw, 0, 4095, 0.0, 14.0);

  // Leitura da Umidade do Solo do DHT22
  umidade_solo = dht.readHumidity();
  if (isnan(umidade_solo)) {
    umidade_solo = -1; // Indica erro, mas não polui o serial principal aqui
  }

  publicarDadosMQTT();

  // Exibição dos Dados no Serial local (para debugging)
  Serial.println("--- Leitura Atual dos Sensores Locais (publicada via MQTT) ---");
  Serial.print("Fosforo (P): "); Serial.println(fosforo_presente ? "Presente" : "Ausente");
  Serial.print("Potassio (K): "); Serial.println(potassio_presente ? "Presente" : "Ausente");
  Serial.print("Valor Raw LDR (Simulado): "); Serial.println(ldr_valor_raw);
  Serial.print("pH Estimado (do LDR Simulado): "); Serial.println(ph_estimado, 1);
  Serial.print("Umidade do Solo (DHT22): "); // Atualizado para refletir a fonte
  if (umidade_solo >= 0) {
    Serial.print(umidade_solo, 1); Serial.println("%");
  } else {
    Serial.println("Erro de leitura DHT");
  }
  Serial.print("Estado Atual da Bomba (controlado via Serial): "); 
  Serial.println(bomba_ligada ? "LIGADA" : "DESLIGADA");
  Serial.println("----------------------------------------------------");

  delay(10000); 
}
