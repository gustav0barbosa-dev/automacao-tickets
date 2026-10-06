# ============================================================
# dashboard/data.py — Carregamento e cache de dados
# ============================================================
# Conecta ao banco em 3 modos:
#   1. DATABASE_URL (env var) — Railway
#   2. Streamlit Secrets      — Streamlit Cloud
#   3. SQLite local           — dev / testes
# ============================================================

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine


# ==================== CONEXÃO ====================
def _obter_database_url():
    """
    Tenta obter a URL do banco em ordem de prioridade:
        1. Streamlit Secrets (formato [connections.postgresql] url = ...)
        2. Streamlit Secrets (chave direta DATABASE_URL)
        3. Variável de ambiente (Railway)
        4. SQLite local (fallback para desenvolvimento)
    """
    # 1. Streamlit Secrets — formato [connections.postgresql]
    try:
        url = st.secrets["connections"]["postgresql"]["url"]
        if url:
            return url
    except (KeyError, FileNotFoundError, Exception):
        pass

    # 2. Streamlit Secrets — chave direta DATABASE_URL
    try:
        url = st.secrets.get("DATABASE_URL")
        if url:
            return url
    except Exception:
        pass

    # 3. Variável de ambiente (Railway)
    url = os.environ.get('DATABASE_URL')
    if url:
        return url

    # 4. Fallback: SQLite local (só pra DEV)
    sqlite_path = Path(__file__).resolve().parent.parent / 'dados' / 'tickets.db'
    if sqlite_path.exists():
        st.info(f'ℹ️ Usando SQLite local: {sqlite_path.name}')
        return f'sqlite:///{sqlite_path}'

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
    """Cria engine do banco (cached)."""
    url = _obter_database_url()
    if not url:
        return None

    # SQLite (local)
    if url.startswith('sqlite:///'):
        return create_engine(
            url,
            connect_args={'check_same_thread': False},
        )

    # Postgres (Neon/Railway)
    url = _limpar_url(url)
    try:
        engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,
            max_overflow=10,
            connect_args={
                'connect_timeout': 30,
                'sslmode': 'require',
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
            },
        )
        return engine
    except Exception as e:
        st.error(f'Erro ao criar engine: {e}')
        return None

# ==================== CARREGAMENTO ====================
@st.cache_data(ttl=3600)
def carregar_tickets():
    engine = get_engine()
    if engine is None:
        return pd.DataFrame()

    try:
        df = pd.read_sql('SELECT * FROM tickets', engine)
    except Exception as e:
        st.error(f'Erro ao carregar tickets: {e}')
        return pd.DataFrame()

    if df.empty:
        return df

    # ---------- CONVERSÕES DE TIPO ----------
    for col in ['criado_data', 'alterado_data', 'previsao',
                'data_resolvido', 'data_1_resolvido']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    if 'id' in df.columns:
        df['id'] = pd.to_numeric(df['id'], errors='coerce').astype('Int64')

    # ---------- COLUNAS DERIVADAS ----------
    hoje = pd.Timestamp.now()

    # dias_aberto: dias desde criado_data (só pra tickets em aberto)
    if 'dias_aberto' not in df.columns:
        df['dias_aberto'] = (hoje - df['criado_data']).dt.days

    # dias_resolucao: dias entre criado_data e data_resolvido
    if 'dias_resolucao' not in df.columns:
        if 'data_resolvido' in df.columns:
            df['dias_resolucao'] = (
                df['data_resolvido'] - df['criado_data']
            ).dt.days

    # dias_1_resolucao: dias até a primeira resolução
    if 'dias_1_resolucao' not in df.columns:
        if 'data_1_resolvido' in df.columns:
            df['dias_1_resolucao'] = (
                df['data_1_resolvido'] - df['criado_data']
            ).dt.days

    # sla_status: cumprido / estourado
    if 'sla_status' not in df.columns:
        if 'previsao' in df.columns and 'data_resolvido' in df.columns:
            df['sla_status'] = None
            mask = df['data_resolvido'].notna() & df['previsao'].notna()
            df.loc[mask & (df['data_resolvido'] <= df['previsao']), 'sla_status'] = 'cumprido'
            df.loc[mask & (df['data_resolvido'] > df['previsao']), 'sla_status'] = 'estourado'

    # status_resolvido: True/False
    if 'status_resolvido' not in df.columns and 'status' in df.columns:
        df['status_resolvido'] = df['status'].isin(['Resolvido', 'Fechado'])

    return df


@st.cache_data(ttl=300)
def carregar_movimentacoes():
    """Carrega a tabela `movimentacoes` do banco."""
    engine = get_engine()
    if engine is None:
        return pd.DataFrame()

    try:
        df = pd.read_sql('SELECT * FROM movimentacoes', engine)
    except Exception as e:
        st.warning(f'⚠️ Erro ao carregar movimentações: {e}')
        return pd.DataFrame()

    if not df.empty:
        if 'data_movimentacao' in df.columns:
            df['data_movimentacao'] = pd.to_datetime(
                df['data_movimentacao'], errors='coerce'
            )
        if 'ticket_id' in df.columns:
            df['ticket_id'] = pd.to_numeric(df['ticket_id'], errors='coerce')

    return df


@st.cache_data(ttl=300)
def carregar_mensagens():
    """Carrega a tabela `mensagens` do banco."""
    engine = get_engine()
    if engine is None:
        return pd.DataFrame()

    try:
        df = pd.read_sql('SELECT * FROM mensagens', engine)
    except Exception as e:
        st.warning(f'⚠️ Erro ao carregar mensagens: {e}')
        return pd.DataFrame()

    if not df.empty:
        if 'data_hora' in df.columns:
            df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce')
        if 'ticket_id' in df.columns:
            df['ticket_id'] = pd.to_numeric(df['ticket_id'], errors='coerce')

    return df

@st.cache_data(ttl=300)
def carregar_analistas():
    """
    Carrega a tabela `analistas` do banco.
    Usada pela view de Roteamento.
    """
    engine = get_engine()
    if engine is None:
        return pd.DataFrame()

    try:
        df = pd.read_sql('SELECT * FROM analistas', engine)
    except Exception as e:
        st.warning(f'⚠️ Erro ao carregar analistas: {e}')
        return pd.DataFrame()

    return df

@st.cache_data(ttl=300)
def carregar_movimentacoes():
    """Carrega a tabela `movimentacoes` do banco."""
    engine = get_engine()
    if engine is None:
        return pd.DataFrame()

    try:
        df = pd.read_sql('SELECT * FROM movimentacoes', engine)
    except Exception as e:
        st.warning(f'⚠️ Erro ao carregar movimentações: {e}')
        return pd.DataFrame()

    if not df.empty:
        if 'data_movimentacao' in df.columns:
            df['data_movimentacao'] = pd.to_datetime(
                df['data_movimentacao'], errors='coerce'
            )
        if 'ticket_id' in df.columns:
            df['ticket_id'] = pd.to_numeric(df['ticket_id'], errors='coerce')

    return df


@st.cache_data(ttl=300)
def carregar_mensagens():
    """Carrega a tabela `mensagens` do banco."""
    engine = get_engine()
    if engine is None:
        return pd.DataFrame()

    try:
        df = pd.read_sql('SELECT * FROM mensagens', engine)
    except Exception as e:
        st.warning(f'⚠️ Erro ao carregar mensagens: {e}')
        return pd.DataFrame()

    if not df.empty:
        if 'data_hora' in df.columns:
            df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce')
        if 'ticket_id' in df.columns:
            df['ticket_id'] = pd.to_numeric(df['ticket_id'], errors='coerce')

    return df