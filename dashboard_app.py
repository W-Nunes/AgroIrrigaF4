import streamlit as st
import pandas as pd
import cx_Oracle 
from datetime import datetime
import plotly.express as px

# --- Configurações Oracle ---
ORACLE_USER = "RM562839"
ORACLE_PASS = "120296" # Lembre-se de proteger esta senha
ORACLE_DSN = "oracle.fiap.com.br:1521/ORCL"

def carregar_dados_oracle():
    conn_oracle = None
    dfs = {} 
    try:
        conn_oracle = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASS, dsn=ORACLE_DSN)
        print("Dashboard: Conectado ao Oracle Database com sucesso.") # Para depuração na consola do Streamlit

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

        # Nova query para umidade do solo da tabela s_umidade_solo
        query_umidade_solo = "SELECT atualizado_em AS timestamp, nivel_umidade AS umidade FROM s_umidade_solo ORDER BY atualizado_em ASC"
        dfs['umidade_solo'] = pd.read_sql_query(query_umidade_solo, conn_oracle)
        if not dfs['umidade_solo'].empty:
            dfs['umidade_solo']['TIMESTAMP'] = pd.to_datetime(dfs['umidade_solo']['TIMESTAMP'])
        else: # Garante que o DataFrame exista mesmo que vazio para evitar erros no layout
            dfs['umidade_solo'] = pd.DataFrame(columns=['TIMESTAMP', 'UMIDADE'])


        print(f"Dados de pH carregados: {len(dfs['ph'])} registos")
        print(f"Dados de nutrientes carregados: {len(dfs['nutrientes'])} registos")
        print(f"Dados da bomba carregados: {len(dfs['bomba'])} registos")
        print(f"Dados de umidade do solo carregados: {len(dfs['umidade_solo'])} registos")

    except cx_Oracle.Error as e:
        error_obj, = e.args
        st.error(f"Erro ao conectar ou ler o banco de dados Oracle: {error_obj.message}")
        # Retorna dicionário com DataFrames vazios em caso de erro para evitar erros no restante do app
        dfs['ph'] = pd.DataFrame(columns=['TIMESTAMP', 'PH_ESTIMADO'])
        dfs['nutrientes'] = pd.DataFrame(columns=['TIMESTAMP', 'FOSFORO_STATUS', 'POTASSIO_STATUS', 'NIVEL_P', 'NIVEL_K'])
        dfs['bomba'] = pd.DataFrame(columns=['TIMESTAMP', 'BOMBA_STATUS_LEGIVEL', 'ESTADO_BOMBA_NUM'])
        dfs['umidade_solo'] = pd.DataFrame(columns=['TIMESTAMP', 'UMIDADE']) # Garante que exista em caso de erro
    finally:
        if conn_oracle:
            conn_oracle.close()
            print("Dashboard: Conexão com Oracle DB fechada.")
    return dfs

# --- Configuração da Página Streamlit ---
st.set_page_config(page_title="AgroIrriga Dashboard", layout="wide")

# Usar st.session_state para definir o nome da empresa uma vez
if 'company_name' not in st.session_state:
    st.session_state.company_name = "AgroIrriga - Soluções Tecnológicas"

st.title(f"🌱 {st.session_state.company_name} - Painel de Monitoramento da Irrigação")
st.markdown(f"Visualização dos dados do sistema de irrigação inteligente da {st.session_state.company_name}.")

if st.button("Recarregar Dados do Banco de Dados"):
    st.cache_data.clear() # Limpa o cache para forçar o recarregamento dos dados

@st.cache_data # Cache para melhorar o desempenho ao recarregar a página
def obter_dados_completos_caching():
    return carregar_dados_oracle()

dados_completos = obter_dados_completos_caching()

# Obter os DataFrames individuais do dicionário, com fallback para DataFrame vazio
df_ph = dados_completos.get('ph', pd.DataFrame(columns=['TIMESTAMP', 'PH_ESTIMADO']))
df_nutrientes = dados_completos.get('nutrientes', pd.DataFrame(columns=['TIMESTAMP', 'FOSFORO_STATUS', 'POTASSIO_STATUS', 'NIVEL_P', 'NIVEL_K']))
df_bomba = dados_completos.get('bomba', pd.DataFrame(columns=['TIMESTAMP', 'BOMBA_STATUS_LEGIVEL', 'ESTADO_BOMBA_NUM']))
df_umidade = dados_completos.get('umidade_solo', pd.DataFrame(columns=['TIMESTAMP', 'UMIDADE']))


if df_ph.empty and df_nutrientes.empty and df_bomba.empty and df_umidade.empty:
    st.warning("Nenhum dado para exibir. Verifique se o banco de dados Oracle contém dados nas tabelas s_ph, s_nutrientes, s_umidade_solo e log_controle_bomba.")
else:
    st.sidebar.header("Filtros e Opções")
    # Adicionar filtros aqui se necessário no futuro (ex: por data)

    st.header("📊 Visualizações dos Sensores e Atuadores")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💧 Umidade do Solo (%) ao Longo do Tempo")
        if not df_umidade.empty and 'UMIDADE' in df_umidade.columns and 'TIMESTAMP' in df_umidade.columns:
            fig_umidade = px.line(df_umidade, x='TIMESTAMP', y='UMIDADE', title="Umidade do Solo (DHT22)", markers=True)
            fig_umidade.update_layout(xaxis_title="Data e Hora", yaxis_title="Umidade do Solo (%)")
            st.plotly_chart(fig_umidade, use_container_width=True)
        else:
            st.info("Sem dados de umidade do solo para exibir.") # Mensagem atualizada

        st.subheader("🧪 Status dos Nutrientes (Última Leitura)")
        if not df_nutrientes.empty:
            ultima_leitura_nut = df_nutrientes.iloc[-1]
            st.metric(label="Fósforo (P)", value=ultima_leitura_nut['FOSFORO_STATUS'])
            st.metric(label="Potássio (K)", value=ultima_leitura_nut['POTASSIO_STATUS'])
        else:
            st.info("Sem dados de nutrientes para exibir o último status.")
            
    with col2:
        st.subheader("🌡️ pH Estimado ao Longo do Tempo")
        if not df_ph.empty and 'PH_ESTIMADO' in df_ph.columns and 'TIMESTAMP' in df_ph.columns:
            fig_ph = px.line(df_ph, x='TIMESTAMP', y='PH_ESTIMADO', title="pH Estimado do Solo (LDR Simulado)", markers=True)
            fig_ph.update_layout(xaxis_title="Data e Hora", yaxis_title="pH Estimado")
            st.plotly_chart(fig_ph, use_container_width=True)
        else:
            st.info("Sem dados de pH para exibir.")

        st.subheader("🌊 Estado da Bomba de Irrigação (Decisões da API)")
        if not df_bomba.empty and 'BOMBA_STATUS_LEGIVEL' in df_bomba.columns:
            contagem_bomba = df_bomba['BOMBA_STATUS_LEGIVEL'].value_counts().reset_index()
            contagem_bomba.columns = ['estado', 'contagem']
            fig_bomba_pie = px.pie(contagem_bomba, values='contagem', names='estado', 
                                   title="Proporção de Comandos para Bomba")
            st.plotly_chart(fig_bomba_pie, use_container_width=True)

            if 'TIMESTAMP' in df_bomba.columns and 'ESTADO_BOMBA_NUM' in df_bomba.columns:
                fig_bomba_eventos = px.line(df_bomba, x='TIMESTAMP', y='ESTADO_BOMBA_NUM', 
                                            title="Histórico de Comandos da Bomba (via API)", markers=False, line_shape='hv')
                fig_bomba_eventos.update_layout(yaxis_title="Comando (0=DESLIGAR, 1=LIGAR)", xaxis_title="Data e Hora da Decisão")
                fig_bomba_eventos.update_yaxes(tickvals=[0, 1], ticktext=['DESLIGAR', 'LIGAR'])
                st.plotly_chart(fig_bomba_eventos, use_container_width=True)
        else:
            st.info("Sem dados de controle da bomba (via API) para exibir.")
            
    st.sidebar.markdown("---")
    total_leituras = len(df_ph) + len(df_nutrientes) + len(df_bomba) + len(df_umidade)
    st.sidebar.info(f"Total de registos carregados das tabelas: {total_leituras}")
    
    st.markdown("---")
    st.caption(f"Dashboard {st.session_state.company_name} - Desenvolvido com Streamlit")
