import paho.mqtt.client as mqtt
import json
import cx_Oracle
from datetime import datetime
import time

# --- Configurações MQTT ---
BROKER_MQTT = "broker.hivemq.com"
PORTA_MQTT = 1883
TOPICO_MQTT_SENSORES = "agroirriga/rm562839/sensores" 
ID_CLIENTE_MQTT_COLETOR = "agroirriga_oracle_collector_rm562839_v2" 

# --- Configurações Oracle ---
ORACLE_USER = "RM562839" 
ORACLE_PASS = "120296"   
ORACLE_DSN = "oracle.fiap.com.br:1521/ORCL" 

conn_oracle_global = None

def conectar_oracle_coletor():
    """Tenta conectar ao banco de dados Oracle e retorna a conexão."""
    try:
        conn = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASS, dsn=ORACLE_DSN)
        print("Coletor MQTT: Conectado ao Oracle Database com sucesso.")
        return conn
    except cx_Oracle.Error as e:
        error_obj, = e.args
        print(f"Coletor MQTT: Erro ao conectar ao Oracle Database: {error_obj.message}")
        return None

def inserir_dados_ph(conn_oracle, cod_sensor, ph_estimado_val):
    """Insere dados de pH na tabela s_ph."""
    if not conn_oracle:
        print("Coletor MQTT: Sem conexão com Oracle para inserir dados de pH.")
        return
    cursor = None
    try:
        cursor = conn_oracle.cursor()
        sql_insert_ph = """
            INSERT INTO s_ph (cod_sensor, nivel_ph, atualizado_em) 
            VALUES (:cod_s, :nivel_ph, SYSDATE)
        """
        cursor.execute(sql_insert_ph, cod_s=cod_sensor, nivel_ph=ph_estimado_val)
        conn_oracle.commit()
        print(f"Coletor MQTT: Dados de pH inseridos: Sensor={cod_sensor}, pH={ph_estimado_val}")
    except cx_Oracle.Error as e:
        error_obj, = e.args
        print(f"Coletor MQTT: Erro ao inserir dados de pH no Oracle: {error_obj.message}")
        if conn_oracle: conn_oracle.rollback()
    finally:
        if cursor: cursor.close()

def inserir_dados_nutrientes(conn_oracle, cod_sensor, p_presente, k_presente, nivel_p_val=None, nivel_k_val=None):
    """Insere dados de nutrientes na tabela s_nutrientes."""
    if not conn_oracle:
        print("Coletor MQTT: Sem conexão com Oracle para inserir dados de nutrientes.")
        return
        
    cursor = None
    try:
        cursor = conn_oracle.cursor()
        sql_insert_nutri = """
            INSERT INTO s_nutrientes (cod_sensor, presenca_p, presenca_k, nivel_p, nivel_k, atualizado_em)
            VALUES (:cod_s, :p_pres, :k_pres, :nivel_p, :nivel_k, SYSDATE)
        """
        p_val = 1 if p_presente else 0
        k_val = 1 if k_presente else 0
        cursor.execute(sql_insert_nutri, cod_s=cod_sensor, p_pres=p_val, k_pres=k_val, 
                       nivel_p=nivel_p_val, nivel_k=nivel_k_val)
        conn_oracle.commit()
        print(f"Coletor MQTT: Dados de Nutrientes inseridos: Sensor={cod_sensor}, P={p_presente}, K={k_presente}")
    except cx_Oracle.Error as e:
        error_obj, = e.args
        print(f"Coletor MQTT: Erro ao inserir dados de nutrientes no Oracle: {error_obj.message}")
        if conn_oracle: conn_oracle.rollback()
    finally:
        if cursor: cursor.close()

def inserir_dados_umidade_solo(conn_oracle, cod_sensor, umidade_val):
    """Insere dados de umidade do solo na tabela s_umidade_solo."""
    if not conn_oracle:
        print("Coletor MQTT: Sem conexão com Oracle para inserir dados de umidade do solo.")
        return
    cursor = None
    try:
        cursor = conn_oracle.cursor()
        sql_insert_umidade = """
            INSERT INTO s_umidade_solo (cod_sensor, nivel_umidade, atualizado_em) 
            VALUES (:cod_s, :nivel_umid, SYSDATE)
        """
        cursor.execute(sql_insert_umidade, cod_s=cod_sensor, nivel_umid=umidade_val)
        conn_oracle.commit()
        print(f"Coletor MQTT: Dados de Umidade do Solo inseridos: Sensor={cod_sensor}, Umidade={umidade_val}%")
    except cx_Oracle.Error as e:
        error_obj, = e.args
        print(f"Coletor MQTT: Erro ao inserir dados de umidade do solo no Oracle: {error_obj.message}")
        if conn_oracle: conn_oracle.rollback()
    finally:
        if cursor: cursor.close()

# --- Funções Callback do MQTT ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Coletor MQTT: Ligado ao Broker MQTT: {BROKER_MQTT}")
        client.subscribe(TOPICO_MQTT_SENSORES)
        print(f"Coletor MQTT: Subscrito ao tópico: {TOPICO_MQTT_SENSORES}")
    else:
        print(f"Coletor MQTT: Falha ao ligar ao MQTT, código de retorno: {rc}")

def on_message(client, userdata, msg):
    global conn_oracle_global
    print(f"\nColetor MQTT: Mensagem recebida no tópico '{msg.topic}'")
    payload_str = msg.payload.decode('utf-8')
    print(f"Payload: {payload_str}")

    try:
        dados_sensor = json.loads(payload_str)

        cod_sensor_ph = dados_sensor.get("cod_sensor_ph")
        ph_val = dados_sensor.get("ph_estimado")

        cod_sensor_nutri = dados_sensor.get("cod_sensor_nutri")
        p_pres = dados_sensor.get("fosforo_presente")
        k_pres = dados_sensor.get("potassio_presente")
        
        cod_sensor_umidade = dados_sensor.get("cod_sensor_umidade") # Nova chave
        umidade_val = dados_sensor.get("umidade_solo") # Nova chave

        if not conn_oracle_global or conn_oracle_global.ping() is None : 
            print("Coletor MQTT: Conexão Oracle não ativa. A tentar reconectar...")
            if conn_oracle_global: 
                try: conn_oracle_global.close()
                except cx_Oracle.Error: pass 
            conn_oracle_global = conectar_oracle_coletor()
        
        if conn_oracle_global:
            if cod_sensor_ph is not None and ph_val is not None:
                inserir_dados_ph(conn_oracle_global, cod_sensor_ph, ph_val)
            
            if cod_sensor_nutri is not None and p_pres is not None and k_pres is not None:
                inserir_dados_nutrientes(conn_oracle_global, cod_sensor_nutri, p_pres, k_pres)
            
            if cod_sensor_umidade is not None and umidade_val is not None: # Processa umidade do solo
                inserir_dados_umidade_solo(conn_oracle_global, cod_sensor_umidade, umidade_val)
        else:
            print("Coletor MQTT: Não foi possível processar a mensagem devido à falha na conexão com o Oracle.")

    except json.JSONDecodeError:
        print("Coletor MQTT: Erro ao fazer parse do JSON da mensagem MQTT.")
    except Exception as e:
        print(f"Coletor MQTT: Erro inesperado ao processar mensagem MQTT: {e}")

# --- Configuração e Loop Principal do Coletor MQTT ---
if __name__ == "__main__":
    if not ORACLE_DSN or ORACLE_DSN == "SEU_HOST_ORACLE:SUA_PORTA_ORACLE/SEU_SERVICE_NAME_OU_SID":
        print("ERRO CRÍTICO: String de conexão Oracle DSN não configurada.")
    else:
        conn_oracle_global = conectar_oracle_coletor() 

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=ID_CLIENTE_MQTT_COLETOR)
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            print(f"Coletor MQTT: A tentar ligar ao broker {BROKER_MQTT}...")
            client.connect(BROKER_MQTT, PORTA_MQTT, 60)
            client.loop_forever() 
        except KeyboardInterrupt:
            print("\nColetor MQTT: Programa interrompido pelo usuário.")
        except Exception as e:
            print(f"Coletor MQTT: Erro ao tentar ligar ou no loop do MQTT: {e}")
        finally:
            if client and client.is_connected(): client.disconnect() # Verifica se está conectado antes de desconectar
            print("Coletor MQTT: Desligado do Broker MQTT.")
            if conn_oracle_global: conn_oracle_global.close()
            print("Coletor MQTT: Conexão com Oracle DB fechada.")
