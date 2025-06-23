# -*- coding: utf-8 -*-
"""
Script para gerar um dataset sintético de dados climáticos e decisões de irrigação.

Simula condições para o Norte do Paraná ao longo de um ano, gerando 10.000
registros com variações sazonais de temperatura e umidade.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def gerar_dados_sinteticos(num_linhas=10000):
    """
    Gera um DataFrame com dados climáticos sintéticos e decisões de irrigação.
    """
    print("Iniciando a geração de dados sintéticos...")

    # --- 1. Definir o Período ---
    data_inicio = datetime(2024, 6, 21)
    datas = pd.to_datetime([data_inicio + timedelta(minutes=x * 52.56) for x in range(num_linhas)])

    # --- 2. Simular Variações Sazonais ---
    # O dia do ano vai de 0 a 365. Isso ajuda a criar uma curva senoidal para a temperatura.
    dia_do_ano = datas.dayofyear

    # Simulação da temperatura base com curva senoidal para as estações no hemisfério sul
    # Pico no verão (em torno do dia 350-365 e 1-50), vale no inverno (em torno do dia 172)
    temp_base = 22 + 8 * np.sin(2 * np.pi * (dia_do_ano - 260) / 365.25)
    
    # Adicionar ruído aleatório para variações diárias
    temp_real = temp_base + np.random.uniform(-3, 3, size=num_linhas)

    # Simulação da umidade
    umidade_base = 65 - 15 * np.sin(2 * np.pi * (dia_do_ano - 260) / 365.25)
    umidade_real = umidade_base + np.random.uniform(-10, 10, size=num_linhas)
    umidade_real = np.clip(umidade_real, 20, 100) # Manter umidade entre 20% e 100%

    # --- 3. Definir Condição do Tempo e Decisão da Bomba ---
    dados = []
    for i in range(num_linhas):
        temp_atual = temp_real[i]
        umidade_atual = umidade_real[i]
        condicao = "Céu Limpo" # Padrão
        
        # Lógica para definir condição do tempo
        rand_clima = np.random.rand()
        if umidade_atual > 85 and rand_clima > 0.3: # Alta chance de chuva com umidade alta
            condicao = "Chuvoso"
            if umidade_atual > 92 and rand_clima > 0.6:
                condicao = "Tempestade"
        elif umidade_atual > 70 and rand_clima > 0.5:
            condicao = "Nublado"

        # Ajustar temperatura com base na condição
        if condicao == "Chuvoso":
            temp_atual -= 3
        elif condicao == "Tempestade":
            temp_atual -= 5
        elif condicao == "Nublado":
            temp_atual -= 2

        # --- LÓGICA DE DECISÃO DA BOMBA (ESSENCIAL) ---
        comando_bomba = ""
        # Se estiver chovendo/tempestade, ou a umidade for muito alta, desliga a bomba
        if condicao in ["Chuvoso", "Tempestade"] or umidade_atual > 78:
            comando_bomba = "DESLIGAR_BOMBA"
        # Se a temperatura for muito baixa, também desliga
        elif temp_atual < 12:
            comando_bomba = "DESLIGAR_BOMBA"
        # Caso contrário, liga a bomba
        else:
            comando_bomba = "LIGAR_BOMBA"

        dados.append({
            "ID_LOG": i + 1,
            "TIMESTAMP_DECISAO": datas[i],
            "COMANDO_BOMBA": comando_bomba,
            "FONTE_DECISAO": "Sintetico",
            "CONDICAO_METEO_DESC": condicao,
            "UMIDADE_AR_API": round(umidade_atual, 2),
            "TEMPERATURA_API": round(temp_atual, 2),
            "ID_TEMPO_API": np.random.randint(200, 805) # ID aleatório
        })

    df_final = pd.DataFrame(dados)
    print("Geração de dados concluída.")
    return df_final

if __name__ == '__main__':
    df_sintetico = gerar_dados_sinteticos(num_linhas=10000)
    
    # Salvar o arquivo
    nome_arquivo_saida = 'dados_climaticos_sinteticos.csv'
    df_sintetico.to_csv(nome_arquivo_saida, index=False, encoding='utf-8')
    
    print(f"\n--- Processo Finalizado com Sucesso! ---")
    print(f"Arquivo '{nome_arquivo_saida}' com {len(df_sintetico)} linhas foi criado.")
    
    # Verificar e mostrar a distribuição das decisões
    distribuicao = df_sintetico['COMANDO_BOMBA'].value_counts()
    print("\nDistribuição das decisões no arquivo gerado:")
    print(distribuicao)
    print("\nAgora você pode usar este CSV para treinar um modelo muito mais robusto!")
