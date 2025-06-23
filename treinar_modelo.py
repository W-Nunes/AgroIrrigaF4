"""
Script para treinar e salvar o modelo de Machine Learning para o projeto AgroIrriga.

Este script realiza os seguintes passos:
1. Carrega os dados do arquivo 'controle_bombar.csv'.
2. Limpa os dados, removendo colunas desnecessárias.
3. Separa os dados em features (X) e alvo (y).
4. Codifica a variável alvo (de texto para número).
5. Treina um modelo de classificação (Random Forest).
6. Salva o modelo treinado, o codificador e a lista de colunas em arquivos .joblib.
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib
import os

def treinar_e_salvar_modelo():
    """
    Função principal que executa todo o processo de treinamento e salvamento.
    """
    # --- 1. Carregar os Dados ---
    caminho_csv = 'dados_climaticos_sinteticos.csv'
    if not os.path.exists(caminho_csv):
        print(f"Erro: Arquivo '{caminho_csv}' não encontrado.")
        print("Por favor, coloque este script na mesma pasta que o seu arquivo CSV.")
        return

    print("Carregando dados do CSV...")
    df = pd.read_csv(caminho_csv)
    
    # --- 2. Limpeza dos Dados ---
    print("Limpando e preparando os dados...")
    # Nomes das colunas em maiúsculas, conforme o arquivo
    colunas_para_remover = [
        'ID_LOG',
        'TIMESTAMP_DECISAO',
        'FONTE_DECISAO',
        'CONDICAO_METEO_DESC',
        'ID_TEMPO_API'
    ]
    df_limpo = df.drop(columns=colunas_para_remover)

    # Tratar valores ausentes (se houver)
    for coluna in df_limpo.select_dtypes(include=['float64', 'int64']).columns:
        df_limpo[coluna].fillna(df_limpo[coluna].mean(), inplace=True)

    # --- 3. Preparação para o Modelo ---
    X = df_limpo.drop('COMANDO_BOMBA', axis=1)
    y = df_limpo['COMANDO_BOMBA']

    # Codificar a variável alvo (COMANDO_BOMBA)
    le = LabelEncoder()
    y_codificado = le.fit_transform(y)

    # --- 4. Treinamento do Modelo ---
    print("Treinando o modelo de Machine Learning...")
    # Usando RandomForestClassifier, um modelo robusto
    modelo = RandomForestClassifier(n_estimators=100, random_state=42)
    modelo.fit(X, y_codificado)
    print("Treinamento concluído!")

    # --- 5. Salvando os Arquivos ---
    print("Salvando os arquivos do modelo...")
    
    # Salva o modelo treinado
    joblib.dump(modelo, 'modelo_irrigacao_preditivo.joblib')
    
    # Salva o codificador (para traduzir a previsão de volta para texto)
    joblib.dump(le, 'label_encoder.joblib')

    # Salva os nomes das colunas usadas no treino (importante para o dashboard)
    colunas_do_modelo = list(X.columns)
    joblib.dump(colunas_do_modelo, 'model_columns.joblib')

    print("\n--- Processo Finalizado com Sucesso! ---")
    print("Os seguintes arquivos foram criados na sua pasta:")
    print("- modelo_irrigacao_preditivo.joblib")
    print("- label_encoder.joblib")
    print("- model_columns.joblib")
    print("Agora você já pode executar o seu dashboard Streamlit!")

if __name__ == '__main__':
    treinar_e_salvar_modelo()
