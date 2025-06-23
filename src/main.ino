// --- Bibliotecas ---
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h> // Para o Display LCD
#include <DHT.h>               // Para o sensor de umidade

// --- Configurações de Hardware ---
// Otimização: Usar uint8_t para números de pino, pois são valores pequenos (0-255)
const uint8_t DHTPIN = 18;
const uint8_t RELAY_PIN = 5;
const uint8_t LDR_PIN = 17; //  Pino do LDR conforme diagram.json
const uint8_t BTN_P_PIN = 12; // Simula sensor de Fósforo (P)
const uint8_t BTN_K_PIN = 13; // Simula sensor de Potássio (K)

// --- Configurações de Sensores e LCD ---
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);
LiquidCrystal_I2C lcd(0x27, 16, 2); // Endereço I2C 0x27, 16 colunas, 2 linhas

// --- Configurações de Rede e MQTT ---
const char* SSID_WIFI = "Wokwi-GUEST";
const char* SENHA_WIFI = "";
const char* BROKER_MQTT = "broker.hivemq.com";
const int PORTA_MQTT = 1883;
const char* TOPICO_MQTT_SENSORES = "agroirriga/rm562839/sensores";
const char* ID_CLIENTE_MQTT = "esp32_farmtech_rm562839_fase4";

// --- Clientes de Conexão ---
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// --- Variáveis Globais de Estado ---
// Otimização: Uso de 'bool' para estados verdadeiro/falso.
bool estado_bomba = false;
bool fosforo_presente = false;
bool potassio_presente = false;

// Otimização: Usar o menor tipo de dado que cabe o valor.
// 'unsigned long' é necessário para millis()
unsigned long tempo_ultima_publicacao_mqtt = 0;
unsigned long tempo_ultima_variacao_nutrientes = 0;
const long INTERVALO_PUBLICACAO_MQTT = 15000; // 15 segundos
const long INTERVALO_VARIACAO_NUTRIENTES = 30000; // 30 segundos

// --- Protótipos das Funções ---
void setup_wifi();
void reconectar_mqtt();
void ler_e_processar_sensores();
void publicar_dados_mqtt(float umidade, float ph, bool p_presente, bool k_presente);
void controlar_bomba(String comando);
void atualizar_display();
void verificar_botoes_nutrientes();
void simular_variacao_nutrientes();
void callback_serial(String comando);
void imprimir_para_serial_plotter(float umidade, float ph);


void setup() {
    Serial.begin(115200);
    
    // Configuração dos pinos
    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, LOW); // Bomba desligada no início
    pinMode(LDR_PIN, INPUT);
    // Usar pull-up interno para os botões. Isso significa que quando o botão é pressionado o pino lê um valor BAIXO (LOW).
    pinMode(BTN_P_PIN, INPUT_PULLUP);
    pinMode(BTN_K_PIN, INPUT_PULLUP);
    
    dht.begin();

    // Inicia o LCD
    Wire.begin(); // O Wire.begin() sem argumentos usa os pinos padrão SDA (21) e SCL (22)
    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    lcd.print(F("AgroIrriga Tech"));
    lcd.setCursor(0, 1);
    lcd.print(F("Iniciando..."));
    
    delay(1000);

    setup_wifi();
    mqttClient.setServer(BROKER_MQTT, PORTA_MQTT);

    ler_e_processar_sensores(); // Leitura inicial para ter dados
    atualizar_display();
}

void loop() {
    if (!mqttClient.connected()) {
        reconectar_mqtt();
    }
    mqttClient.loop();

    // Processa comandos da Serial
    if (Serial.available() > 0) {
        String comando = Serial.readStringUntil('\n');
        comando.trim();
        callback_serial(comando);
    }
    
    // Lógica principal baseada no tempo
    unsigned long tempo_atual = millis();

    if (tempo_atual - tempo_ultima_publicacao_mqtt >= INTERVALO_PUBLICACAO_MQTT) {
        tempo_ultima_publicacao_mqtt = tempo_atual;
        
        simular_variacao_nutrientes(); // Simula variação automática
        ler_e_processar_sensores();
    }
    
    // Verificação contínua dos botões 
    verificar_botoes_nutrientes();
}

// --- Funções de Configuração e Conexão ---

void setup_wifi() {
    Serial.println();
    Serial.print(F("Conectando a "));
    Serial.println(SSID_WIFI);
    lcd.clear();
    lcd.print(F("Conectando WiFi"));

    WiFi.begin(SSID_WIFI, SENHA_WIFI);

    int tentativas = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(F("."));
        tentativas++;
        if (tentativas > 20) {
            Serial.println(F("\nFalha ao conectar. Reiniciando..."));
            lcd.clear();
            lcd.print(F("Erro WiFi"));
            delay(2000);
            ESP.restart();
        }
    }

    Serial.println(F("\nWiFi conectado!"));
    Serial.print(F("IP: "));
    Serial.println(WiFi.localIP());
    lcd.clear();
    lcd.print(F("WiFi Conectado!"));
    lcd.setCursor(0, 1);
    lcd.print(WiFi.localIP());
    delay(1500);
}

void reconectar_mqtt() {
    while (!mqttClient.connected()) {
        Serial.print(F("Tentando conectar ao Broker MQTT..."));
        lcd.clear();
        lcd.print(F("Conectando MQTT"));

        if (mqttClient.connect(ID_CLIENTE_MQTT)) {
            Serial.println(F(" conectado!"));
            lcd.clear();
            lcd.print(F("MQTT Conectado!"));
            delay(1500);
        } else {
            Serial.print(F(" falhou, rc="));
            Serial.print(mqttClient.state());
            Serial.println(F(" Tentando novamente em 5 segundos"));
            lcd.clear();
            lcd.print(F("Falha no MQTT"));
            delay(5000);
        }
    }
}

// --- Funções de Sensores e Atuadores ---

void ler_e_processar_sensores() {
    // --- Leitura de Umidade ---
    // Otimização: a biblioteca DHT já retorna float, que é o tipo apropriado.
    float umidade_solo = dht.readHumidity();
    if (isnan(umidade_solo)) {
        Serial.println(F("Falha ao ler umidade do sensor DHT!"));
        umidade_solo = 0.0; // Valor padrão em caso de falha
    }
    
    // --- Leitura do LDR (simulando pH) ---
    // Otimização: uint16_t para leitura analógica 0-4095
    uint16_t ldr_valor = analogRead(LDR_PIN);
    // Mapeamento do valor do LDR (0-4095) para uma faixa de pH (ex: 3.0 a 9.0)
    float ph_estimado = map(ldr_valor, 0, 4095, 30, 90) / 10.0;

    Serial.println(F("\n--- Novas Leituras ---"));
    Serial.print(F("Umidade do solo: ")); Serial.print(umidade_solo); Serial.println(F("%"));
    Serial.print(F("pH Estimado: ")); Serial.println(ph_estimado);
    Serial.print(F("Fosforo: ")); Serial.println(fosforo_presente ? "Presente" : "Ausente");
    Serial.print(F("Potassio: ")); Serial.println(potassio_presente ? "Presente" : "Ausente");
    
    // Publica os dados via MQTT
    publicar_dados_mqtt(umidade_solo, ph_estimado, fosforo_presente, potassio_presente);
    
    // Atualiza o display LCD com as novas informações
    atualizar_display();

    // Imprime dados formatados para o Serial Plotter
    imprimir_para_serial_plotter(umidade_solo, ph_estimado);
}

void verificar_botoes_nutrientes() {
    // Botões usam INPUT_PULLUP, então LOW significa pressionado.
    if (digitalRead(BTN_P_PIN) == LOW) {
        fosforo_presente = true;
        Serial.println(F("Botão Fósforo (P) pressionado: Marcado como Presente."));
        atualizar_display();
        delay(200); // Debounce
    }
    if (digitalRead(BTN_K_PIN) == LOW) {
        potassio_presente = true;
        Serial.println(F("Botão Potássio (K) pressionado: Marcado como Presente."));
        atualizar_display();
        delay(200); // Debounce
    }
}

void simular_variacao_nutrientes() {
    // Alterna o estado dos nutrientes para simular variação natural
    fosforo_presente = !fosforo_presente;
    potassio_presente = random(0, 2); // 0 ou 1
    Serial.println(F("Simulando variação de nutrientes..."));
}

void controlar_bomba(String comando) {
    if (comando.equalsIgnoreCase("LIGAR_BOMBA")) {
        digitalWrite(RELAY_PIN, HIGH);
        estado_bomba = true;
        Serial.println(F("Comando recebido: LIGAR BOMBA"));
    } else if (comando.equalsIgnoreCase("DESLIGAR_BOMBA")) {
        digitalWrite(RELAY_PIN, LOW);
        estado_bomba = false;
        Serial.println(F("Comando recebido: DESLIGAR BOMBA"));
    } else {
        Serial.print(F("Comando desconhecido: "));
        Serial.println(comando);
    }
    atualizar_display(); // Atualiza o status da bomba no LCD
}


// --- Funções de Comunicação (MQTT e Serial) ---

void publicar_dados_mqtt(float umidade, float ph, bool p_presente, bool k_presente) {
    // Otimização: JSON dinâmico com tamanho calculado para evitar alocação excessiva.
    StaticJsonDocument<256> doc;

    // Adiciona os valores ao documento JSON
    doc["cod_sensor_umidade"] = "DHT22_01";
    doc["umidade_solo"] = umidade;
    doc["cod_sensor_ph"] = "LDR_01";
    doc["ph_estimado"] = ph;
    doc["cod_sensor_nutri"] = "BTN_SIM_01";
    doc["fosforo_presente"] = p_presente;
    doc["potassio_presente"] = k_presente;

    char buffer_json[256];
    serializeJson(doc, buffer_json);

    Serial.print(F("Publicando no MQTT: "));
    Serial.println(buffer_json);

    if (!mqttClient.publish(TOPICO_MQTT_SENSORES, buffer_json)) {
        Serial.println(F("Falha ao publicar no MQTT."));
    }
}

void callback_serial(String comando) {
    Serial.print(F("Recebido via Serial: "));
    Serial.println(comando);

    if (comando.equalsIgnoreCase("LIGAR_BOMBA") || comando.equalsIgnoreCase("DESLIGAR_BOMBA")) {
        controlar_bomba(comando);
    } else if (comando.equalsIgnoreCase("p")) {
        fosforo_presente = true;
        Serial.println(F("Comando 'p' recebido: Fósforo marcado como presente."));
    } else if (comando.equalsIgnoreCase("k")) {
        potassio_presente = true;
        Serial.println(F("Comando 'k' recebido: Potássio marcado como presente."));
    }
    atualizar_display();
}

// --- Funções de Interface (Display e Serial Plotter) ---

void atualizar_display() {
    lcd.clear();

    // Linha 1: Umidade
    lcd.setCursor(0, 0);
    lcd.print(F("Umidade: "));
    float umidade_atual = dht.readHumidity();
    if(isnan(umidade_atual)) umidade_atual = 0.0;
    lcd.print(umidade_atual, 1); // Imprime com 1 casa decimal
    lcd.print(F("%"));

    // Linha 2: Nutrientes e Bomba
    lcd.setCursor(0, 1);
    lcd.print(F("P:"));
    lcd.print(fosforo_presente ? F("S") : F("N"));

    lcd.setCursor(4, 1);
    lcd.print(F("K:"));
    lcd.print(potassio_presente ? F("S") : F("N"));

    lcd.setCursor(8, 1);
    lcd.print(F("Bomba:"));
    lcd.print(estado_bomba ? F("ON") : F("OFF"));
}

void imprimir_para_serial_plotter(float umidade, float ph) {
    Serial.print(umidade);
    Serial.print(" "); // Separador
    Serial.println(ph);
}
