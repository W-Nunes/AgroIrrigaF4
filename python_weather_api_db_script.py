import requests
import json
import time
import cx_Oracle # Biblioteca para Oracle
import os
from datetime import datetime
import serial

# --- Configurações ---
API_KEY = "c98bc5acbfe9460aead8c017e033c644"
CIDADE = "Ibipora,BR"
UNITS = "metric"


ORACLE_USER = "RM562839" 
ORACLE_PASS = "120296"   


ORACLE_DSN = "oracle.fiap.com.br:1521/ORCL"


# Configurações da Porta Serial para comunicar com o ESP32
PORTA_SERIAL = "COM3"
BAUD_RATE = 115200
TIMEOUT_SERIAL = 1

ser_conn_python = None # Renomeada para evitar conflito com 'conn' do Oracle

def conectar_oracle():
    """Tenta conectar ao banco de dados Oracle."""
    try:

        conn = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASS, dsn=ORACLE_DSN)
        print("Conectado ao Oracle Database com sucesso.")
        return conn
    except cx_Oracle.Error as e:
        error_obj, = e.args
        print(f"Erro ao conectar ao Oracle Database: {error_obj.message}")
        print(f"Verifique suas credenciais, DSN ({ORACLE_DSN}), e se o listener Oracle está em execução.")
        return None

def conectar_serial_esp32():
    """Tenta conectar à porta serial do ESP32."""
    global ser_conn_python
    try:
        ser_conn_python = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=TIMEOUT_SERIAL)
        print(f"Conectado à porta serial {PORTA_SERIAL} com sucesso.")
        time.sleep(2)
        return True
    except serial.SerialException as e:
        print(f"Erro ao conectar à porta serial {PORTA_SERIAL}: {e}")
        ser_conn_python = None
        return False

def enviar_comando_esp32(comando):
    """Envia um comando para o ESP32 via serial."""
    if ser_conn_python and ser_conn_python.is_open:
        try:
            print(f"Enviando comando para ESP32: {comando}")
            ser_conn_python.write(comando.encode('utf-8'))
            ser_conn_python.write(b'\n')
        except serial.SerialException as e:
            print(f"Erro ao enviar comando via serial: {e}")
    else:
        print("Porta serial não está aberta. Não é possível enviar comando.")
        print(f"Comando que seria enviado (simulado): {comando}")

def obter_dados_meteorologicos(api_key, cidade, units):
    """Obtém dados meteorológicos da API OpenWeather."""
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    url_completa = f"{base_url}appid={api_key}&q={cidade}&units={units}&lang=pt_br"
    try:
        resposta = requests.get(url_completa)
        resposta.raise_for_status()
        dados = resposta.json()
        return dados
    except requests.exceptions.RequestException as err:
        print(f"Erro na Requisição da API OpenWeather: {err}")
    except json.JSONDecodeError:
        print("Erro ao decodificar a resposta JSON da API OpenWeather.")
    return None

def salvar_decisao_no_oracle(conn_oracle, dados_meteo):
    """Decide sobre a irrigação e salva a decisão e dados no Oracle DB."""
    comando_bomba = "DESLIGAR_BOMBA" # Decisão segura por padrão
    fonte_decisao = "Falha na API"
    cond_meteo = "Erro ao obter dados"
    umidade_api = None
    temp_api = None
    id_tempo_api_val = None

    if dados_meteo:
        fonte_decisao = "API OpenWeather"
        cond_meteo = dados_meteo['weather'][0]['description'].capitalize()
        id_tempo_api_val = str(dados_meteo['weather'][0]['id'])
        umidade_api = dados_meteo['main']['humidity']
        temp_api = dados_meteo['main']['temp']

        print(f"\n--- Dados Meteorológicos para {CIDADE} ---")
        print(f"Condição: {cond_meteo}")
        print(f"Umidade do Ar: {umidade_api}%")
        print(f"Temperatura: {temp_api}°C")

        if int(id_tempo_api_val) < 700: # Chuva ou similar
            print("Decisão API: Previsão de chuva ou chuva atual. Não irrigar.")
            comando_bomba = "DESLIGAR_BOMBA"
        elif umidade_api is not None and umidade_api > 75:
            print("Decisão API: Umidade do ar elevada. Não irrigar.")
            comando_bomba = "DESLIGAR_BOMBA"
        else:
            print("Decisão API: Condições indicam necessidade de irrigação.")
            comando_bomba = "LIGAR_BOMBA"
    else:
        print("Não foi possível obter dados meteorológicos para decisão.")

    if conn_oracle:
        cursor = None
        try:
            cursor = conn_oracle.cursor()
            sql_insert = """
                INSERT INTO log_controle_bomba 
                (timestamp_decisao, comando_bomba, fonte_decisao, condicao_meteo_desc, umidade_ar_api, temperatura_api, id_tempo_api)
                VALUES (SYSDATE, :comando, :fonte, :cond_meteo, :umidade, :temp, :id_tempo)
            """
            cursor.execute(sql_insert, comando=comando_bomba, fonte=fonte_decisao, cond_meteo=cond_meteo,
                           umidade=umidade_api, temp=temp_api, id_tempo=id_tempo_api_val)
            conn_oracle.commit()
            print(f"Decisão '{comando_bomba}' salva no Oracle DB.")
        except cx_Oracle.Error as e:
            error_obj, = e.args
            print(f"Erro ao inserir dados no Oracle (log_controle_bomba): {error_obj.message}")
            if conn_oracle: conn_oracle.rollback() # Importante em caso de erro
        finally:
            if cursor:
                cursor.close()
    else:
        print("Sem conexão com Oracle DB. Decisão não foi salva.")
    
    return comando_bomba


def ler_ultimo_comando_do_oracle_e_enviar(conn_oracle):
    """Lê o último comando da tabela log_controle_bomba e envia para o ESP32."""
    comando_a_enviar = "DESLIGAR_BOMBA" # Comando seguro padrão
    if conn_oracle:
        cursor = None
        try:
            cursor = conn_oracle.cursor()
            # Oracle não tem LIMIT 1 fácil como MySQL/Postgres.
            sql_select = """
                SELECT comando_bomba FROM (
                    SELECT comando_bomba, timestamp_decisao 
                    FROM log_controle_bomba 
                    ORDER BY timestamp_decisao DESC
                ) WHERE ROWNUM = 1
            """
            cursor.execute(sql_select)
            resultado = cursor.fetchone()
            if resultado:
                comando_a_enviar = resultado[0]
                print(f"\nLendo do Oracle DB: Último comando registrado = {comando_a_enviar}")
            else:
                print("Nenhum comando encontrado no Oracle DB. Usando comando padrão (DESLIGAR_BOMBA).")
        except cx_Oracle.Error as e:
            error_obj, = e.args
            print(f"Erro ao ler dados do Oracle (log_controle_bomba): {error_obj.message}")
        finally:
            if cursor:
                cursor.close()
    else:
        print("Sem conexão com Oracle DB. Usando comando padrão (DESLIGAR_BOMBA).")

    enviar_comando_esp32(comando_a_enviar)


if __name__ == "__main__":
    if not API_KEY or API_KEY == "e47865202bb148c6397ad4860d1fe4dd":
        print("ERRO: Chave da API OpenWeather não configurada.")
    elif not ORACLE_DSN or ORACLE_DSN == "SEU_HOST_ORACLE:SUA_PORTA_ORACLE/SEU_SERVICE_NAME_OU_SID":
        print("ERRO: String de conexão Oracle DSN não configurada corretamente.")
    else:
        conn_oracle_main = conectar_oracle() # Tenta conectar ao Oracle na inicialização
        
        # Tenta conectar à serial para o ESP32
        # A falha aqui não impede o script de rodar e interagir com Oracle/API
        conexao_serial_ativa = conectar_serial_esp32()

        intervalo_verificacao_api_segundos = 1 * 10 
        intervalo_envio_comando_segundos = 30      

        proxima_verificacao_api = time.time()
        proximo_envio_comando = time.time()

        try:
            while True:
                tempo_atual = time.time()

                if tempo_atual >= proxima_verificacao_api:
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Verificando API meteorológica...")
                    dados_api = obter_dados_meteorologicos(API_KEY, CIDADE, UNITS)
                    salvar_decisao_no_oracle(conn_oracle_main, dados_api)
                    proxima_verificacao_api = tempo_atual + intervalo_verificacao_api_segundos
                    print("-" * 40)

                if tempo_atual >= proximo_envio_comando:
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Verificando Oracle DB para enviar comando ao ESP32...")
                    ler_ultimo_comando_do_oracle_e_enviar(conn_oracle_main)
                    proximo_envio_comando = tempo_atual + intervalo_envio_comando_segundos
                    print("-" * 40)
                
                time.sleep(5) 
        except KeyboardInterrupt:
            print("\nPrograma interrompido pelo usuário.")
        finally:
            if conn_oracle_main:
                conn_oracle_main.close()
                print("Conexão com Oracle DB fechada.")
            if ser_conn_python and ser_conn_python.is_open:
                ser_conn_python.close()
                print("Conexão serial com ESP32 fechada.")
