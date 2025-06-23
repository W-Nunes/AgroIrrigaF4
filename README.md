# AgroIrriga - Soluções Tecnológicas: Detalhamento do Circuito e Lógica de Controle

Este documento descreve a montagem do circuito eletrônico e a lógica de controle implementada no microcontrolador ESP32 para o sistema de irrigação inteligente simulado da AgroIrriga.

## 1. Componentes do Circuito

O sistema simulado utiliza os seguintes componentes eletrônicos:

* **Microcontrolador:** ESP32 DevKitC V4 (ou similar) - O cérebro do sistema, responsável por ler os sensores e controlar os atuadores.
* **Sensor de Umidade do Solo:** Módulo DHT22 - Fornece leituras de umidade do solo (e temperatura, embora o foco seja umidade).
    * *(Visualizado em `img 1.png` e `img 2.png`)*
* **Sensor de pH (Simulado):** Módulo Sensor Fotoresistor (LDR) - Um sensor de luz (LDR) é usado para simular as variações contínuas de um sensor de pH. A variação da luminosidade captada pelo LDR é lida como um valor analógico.
    * *(Visualizado em `img 1.png` e `img 3.png`)*
* **Sensor de Fósforo (P - Simulado):** Botão de pressão (Push Button) - Simula a detecção de presença/ausência de Fósforo.
    * *(Botão vermelho em `img 1.png` e `img 3.png`)*
* **Sensor de Potássio (K - Simulado):** Botão de pressão (Push Button) - Simula a detecção de presença/ausência de Potássio.
    * *(Botão amarelo em `img 1.png` e `img 3.png`)*
* **Atuador da Bomba de Irrigação (Simulado):** Módulo Relé de 1 canal - Controla o acionamento da bomba d'água (a bomba em si não está no circuito, apenas o relé que a controlaria).
    * *(Visualizado em `img 1.png` e `img 2.png`)*
* **Resistores:**
    * 1x Resistor (ex: 10kΩ) para o divisor de tensão com o LDR (se o módulo LDR não tiver um circuito adequado para saída analógica direta ou se um LDR simples for usado). A imagem `img 3.png` mostra um módulo sensor LDR que já pode incluir a eletrónica necessária, mas a nossa implementação final no `diagram.json` considerou um LDR com resistor externo para o divisor.
    * 2x Resistores (ex: 10kΩ) para pull-up dos botões de pressão.
* **Protoboard (Breadboard):** Para facilitar a montagem e as conexões dos componentes.
* **Jumpers:** Fios para realizar as conexões.

## 2. Montagem e Conexões do Circuito

As conexões são realizadas conforme o `diagram.json` do projeto Wokwi e podem ser visualizadas nas imagens fornecidas.

* **Alimentação Geral:**
    * O ESP32 fornece alimentação de 3.3V e GND para os componentes na protoboard.
    * As linhas de barramento da protoboard são usadas para distribuir 3.3V e GND.
        * *(Conexões de alimentação do ESP32 para a protoboard visíveis em `img 1.png`)*

* **ESP32 e Protoboard:**
    * O ESP32 é encaixado na protoboard.
    * Pinos `3V3` e `GND` do ESP32 são conectados às linhas de alimentação da protoboard.

* **Sensor de Umidade do Solo (DHT22):**
    * **VCC:** Conectado ao barramento de 3.3V da protoboard.
    * **GND:** Conectado ao barramento GND da protoboard.
    * **DATA (Sinal):** Conectado ao **GPIO18** do ESP32.
        * *(Conexões visíveis em `img 2.png`)*

* **Sensor de pH (Módulo LDR ou LDR com Divisor de Tensão):**
    * O módulo LDR (azul em `img 3.png`) ou um LDR simples é configurado para fornecer uma saída analógica.
    * **VCC (Módulo):** Conectado ao barramento de 3.3V.
    * **GND (Módulo):** Conectado ao barramento GND.
    * **AO (Saída Analógica do Módulo ou ponto médio do divisor de tensão):** Conectado ao **GPIO34** do ESP32 (um pino ADC - Conversor Analógico-Digital).
        * *(O módulo LDR é visto em `img 3.png`. A lógica do divisor é: 3.3V -> LDR -> (Ponto de Leitura/AO) -> Resistor -> GND)*

* **Sensores de Nutrientes (Botões P e K):**
    * Configuração com resistor de **pull-up externo**:
        * Um terminal do botão é conectado ao barramento GND.
        * O outro terminal do botão é conectado:
            * Ao pino de entrada digital do ESP32.
            * A um resistor (ex: 10kΩ), cujo outro lado é conectado ao barramento de 3.3V (VCC).
    * **Botão de Fósforo (P - Vermelho):** Sinal conectado ao **GPIO13** do ESP32.
    * **Botão de Potássio (K - Amarelo):** Sinal conectado ao **GPIO12** do ESP32.
        * *(Conexões dos botões e resistores de pull-up visíveis em `img 3.png`)*

* **Módulo Relé (Bomba de Irrigação):**
    * **VCC:** Conectado ao pino **5V** do ESP32 (muitos módulos relé requerem 5V para a bobina).
    * **GND:** Conectado ao barramento GND da protoboard.
    * **IN (Sinal de Controle):** Conectado ao **GPIO5** do ESP32.
        * *(Conexões visíveis em `img 2.png`)*

## 3. Lógica de Controle Implementada no ESP32

O firmware carregado no ESP32 executa as seguintes funções:

* **Inicialização (`setup()`):**
    * Configura a comunicação serial para debugging e visualização.
    * Define os pinos dos sensores como ENTRADA (os botões P e K usam resistores de pull-up externos).
    * Define o pino do relé como SAÍDA e o inicializa como desligado.
    * Inicializa o sensor DHT22.
    * Inicializa o gerador de números aleatórios.
    * Configura e tenta conectar-se à rede Wi-Fi (simulada no Wokwi) e ao broker MQTT para publicação dos dados dos sensores (esta parte é para a integração completa, mas o ESP32 em si se prepara para isso).

* **Loop Principal (`loop()`):**
    1.  **Conectividade:** Verifica e tenta restabelecer conexões Wi-Fi e MQTT caso tenham caído.
    2.  **Recebimento de Comandos Seriais:** Ouve a porta serial por comandos como "LIGAR_BOMBA" ou "DESLIGAR_BOMBA". Estes comandos, no sistema completo, são enviados pelo script Python que interage com a API meteorológica e o banco de dados Oracle.
        * A variável `bomba_ligada` é atualizada com base no comando recebido.
        * O `RELAY_PIN` é acionado (HIGH para ligar, LOW para desligar) de acordo.
    3.  **Simulação Automática dos Sensores de Nutrientes (P e K):**
        * Os estados de presença/ausência de Fósforo (`sim_fosforo_state`) e Potássio (`sim_potassio_state`) são atualizados periodicamente (em intervalos de tempo aleatórios entre 10 e 30 segundos).
        * A cada reavaliação, o novo estado (presente/ausente) é escolhido aleatoriamente.
    4.  **Leitura dos Botões Físicos (P e K):**
        * O estado dos botões físicos (GPIO13 para P, GPIO12 para K) é lido. Um botão pressionado (nível LOW devido ao pull-up) indica presença.
    5.  **Determinação do Estado Final de P e K:**
        * O estado final (`fosforo_presente`, `potassio_presente`) para a leitura atual é considerado "Presente" se a simulação automática indicar presença, OU se o botão físico correspondente estiver pressionado.
    6.  **Simulação da Leitura do LDR (pH):**
        * Um valor analógico bruto (`ldr_valor_raw`) é gerado aleatoriamente (simulando a variação da leitura de um LDR conectado ao GPIO34).
        * O `ph_estimado` é calculado mapeando este `ldr_valor_raw` para uma escala de pH (ex: 0-14).
    7.  **Leitura do Sensor de Umidade do Solo (DHT22):**
        * A umidade do solo (`umidade_solo`) é lida do sensor DHT22 conectado ao GPIO18.
    8.  **Publicação de Dados via MQTT:**
        * Todos os dados dos sensores (pH estimado, presença de P, presença de K, umidade do solo) são formatados num payload JSON.
        * Este JSON é publicado num tópico MQTT específico (`agroirriga/rm562839/sensores`).
    9.  **Exibição no Monitor Serial Local:**
        * Os valores atuais de todos os sensores e o estado da bomba são impressos no Monitor Serial do Wokwi para depuração e acompanhamento.
    10. **Atraso:** Uma pausa (ex: 10 segundos) é feita antes de repetir o loop.

Esta lógica permite que o ESP32 opere de forma semi-autónoma na simulação dos sensores, publique esses dados para um sistema externo (via MQTT) e seja controlado remotamente (via comandos seriais) para o acionamento da bomba de irrigação.
