# ============================================================
# dashboard/data.py — Carregamento e cache de dados
# ============================================================
# Conecta ao PostgreSQL (Neon) via DATABASE_URL.
# A URL pode vir de:
#   1. Variável de ambiente (uso local)
#   2. Streamlit Secrets (uso no Streamlit Cloud)
# ============================================================

import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine


# ==================== CONEXÃO ====================
def _obter_database_url():
    """
    Tenta obter a DATABASE_URL de várias fontes:
        1. Streamlit Secrets (prioridade — funciona na nuvem)
        2. Variável de ambiente (uso local)
    """
    # 1. Streamlit Secrets
    try:
        url = st.secrets.get('DATABASE_URL')
        if url:
            return url
    except Exception:
        pass

    # 2. Variável de ambiente
    url = os.environ.get('DATABASE_URL')
    if url:
        return url

    # Nada encontrado
    return None


def _limpar_url(url):
    """Remove parâmetros problemáticos do Neon."""
    if not url:
        return url
    url = url.replace('&channel_binding=require', '')
    url = url.replace('?channel_binding=require&', '?')
    url = url.replace('?channel_binding=require', '')
    return url


@st.cache_resource
def get_engine():
    """
    Cria engine do PostgreSQL (cached).
    Retorna None se a URL não estiver configurada.
    """
    url = _obter_database_url()

    if not url:
        return None

    url = _limpar_url(url)

    try:
        engine = create_engine(
            url,
            pool_pre_ping=True,      # valida conexão antes de usar
            pool_recycle=3600,       # recicla conexões antigas
            connect_args={
                'connect_timeout': 10,
                'sslmode': 'require',
            },
        )
        return engine
    except Exception as e:
        st.error(f'❌ Erro ao criar engine: {e}')
        return None


def _executar_query(sql):
    """Executa uma query e retorna DataFrame. Lança exceção se falhar."""
    engine = get_engine()

    if engine is None:
        raise RuntimeError(
            'DATABASE_URL não configurada. '
            'Adicione nos Secrets do Streamlit Cloud ou em variável de ambiente.'
        )

    return pd.read_sql(sql, engine)


# ==================== FUNÇÕES DE CARREGAMENTO ====================
@st.cache_data(ttl=300)
def carregar_tickets():
    """Carrega todos os tickets do banco com colunas derivadas."""
    try:
        df = _executar_query('SELECT * FROM tickets')
    except Exception as e:
        st.error(f'❌ Erro ao carregar tickets: {e}')
        return None

    if df.empty:
        return df

    # Converte colunas de data
    colunas_data = ['criado_data', 'alterado_data', 'previsao',
                    'data_resolvido', 'data_1_resolvido',
                    'previsao_esperada', 'snapshot_data']
    for col in colunas_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Colunas derivadas
    df['dias_aberto'] = (pd.Timestamp.now() - df['criado_data']).dt.days
    df['dias_resolucao'] = (df['data_resolvido'] - df['criado_data']).dt.days
    df['dias_1a_resposta'] = (df['data_1_resolvido'] - df['criado_data']).dt.days

    # Status SLA
    df['sla_status'] = 'em_andamento'
    mask = df['data_resolvido'].notna() & df['previsao'].notna()
    df.loc[mask & (df['data_resolvido'] <= df['previsao']), 'sla_status'] = 'cumprido'
    df.loc[mask & (df['data_resolvido'] > df['previsao']), 'sla_status'] = 'estourado'

    return df


@st.cache_data(ttl=300)
def carregar_snapshots():
    """Histórico de snapshots (execuções do pipeline)."""
    try:
        df = _executar_query(
            'SELECT * FROM snapshots ORDER BY data_execucao DESC'
        )
        if 'data_execucao' in df.columns:
            df['data_execucao'] = pd.to_datetime(df['data_execucao'], errors='coerce')
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def carregar_movimentacoes():
    """Movimentações (histórico de status)."""
    try:
        df = _executar_query('SELECT * FROM movimentacoes')
        if 'data_movimentacao' in df.columns:
            df['data_movimentacao'] = pd.to_datetime(
                df['data_movimentacao'], errors='coerce'
            )
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def carregar_mensagens():
    """Mensagens (área de fluxo)."""
    try:
        df = _executar_query('SELECT * FROM mensagens')
        if 'data_hora' in df.columns:
            df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce')
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def carregar_analistas():
    """Analistas (tabela de cadastro)."""
    try:
        return _executar_query(
            'SELECT nome, email, empresa_tipo FROM analistas'
        )
    except Exception:
        return pd.DataFrame()