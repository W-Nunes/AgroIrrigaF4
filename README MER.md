AgroIrriga - Soluções Tecnológicas em Irrigação Inteligente (Projeto Simulado)
1. Visão Geral do Projeto
Este projeto, desenvolvido para a disciplina de Edge Computing & Computer Systems da FIAP, simula um sistema de irrigação inteligente para a empresa fictícia "AgroIrriga - Soluções Tecnológicas". O objetivo é coletar dados de sensores simulados (umidade do solo, nutrientes P/K, pH), integrar com uma API meteorológica para tomar decisões de irrigação e armazenar todos os dados relevantes num banco de dados Oracle. Um dashboard em Python (Streamlit) permite a visualização e análise desses dados. A simulação do hardware é realizada na plataforma Wokwi.com, e a automação da coleta de dados do ESP32 para o banco de dados é feita utilizando o protocolo MQTT.

2. Arquitetura do Sistema
O sistema é composto pelos seguintes componentes principais:

Simulador de Hardware (Wokwi com ESP32):

Microcontrolador ESP32.

Sensor de Umidade do Solo (DHT22).

Sensor de Fósforo (P): Simulado por um botão físico e também por variação automática interna.

Sensor de Potássio (K): Simulado por um botão físico e também por variação automática interna.

Sensor de pH: Simulado por um LDR (Light Dependent Resistor) cuja leitura varia automaticamente.

Atuador da Bomba de Irrigação: Representado por um módulo Relé.

O ESP32 publica os dados dos sensores via MQTT e recebe comandos para a bomba via Serial.

Broker MQTT:

Um broker MQTT público (ex: broker.hivemq.com) é usado para mediar a comunicação entre o ESP32 e o script coletor de dados.

Script Python Coletor MQTT (mqtt_oracle_collector.py):

Subscreve ao tópico MQTT onde o ESP32 publica os dados dos sensores.

Recebe os dados, faz o parse e insere-os nas tabelas apropriadas (s_umidade_solo, s_ph, s_nutrientes) no banco de dados Oracle.

Script Python da API Meteorológica (python_oracle_weather_api_script.py):

Consulta uma API pública (OpenWeather) para obter dados meteorológicos.

Com base nesses dados, decide se a irrigação deve ser ligada ou desligada.

Registra essa decisão e os dados meteorológicos na tabela log_controle_bomba do Oracle.

Lê a última decisão do Oracle e a envia (atualmente por impressão no console, para ser inserida manualmente no Monitor Serial do Wokwi) para o ESP32 controlar a bomba.

Banco de Dados Oracle:

Armazena todos os dados históricos dos sensores e as decisões de controle da bomba.

Tabelas principais: s_umidade_solo, s_ph, s_nutrientes, log_controle_bomba (e tabelas de apoio como produtor, talhao, cultura que foram simplificadas ou tiveram suas FKs tornadas opcionais/removidas nas tabelas de sensores para foco inicial).

Dashboard Python (dashboard_app.py):

Desenvolvido com Streamlit.

Conecta-se ao banco de dados Oracle.

Exibe gráficos e tabelas interativas com os dados de umidade do solo, pH, nutrientes e o histórico de acionamento da bomba.

3. Simulação dos Sensores no ESP32
Umidade do Solo: Lida diretamente do sensor DHT22.

Fósforo (P) e Potássio (K): O estado (Presente/Ausente) é simulado para variar automaticamente em intervalos de tempo aleatórios. Além disso, botões físicos no Wokwi e comandos seriais ('p', 'k') podem forçar o estado "Presente" para a leitura atual.

pH: A leitura de um LDR simulado (valor raw) varia automaticamente, e o pH é então calculado a partir dessa leitura simulada.

4. Lógica de Controle da Irrigação
O script Python python_oracle_weather_api_script.py consulta a API OpenWeather.

Com base em regras (ex: se há previsão de chuva, se a umidade do ar está alta), ele decide se a bomba deve ser "LIGAR_BOMBA" ou "DESLIGAR_BOMBA".

Esta decisão é gravada na tabela log_controle_bomba do Oracle.

O mesmo script lê a decisão mais recente do Oracle e a passa para o ESP32 (atualmente, imprimindo no console para transferência manual para o Monitor Serial do Wokwi).

O ESP32 recebe o comando e aciona o relé da bomba.

5. Estrutura do Banco de Dados Oracle (Principais Tabelas)
s_umidade_solo: Armazena leituras de umidade do solo (cod_sensor, nivel_umidade, atualizado_em).

s_ph: Armazena leituras de pH (cod_sensor, nivel_ph, atualizado_em).

s_nutrientes: Armazena dados de nutrientes (cod_sensor, presenca_p, presenca_k, nivel_p (opcional), nivel_k (opcional), atualizado_em).

log_controle_bomba: Registra as decisões de ligar/desligar a bomba vindas da API meteorológica, incluindo dados que justificaram a decisão.

(Outras tabelas como produtor, talhao, cultura, categoria_sensor foram definidas, mas as chaves estrangeiras nas tabelas de sensores foram simplificadas/removidas para focar no fluxo principal de dados dos sensores e da API).

6. Como Executar o Sistema Completo
Pré-requisitos:

Ambiente Python com as bibliotecas: requests, cx_Oracle, paho-mqtt, streamlit, pandas, plotly.

Acesso a um servidor Oracle com as tabelas do projeto criadas (usar os DDLs fornecidos).

Uma chave de API válida da OpenWeather.

VSCode com a extensão PlatformIO e Wokwi (ou acesso ao site Wokwi.com).

Ordem de Execução:

Configurar platformio.ini no VSCode: Adicionar as lib_deps para PubSubClient e ArduinoJson se ainda não estiverem lá.

Configurar diagram.json no Wokwi: Usar a versão final com atributos Wi-Fi.

Script Coletor MQTT (mqtt_oracle_collector.py):

Configure as credenciais Oracle e detalhes do broker MQTT.

Execute num terminal: python mqtt_oracle_collector.py. Deixe a rodar.

Simulação ESP32 (Wokwi):

Carregue o código farmtech_esp32_mqtt_publisher_v2.ino (ou o nome que você deu ao ficheiro .ino) no Wokwi.

Inicie a simulação.

Abra o Monitor Serial do Wokwi para observar os logs de conexão Wi-Fi/MQTT e publicação de dados.

Verifique o terminal do Coletor MQTT para confirmar o recebimento e inserção dos dados no Oracle.

Script da API Meteorológica (python_oracle_weather_api_script.py):

Configure a chave da API OpenWeather e as credenciais Oracle.

Execute num outro terminal: python python_oracle_weather_api_script.py. Deixe a rodar.

Observe os logs para a busca na API, decisão e registo no Oracle.

Copie o "Comando que seria enviado (simulado)" da sua saída.

Controle do ESP32 (Manual):

Cole o comando copiado do script da API no Monitor Serial do Wokwi e pressione Enter.

Observe a reação do ESP32 e do relé.

Dashboard (dashboard_app.py):

Configure as credenciais Oracle.

Execute num terceiro terminal: streamlit run dashboard_app.py.

Acesse o dashboard no seu navegador (ex: http://localhost:8501).

Use o botão "Recarregar Dados" para ver as informações mais recentes.

7. Atividades "Ir Além"
Ir Além 1: Dashboard em Python: Implementado parcialmente com este dashboard Streamlit. Pode ser expandido com mais interatividade, filtros e tipos de gráficos.

Ir Além 2: Integração Python com API Pública: Implementado com o script que consulta a OpenWeather e usa esses dados para influenciar a decisão de irrigação, registando-a no Oracle.

8. Nome da Empresa
AgroIrriga - Soluções Tecnológicas