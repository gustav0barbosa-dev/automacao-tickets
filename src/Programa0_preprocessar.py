# ============================================================
# Programa0_preprocessar.py
# Processa a "Tickets - Tabela fato.xlsx" (diário de anotações)
# e gera APENAS 'tickets_com_respondido.xlsx' (ID + Data Respondido)
#
# IMPORTANTE: Este programa NÃO gera 'tickets.xlsx' — essa base
# completa de tickets é baixada pelo Programa1 do site do Help360.
# ============================================================

import pandas as pd
import numpy as np
import re
import os
from datetime import datetime


def localizar_arquivo_tabela_fato():
    """Procura a planilha de anotações (Tabela fato)."""
    caminhos = [
        os.path.join(os.path.expanduser('~'), 'Downloads', 'Tickets - Tabela fato.xlsx'),
        'Tickets - Tabela fato.xlsx'
    ]
    for caminho in caminhos:
        if os.path.exists(caminho):
            return caminho
    return None


def extrair_ultima_data(texto, ano_referencia=None):
    """
    Extrai a data/hora MAIS RECENTE de um texto da Tabela fato.

    Suporta:
      - Strings com uma ou mais datas: 'DD/MM/AAAA', 'DD/MM/AAAA HH:MM', 'DD/MM'
      - Datas nativas do pandas/Excel (Timestamp / datetime)
      - Números de série do Excel (ex: 46250.5847)

    Ignora: '0', '0.0', '-', '#N/A', '#VALUE!', 'nan', 'NaN', 'None', '', NaN/NaT.
    """
    if ano_referencia is None:
        ano_referencia = datetime.now().year

    # --- Caso 1: já é data nativa do pandas ou datetime ---
    if isinstance(texto, (pd.Timestamp, datetime)):
        return texto

    # --- Caso 2: vazio / nulo ---
    if pd.isna(texto):
        return None

    # --- Caso 3: número de série do Excel (float/int, ex: 46250.5847) ---
    if isinstance(texto, (int, float)) and not isinstance(texto, bool):
        # Se for 0, ignora (lixo comum na Tabela fato)
        if texto == 0:
            return None
        try:
            # Número de série do Excel: dias desde 30/12/1899
            if texto > 1000:  # abaixo disso não é data válida no Excel
                return pd.to_datetime(texto, unit='D', origin='1899-12-30')
        except Exception:
            return None

    # --- Caso 4: string com texto ---
    texto_str = str(texto).strip()
    if texto_str in ('', '0', '0.0', '-', '#N/A', '#VALUE!', 'nan', 'NaN', 'None'):
        return None

    datas_encontradas = []

    # Padrão completo: DD/MM/AAAA (com hora opcional)
    padrao_completo = r'(\d{2}/\d{2}/\d{4})(?:\s*[-:]?\s*(\d{2}:\d{2}))?'
    for match in re.finditer(padrao_completo, texto_str):
        data_str, hora_str = match.groups()
        try:
            if hora_str:
                dt = datetime.strptime(f'{data_str} {hora_str}', '%d/%m/%Y %H:%M')
            else:
                dt = datetime.strptime(data_str, '%d/%m/%Y')
            datas_encontradas.append(dt)
        except ValueError:
            pass

    # Padrão curto: DD/MM (sem ano) — o lookahead evita capturar parte de DD/MM/AAAA
    padrao_curto = r'(\d{2}/\d{2})(?!\/\d{4})(?:\s*[-:]?\s*(\d{2}:\d{2}))?'
    for match in re.finditer(padrao_curto, texto_str):
        data_str, hora_str = match.groups()
        try:
            if hora_str:
                dt = datetime.strptime(
                    f'{data_str}/{ano_referencia} {hora_str}', '%d/%m/%Y %H:%M')
            else:
                dt = datetime.strptime(
                    f'{data_str}/{ano_referencia}', '%d/%m/%Y')
            datas_encontradas.append(dt)
        except ValueError:
            pass

    # Retorna a MAIOR data encontrada no histórico do registro
    return max(datas_encontradas) if datas_encontradas else None


def extrair_anotacoes(df_acomp, df_status):
    """
    Extrai a data da ÚLTIMA anotação VÁLIDA de cada ticket.
    Itera da última coluna para trás e usa a data mais recente encontrada.
    """
    df_status = df_status.copy()
    df_status['ID'] = df_status['ID'].astype(str).str.strip()
    df_acomp = df_acomp.copy()
    df_acomp['ID'] = df_acomp['ID'].astype(str).str.strip()

    colunas_datas = [col for col in df_acomp.columns if col != 'ID']
    anotacoes = []

    for _, row in df_acomp.iterrows():
        ticket_id = row['ID']
        ultima_data = pd.NaT

        # Itera da última coluna de data para trás
        for col in reversed(colunas_datas):
            valor = row[col]
            data_extraida = extrair_ultima_data(valor)
            if data_extraida is not None:
                try:
                    ultima_data = pd.Timestamp(data_extraida)
                except Exception:
                    ultima_data = pd.NaT
                break  # achou a data mais recente → para

        anotacoes.append({
            'ID': ticket_id,
            'Data Respondido': ultima_data
        })

    df_anotacoes = pd.DataFrame(anotacoes)

    # Garante que TODOS os IDs da aba Status estejam no resultado.
    # Se um ID não tiver anotação, ele entra com Data Respondido = NaT.
    df_ids_completos = df_status[['ID']].drop_duplicates()
    df_final = df_ids_completos.merge(df_anotacoes, on='ID', how='left')
    df_final['Data Respondido'] = pd.to_datetime(df_final['Data Respondido'], errors='coerce')

    return df_final


def gerar_respondidos_xlsx(df_anotacoes):
    """Gera 'tickets_com_respondido.xlsx' com ID e Data Respondido."""
    caminho_saida = os.path.join(
        os.path.expanduser('~'), 'Downloads', 'tickets_com_respondido.xlsx')

    df_resp = df_anotacoes.copy()
    df_resp.to_excel(caminho_saida, index=False)

    total = len(df_resp)
    respondidos = df_resp['Data Respondido'].notna().sum()
    pendentes = total - respondidos

    print(f"✅ 'tickets_com_respondido.xlsx' gerado em: {caminho_saida}")
    print(f"   -> {total} registros ({respondidos} respondidos, {pendentes} pendentes)")
    return df_resp


def main():
    print("=" * 60)
    print("PROGRAMA 0 - PRÉ-PROCESSAMENTO DA TABELA FATO")
    print("(gera APENAS 'tickets_com_respondido.xlsx')")
    print("=" * 60)

    arquivo = localizar_arquivo_tabela_fato()
    if not arquivo:
        print("⚠️ Arquivo 'Tickets - Tabela fato.xlsx' não encontrado.")
        print("   Pulando pré-processamento.")
        return False

    print(f"📂 Arquivo encontrado: {arquivo}")

    try:
        xls = pd.ExcelFile(arquivo)
        df_status = pd.read_excel(xls, sheet_name='Status')
        df_acomp = pd.read_excel(xls, sheet_name='Acompanhamento')
    except Exception as e:
        print(f"❌ Erro ao ler as abas: {e}")
        return False

    df_anotacoes = extrair_anotacoes(df_acomp, df_status)
    gerar_respondidos_xlsx(df_anotacoes)

    print("\n✅ Pré-processamento concluído!")
    return True


if __name__ == "__main__":
    main()