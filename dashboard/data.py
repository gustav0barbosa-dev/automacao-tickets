# ============================================================
# dashboard/data.py — Carregamento e cache de dados
# ============================================================

import sqlite3
import pandas as pd
import streamlit as st

from config import CAMINHO_BANCO


@st.cache_data(ttl=300)
def carregar_tickets():
    """Carrega todos os tickets do banco com colunas derivadas."""
    if not CAMINHO_BANCO.exists():
        return None

    conn = sqlite3.connect(CAMINHO_BANCO)
    df = pd.read_sql('SELECT * FROM tickets', conn)
    conn.close()

    for col in ['criado_data', 'alterado_data', 'previsao',
                'data_resolvido', 'data_1_resolvido']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    df['dias_aberto'] = (pd.Timestamp.now() - df['criado_data']).dt.days
    df['dias_resolucao'] = (df['data_resolvido'] - df['criado_data']).dt.days
    df['dias_1a_resposta'] = (df['data_1_resolvido'] - df['criado_data']).dt.days

    df['sla_status'] = 'em_andamento'
    mask = df['data_resolvido'].notna()
    df.loc[mask & (df['data_resolvido'] <= df['previsao']), 'sla_status'] = 'cumprido'
    df.loc[mask & (df['data_resolvido'] > df['previsao']), 'sla_status'] = 'estourado'

    return df


@st.cache_data(ttl=300)
def carregar_snapshots():
    """Histórico de snapshots (execuções do pipeline)."""
    if not CAMINHO_BANCO.exists():
        return None

    conn = sqlite3.connect(CAMINHO_BANCO)
    df = pd.read_sql('SELECT * FROM snapshots ORDER BY data_execucao DESC', conn)
    conn.close()

    if 'data_execucao' in df.columns:
        df['data_execucao'] = pd.to_datetime(df['data_execucao'], errors='coerce')
    return df


@st.cache_data(ttl=300)
def carregar_movimentacoes():
    if not CAMINHO_BANCO.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(CAMINHO_BANCO)
    df = pd.read_sql('SELECT * FROM movimentacoes', conn)
    conn.close()
    if 'data_movimentacao' in df.columns:
        df['data_movimentacao'] = pd.to_datetime(df['data_movimentacao'], errors='coerce')
    return df


@st.cache_data(ttl=300)
def carregar_mensagens():
    if not CAMINHO_BANCO.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(CAMINHO_BANCO)
    df = pd.read_sql('SELECT * FROM mensagens', conn)
    conn.close()
    if 'data_hora' in df.columns:
        df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce')
    return df

@st.cache_data(ttl=300)
def carregar_analistas():
    """Carrega a tabela de analistas."""
    if not CAMINHO_BANCO.exists():
        return pd.DataFrame()

    conn = sqlite3.connect(CAMINHO_BANCO)
    df = pd.read_sql('SELECT nome, email, empresa_tipo FROM analistas', conn)
    conn.close()
    return df