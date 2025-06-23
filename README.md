# FarmTech Solutions - Fase 4: Irrigação Inteligente com Machine Learning

## 1. Visão Geral do Projeto

Este repositório representa a **Fase 4** do projeto **FarmTech Solutions**, uma evolução significativa do sistema de irrigação inteligente desenvolvido na Fase 3. O objetivo principal desta fase foi incorporar uma camada de inteligência artificial com **Scikit-learn**, aprimorar a interface do usuário com **Streamlit** e otimizar o sistema embarcado no **ESP32**, incluindo um novo display LCD para feedback em tempo real e monitoramento via Serial Plotter.

O sistema agora não apenas coleta e exibe dados, mas também **prevê a necessidade de irrigação** com base em dados climáticos, tornando as operações agrícolas mais eficientes e sustentáveis.

---

## 2. Arquitetura do Sistema

A arquitetura foi expandida para incluir os novos componentes de software e hardware, mantendo a base robusta da Fase 3:

* **ESP32 (Wokwi):**
    * Coleta dados de umidade, pH (simulado) e nutrientes (simulado).
    * Exibe dados em tempo real em um **display LCD 16x2 I2C**.
    * Envia dados formatados para o **Serial Plotter** para monitoramento visual.
    * Publica os dados dos sensores para um **Broker MQTT**.
    * Recebe comandos (LIGAR/DESLIGAR) para o relé da bomba.
* **Scripts Python:**
    * `gerador_dados_climaticos.py`: **(Novo)** Script para criar um dataset sintético e balanceado para o treinamento do modelo.
    * `treinar_modelo.py`: **(Novo)** Script que utiliza **Scikit-learn** para treinar um modelo de classificação (Random Forest) e salvá-lo em um arquivo `.joblib`.
    * `mqtt_oracle_collector.py`: Coletor de dados que escuta o Broker MQTT e persiste os dados dos sensores no Oracle DB.
    * `python_weather_api_db_script.py`: Script que consulta a API OpenWeather e registra decisões no Oracle DB.
* **Dashboard Interativo:**
    * `dashboard_app_fase4.py`: **(Aprimorado)** Desenvolvido com **Streamlit**, agora inclui uma seção interativa que carrega o modelo treinado para fazer previsões em tempo real com base na entrada do usuário.
* **Banco de Dados:**
    * **Oracle DB** continua sendo o repositório central para todos os dados históricos de sensores e decisões de irrigação.

---

## 3. Melhorias e Implementações da Fase 4

### a) Incorporação de Scikit-learn (Modelo Preditivo)

Para adicionar inteligência ao sistema, foi desenvolvido um modelo de Machine Learning usando a biblioteca Scikit-learn.

* **Modelo:** Foi utilizado um `RandomForestClassifier` por sua robustez em tarefas de classificação.
* **Objetivo:** Prever o `COMANDO_BOMBA` ("LIGAR_BOMBA" ou "DESLIGAR_BOMBA") com base nas `UMIDADE_AR_API` e `TEMPERATURA_API`.
* **Treinamento:** O script `treinar_modelo.py` foi criado para carregar os dados, pré-processá-los, treinar o modelo e salvar os artefatos (`.joblib`) para uso posterior no dashboard.
* **Dados Sintéticos:** Devido à falta de variedade nos dados originais, foi criado o `gerador_dados_climaticos.py` para gerar 10.000 linhas de dados climáticos realistas e balanceados, simulando um ano de condições para o Norte do Paraná.

### b) Implementação e Aprimoramento do Streamlit

O dashboard da Fase 3 foi significativamente melhorado:

* **Seção Preditiva:** Uma nova seção "Modelo Preditivo de Irrigação" foi adicionada ao `dashboard_app_fase4.py`.
* **Interatividade:** O usuário pode agora usar sliders para ajustar os valores de umidade e temperatura e clicar em um botão para receber uma recomendação instantânea do modelo de IA.
* **Integração:** O dashboard carrega os arquivos `.joblib` (modelo, codificador e colunas) para realizar as previsões sem a necessidade de se conectar a um endpoint de API de ML.

### c) Display LCD no Wokwi

Para fornecer feedback visual direto no "hardware", um display LCD 16x2 com comunicação I2C foi adicionado ao circuito no Wokwi.

* **Informações Exibidas:** O display mostra em tempo real:
    * **Linha 1:** Nível de umidade do solo.
    * **Linha 2:** Status dos nutrientes (P/K) e o estado atual da bomba (ON/OFF).
* **Código:** O arquivo `.ino` foi atualizado com a biblioteca `LiquidCrystal_I2C` e uma função `atualizar_display()` que é chamada sempre que os dados são lidos ou um comando é recebido.

### d) Monitoramento com Serial Plotter

Para facilitar a análise visual e em tempo real das variáveis dos sensores:

* **Saída Formatada:** Uma função `imprimir_para_serial_plotter()` foi adicionada ao código do ESP32. Ela envia os valores de umidade e pH para a porta serial, separados por um espaço.
* **Uso:** Ao abrir o **Serial Plotter** no VS Code (com a extensão PlatformIO) ou na Arduino IDE enquanto a simulação está rodando, dois gráficos são exibidos, um para cada variável, permitindo a observação de suas flutuações.

*Exemplo de Print do Serial Plotter:*
*Obs: Insira aqui um print da sua tela mostrando o gráfico do Serial Plotter.*

[Imagem do Serial Plotter]


### e) Otimização de Memória no ESP32

O código C/C++ do ESP32 foi revisado e otimizado para um uso mais eficiente da memória, uma prática crucial em sistemas embarcados. As otimizações estão comentadas no próprio código (`.ino`):

* **Tipos de Dados Específicos:** Uso de `uint8_t` para pinos (valores de 0 a 255) e `uint16_t` para leituras analógicas (0-4095), em vez de `int`, economizando memória. `bool` foi usado para variáveis de estado.
* **Uso da Macro `F()`:** Strings literais (como "Conectando WiFi" ou "Umidade:") foram envolvidas pela macro `F()`. Isso armazena a string na memória FLASH (programa) em vez da SRAM (dados), liberando a valiosa SRAM para as variáveis do programa.
* **Constantes:** Uso de `const` para declarar pinos e configurações fixas, permitindo que o compilador realize otimizações.

---

## 4. Como Executar o Sistema Completo

Siga esta ordem para garantir o funcionamento correto de todos os componentes.

### Pré-requisitos

1.  **Python 3.8+** instalado.
2.  **VS Code** com a extensão **PlatformIO IDE**.
3.  **Oracle Instant Client** configurado no seu sistema para que a biblioteca `cx_Oracle` funcione.
4.  Instale todas as bibliotecas Python necessárias com um único comando:
    ```bash
    pip install streamlit pandas scikit-learn joblib cx_Oracle paho-mqtt numpy
    ```

### Ordem de Execução

#### Etapa de Preparação (Fazer apenas uma vez)

1.  **Gerar Dados Climáticos:** Primeiro, crie o dataset que será usado para o treinamento.
    * **Comando:** `python gerador_dados_climaticos.py`
    * **Resultado:** Será criado o arquivo `dados_climaticos_sinteticos.csv`.

2.  **Treinar o Modelo de ML:** Use o dataset gerado para treinar o modelo.
    * **Importante:** Abra o arquivo `treinar_modelo.py` e certifique-se de que ele está lendo o arquivo correto: `caminho_csv = 'dados_climaticos_sinteticos.csv'`.
    * **Comando:** `python treinar_modelo.py`
    * **Resultado:** Serão criados os três arquivos `.joblib` necessários para o dashboard.

#### Etapa de Execução do Sistema (Rodar sempre que for usar)

Abra 3 terminais separados.

1.  **Terminal 1 - Iniciar a Simulação do Hardware:**
    * Abra o projeto no VS Code e inicie a simulação no **Wokwi**.

2.  **Terminal 2 - Iniciar o Coletor de Dados:**
    * Este script escuta os dados do ESP32 e salva no Oracle.
    * **Comando:** `python mqtt_oracle_collector.py`

3.  **Terminal 3 - Iniciar o Dashboard Interativo:**
    * Este comando iniciará o servidor web local e abrirá o dashboard no seu navegador.
    * **Comando:** `streamlit run dashboard_app_fase4.py`

Após esses passos, o sistema estará totalmente operacional. Você verá os dados dos sensores sendo atualizados no dashboard e poderá usar a seção de previsão para interagir com o modelo de Machine Learning.

---

## 5. Vídeo de Demonstração

Para uma visão completa do sistema em funcionamento, assista ao vídeo de demonstração no YouTube:

* **Link do Vídeo:** [Vídeo explicando o funcionamento]](https://youtu.be/SBN8cDLW3sM)

