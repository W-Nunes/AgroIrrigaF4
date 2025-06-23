import streamlit as st
import pandas as pd
import cx_Oracle 
from datetime import datetime
import plotly.express as px
import joblib # Para carregar o modelo de ML
import os

# --- Configurações da Página Streamlit ---
st.set_page_config(page_title="AgroIrriga Dashboard F4", layout="wide")

# Usar st.session_state para definir o nome da empresa uma vez
if 'company_name' not in st.session_state:
    st.session_state.company_name = "AgroIrriga - Soluções Tecnológicas"

st.title(f"🌱 {st.session_state.company_name}")
st.markdown(f"Visualização dos dados do sistema de irrigação inteligente!!")


# --- Carregamento do Modelo de Machine Learning ---
# Carregar o modelo, o codificador e as colunas (se existirem)
model = None
le = None
model_columns = None

try:
    model_path = 'modelo_irrigacao_preditivo.joblib'
    encoder_path = 'label_encoder.joblib'
    columns_path = 'model_columns.joblib'

    if os.path.exists(model_path):
        model = joblib.load(model_path)
        st.sidebar.success("Modelo de ML carregado!")
    else:
        st.sidebar.error("Arquivo do modelo não encontrado.")

    if os.path.exists(encoder_path):
        le = joblib.load(encoder_path)
    else:
        st.sidebar.error("Arquivo do LabelEncoder não encontrado.")
    
    if os.path.exists(columns_path):
        model_columns = joblib.load(columns_path)
    else:
        st.sidebar.error("Arquivo de colunas do modelo não encontrado.")

except Exception as e:
    st.sidebar.error(f"Erro ao carregar arquivos do modelo: {e}")


# --- Nova Seção: Modelo Preditivo ---
st.header("🤖 Modelo Preditivo de Irrigação")
st.markdown("Use os controles abaixo para simular condições e obter uma recomendação do nosso modelo de IA sobre a necessidade de irrigação.")

col_pred1, col_pred2 = st.columns([2, 1])

with col_pred1:
    st.subheader("Simular Condições Atuais")
    
    # Usar as colunas do modelo para criar os inputs dinamicamente
    if model_columns:
        # Criar sliders para as features do modelo
        umidade_input = st.slider(
            "Umidade do Ar da API (%)", 
            min_value=0, 
            max_value=100, 
            value=70,
            help="Simule a umidade do ar reportada pela API meteorológica."
        )
        temperatura_input = st.slider(
            "Temperatura da API (°C)", 
            min_value=-10.0, 
            max_value=50.0, 
            value=25.0, 
            step=0.5,
            help="Simule a temperatura reportada pela API meteorológica."
        )
    else:
        st.warning("As colunas do modelo não foram carregadas. Inputs manuais desativados.")

with col_pred2:
    st.subheader("Recomendação do Modelo")
    if st.button("Verificar Recomendação"):
        if model and le and model_columns:
            # Criar um DataFrame com os dados de entrada
            input_data = pd.DataFrame([[umidade_input, temperatura_input]], columns=model_columns)
            
            # Fazer a predição
            prediction_numeric = model.predict(input_data)
            
            # Decodificar o resultado para texto
            prediction_text = le.inverse_transform(prediction_numeric)
            
            st.markdown("---")
            if prediction_text[0] == 'LIGAR_BOMBA':
                st.success(f"**Recomendação: {prediction_text[0]}**")
                st.info("O modelo sugere que as condições são favoráveis para a irrigação.")
            else:
                st.error(f"**Recomendação: {prediction_text[0]}**")
                st.warning("O modelo sugere que a irrigação não é necessária no momento.")
            st.markdown("---")
        else:
            st.error("Modelo não carregado. Não é possível fazer a previsão.")

st.markdown("---")


# --- SEÇÃO DE DADOS DO BANCO ORACLE ---

st.header("📊 Visualizações dos Sensores em Tempo Real (do Banco de Dados)")

# --- Configurações Oracle ---
ORACLE_USER = "RM562839"
ORACLE_PASS = "120296" 
ORACLE_DSN = "oracle.fiap.com.br:1521/ORCL"

@st.cache_data(ttl=300) # Cache de 5 minutos para os dados do Oracle
def carregar_dados_oracle():
    conn_oracle = None
    dfs = {} 
    try:
        conn_oracle = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASS, dsn=ORACLE_DSN)
        
        # Query para dados de pH da tabela s_ph
        query_ph = "SELECT atualizado_em AS timestamp, nivel_ph AS ph_estimado FROM s_ph ORDER BY atualizado_em ASC"
        dfs['ph'] = pd.read_sql_query(query_ph, conn_oracle)
        if not dfs['ph'].empty: dfs['ph']['TIMESTAMP'] = pd.to_datetime(dfs['ph']['TIMESTAMP'])

        # Query para dados de nutrientes da tabela s_nutrientes
        query_nutrientes = """
            SELECT atualizado_em AS timestamp, presenca_p, presenca_k, nivel_p, nivel_k
            FROM s_nutrientes ORDER BY atualizado_em ASC
        """
        dfs['nutrientes'] = pd.read_sql_query(query_nutrientes, conn_oracle)
        if not dfs['nutrientes'].empty:
            dfs['nutrientes']['TIMESTAMP'] = pd.to_datetime(dfs['nutrientes']['TIMESTAMP'])
            dfs['nutrientes']['FOSFORO_STATUS'] = dfs['nutrientes']['PRESENCA_P'].apply(lambda x: 'Presente' if x == 1 else 'Ausente')
            dfs['nutrientes']['POTASSIO_STATUS'] = dfs['nutrientes']['PRESENCA_K'].apply(lambda x: 'Presente' if x == 1 else 'Ausente')

        # Query para log de controle da bomba
        query_bomba = """
            SELECT timestamp_decisao AS timestamp, comando_bomba, condicao_meteo_desc, 
                   umidade_ar_api, temperatura_api 
            FROM log_controle_bomba ORDER BY timestamp_decisao ASC
        """
        dfs['bomba'] = pd.read_sql_query(query_bomba, conn_oracle)
        if not dfs['bomba'].empty:
            dfs['bomba']['TIMESTAMP'] = pd.to_datetime(dfs['bomba']['TIMESTAMP'])
            dfs['bomba']['ESTADO_BOMBA_NUM'] = dfs['bomba']['COMANDO_BOMBA'].apply(lambda x: 1 if x == 'LIGAR_BOMBA' else 0)
            dfs['bomba']['BOMBA_STATUS_LEGIVEL'] = dfs['bomba']['COMANDO_BOMBA'].apply(lambda x: 'LIGADA' if x == 'LIGAR_BOMBA' else 'DESLIGADA')

        # Query para umidade do solo da tabela s_umidade_solo
        query_umidade_solo = "SELECT atualizado_em AS timestamp, nivel_umidade AS umidade FROM s_umidade_solo ORDER BY atualizado_em ASC"
        dfs['umidade_solo'] = pd.read_sql_query(query_umidade_solo, conn_oracle)
        if not dfs['umidade_solo'].empty:
            dfs['umidade_solo']['TIMESTAMP'] = pd.to_datetime(dfs['umidade_solo']['TIMESTAMP'])
        
    except cx_Oracle.Error as e:
        error_obj, = e.args
        st.error(f"Erro ao conectar ou ler o banco de dados Oracle: {error_obj.message}")
        # Retorna dicionário com DataFrames vazios para evitar erros
        dfs = {
            'ph': pd.DataFrame(columns=['TIMESTAMP', 'PH_ESTIMADO']),
            'nutrientes': pd.DataFrame(columns=['TIMESTAMP', 'FOSFORO_STATUS', 'POTASSIO_STATUS']),
            'bomba': pd.DataFrame(columns=['TIMESTAMP', 'BOMBA_STATUS_LEGIVEL']),
            'umidade_solo': pd.DataFrame(columns=['TIMESTAMP', 'UMIDADE'])
        }
    finally:
        if conn_oracle:
            conn_oracle.close()
    return dfs

if st.sidebar.button("Recarregar Dados do Banco de Dados"):
    st.cache_data.clear()

dados_completos = carregar_dados_oracle()
df_ph = dados_completos.get('ph', pd.DataFrame())
df_nutrientes = dados_completos.get('nutrientes', pd.DataFrame())
df_bomba = dados_completos.get('bomba', pd.DataFrame())
df_umidade = dados_completos.get('umidade_solo', pd.DataFrame())

if all(df.empty for df in dados_completos.values()):
    st.warning("Nenhum dado para exibir do banco Oracle. Verifique a conexão e se as tabelas contêm dados.")
else:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💧 Umidade do Solo (%) ao Longo do Tempo")
        if not df_umidade.empty:
            fig_umidade = px.line(df_umidade, x='TIMESTAMP', y='UMIDADE', title="Umidade do Solo (DHT22)", markers=True)
            st.plotly_chart(fig_umidade, use_container_width=True)
        else:
            st.info("Sem dados de umidade do solo para exibir.")

        st.subheader("🧪 Status dos Nutrientes (Última Leitura)")
        if not df_nutrientes.empty:
            ultima_leitura_nut = df_nutrientes.iloc[-1]
            st.metric(label="Fósforo (P)", value=ultima_leitura_nut['FOSFORO_STATUS'])
            st.metric(label="Potássio (K)", value=ultima_leitura_nut['POTASSIO_STATUS'])
        else:
            st.info("Sem dados de nutrientes para exibir.")
            
    with col2:
        st.subheader("🌡️ pH Estimado ao Longo do Tempo")
        if not df_ph.empty:
            fig_ph = px.line(df_ph, x='TIMESTAMP', y='PH_ESTIMADO', title="pH Estimado do Solo (LDR Simulado)", markers=True)
            st.plotly_chart(fig_ph, use_container_width=True)
        else:
            st.info("Sem dados de pH para exibir.")

        st.subheader("🌊 Estado da Bomba de Irrigação (Decisões da API)")
        if not df_bomba.empty:
            contagem_bomba = df_bomba['BOMBA_STATUS_LEGIVEL'].value_counts().reset_index()
            contagem_bomba.columns = ['estado', 'contagem']
            fig_bomba_pie = px.pie(contagem_bomba, values='contagem', names='estado', title="Proporção de Comandos para Bomba")
            st.plotly_chart(fig_bomba_pie, use_container_width=True)
        else:
            st.info("Sem dados de controle da bomba para exibir.")
