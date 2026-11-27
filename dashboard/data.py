# ============================================================
# dashboard/data.py — Carregamento de dados via Neon Data API
# ============================================================
"""
Acesso aos dados do dashboard via HTTP (Neon Data API / PostgREST).

Não há mais SQLAlchemy, psycopg2 ou engine de banco: todas as consultas
são GETs autenticados com o JWT obtido em dashboard/auth.py.

IMPORTANTE — RLS (Row Level Security):
    A Data API do Neon NÃO gerencia permissões sozinha. Ela apenas
    repassa o JWT para o PostgreSQL, que aplica RLS e GRANTs. Para o
    dashboard funcionar, cada tabela precisa de:
        - RLS habilitado (ALTER TABLE ... ENABLE ROW LEVEL SECURITY);
        - políticas de leitura para o role `authenticated`;
        - GRANT SELECT ON <tabela> TO authenticated;
    Sem isso, a API responde 401/403 e o dashboard exibe um erro
    amigável, retornando um DataFrame vazio.
"""

from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

try:
    from auth import obter_config
except ImportError:  # importação como pacote (dashboard.data)
    from .auth import obter_config


_TIMEOUT_API = 30


class DataAPIError(Exception):
    """Falha ao consultar a Neon Data API."""


# ==================== INFRAESTRUTURA ====================
def _token_atual() -> str:
    """Retorna o JWT da sessão atual (ou string vazia)."""
    return str(st.session_state.get('jwt_token') or '')


def _data_api_url() -> str:
    """Retorna a URL base da Neon Data API, sem barra final."""
    url = obter_config('NEON_DATA_API_URL')
    if not url:
        raise DataAPIError(
            '⚠️ NEON_DATA_API_URL não configurada. '
            'Defina a variável no .env ou nos secrets do Streamlit.'
        )
    return url.rstrip('/')


def _requisitar(
    tabela: str,
    token: str,
    params: dict | None = None,
) -> pd.DataFrame:
    """
    Executa GET {NEON_DATA_API_URL}/{tabela}?select=* e devolve um DataFrame.

    Levanta DataAPIError em falhas de rede, autenticação/autorização ou
    resposta inválida. Não exibe nada na tela: quem chama decide a mensagem.
    """
    if not token:
        raise DataAPIError(
            '🔒 Sessão não autenticada. Faça login novamente.'
        )

    url = f'{_data_api_url()}/{tabela}'
    query = {'select': '*'}
    if params:
        query.update(params)

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    }

    try:
        resposta = requests.get(
            url,
            headers=headers,
            params=query,
            timeout=_TIMEOUT_API,
        )
    except requests.exceptions.Timeout:
        raise DataAPIError(
            f'⏱️ Tempo esgotado ao carregar {tabela}. Tente novamente.'
        ) from None
    except requests.exceptions.RequestException as exc:
        raise DataAPIError(
            f'🌐 Falha de rede ao carregar {tabela}: {exc}'
        ) from exc

    if resposta.status_code == 401:
        raise DataAPIError(
            '🔒 Sessão expirada ou token inválido. Faça login novamente.'
        )
    if resposta.status_code == 403:
        raise DataAPIError(
            f'🚫 Acesso negado à tabela `{tabela}`. Verifique no Neon se '
            'há RLS configurado e GRANT SELECT para o role `authenticated`.'
        )
    if resposta.status_code not in (200, 206):
        detalhe = (resposta.text or '')[:200]
        raise DataAPIError(
            f'❌ Erro ao carregar {tabela} (HTTP {resposta.status_code}). '
            f'{detalhe}'
        )

    try:
        dados = resposta.json()
    except ValueError:
        raise DataAPIError(
            f'❌ Resposta inválida da Data API ao carregar {tabela}.'
        ) from None

    if not dados:
        return pd.DataFrame()

    # PostgREST normalmente devolve uma lista; erros vêm como objeto.
    if isinstance(dados, dict):
        if 'message' in dados or 'error' in dados:
            raise DataAPIError(
                f'❌ Erro retornado pela Data API em {tabela}: '
                f'{dados.get("message") or dados.get("error")}'
            )
        dados = [dados]

    try:
        return pd.DataFrame(dados)
    except Exception as exc:
        raise DataAPIError(
            f'❌ Não foi possível converter {tabela} em DataFrame: {exc}'
        ) from exc


def _carregar_com_tratamento(funcao, nome: str, *args) -> pd.DataFrame:
    """
    Executa uma função de carga (já cacheada) e traduz falhas em st.error.

    O token é passado como primeiro argumento para que o cache do
    Streamlit seja isolado por usuário/JWT — importante com RLS.
    """
    try:
        return funcao(_token_atual(), *args)
    except DataAPIError as exc:
        st.error(str(exc))
        return pd.DataFrame()
    except Exception as exc:
        st.error(f'❌ Erro inesperado ao carregar {nome}: {exc}')
        return pd.DataFrame()


# ==================== CONVERSÕES ====================
def _converter_tickets(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica conversões de tipo e colunas derivadas usadas pelas views."""
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
    if 'dias_aberto' not in df.columns and 'criado_data' in df.columns:
        df['dias_aberto'] = (hoje - df['criado_data']).dt.days

    # dias_resolucao: dias entre criado_data e data_resolvido
    if ('dias_resolucao' not in df.columns
            and 'criado_data' in df.columns
            and 'data_resolvido' in df.columns):
        df['dias_resolucao'] = (
            df['data_resolvido'] - df['criado_data']
        ).dt.days

    # dias_1_resolucao: dias até a primeira resolução
    if ('dias_1_resolucao' not in df.columns
            and 'criado_data' in df.columns
            and 'data_1_resolvido' in df.columns):
        df['dias_1_resolucao'] = (
            df['data_1_resolvido'] - df['criado_data']
        ).dt.days

    # sla_status: cumprido / estourado
    if 'sla_status' not in df.columns:
        if 'previsao' in df.columns and 'data_resolvido' in df.columns:
            df['sla_status'] = None
            mask = df['data_resolvido'].notna() & df['previsao'].notna()
            df.loc[
                mask & (df['data_resolvido'] <= df['previsao']),
                'sla_status',
            ] = 'cumprido'
            df.loc[
                mask & (df['data_resolvido'] > df['previsao']),
                'sla_status',
            ] = 'estourado'

    # status_resolvido: True/False
    if 'status_resolvido' not in df.columns and 'status' in df.columns:
        df['status_resolvido'] = df['status'].isin(['Resolvido', 'Fechado'])

    return df


def _converter_movimentacoes(df: pd.DataFrame) -> pd.DataFrame:
    if not df.empty:
        if 'data_movimentacao' in df.columns:
            df['data_movimentacao'] = pd.to_datetime(
                df['data_movimentacao'], errors='coerce'
            )
        if 'ticket_id' in df.columns:
            df['ticket_id'] = pd.to_numeric(
                df['ticket_id'], errors='coerce'
            )
    return df


def _converter_mensagens(df: pd.DataFrame) -> pd.DataFrame:
    if not df.empty:
        if 'data_hora' in df.columns:
            df['data_hora'] = pd.to_datetime(
                df['data_hora'], errors='coerce'
            )
        if 'ticket_id' in df.columns:
            df['ticket_id'] = pd.to_numeric(
                df['ticket_id'], errors='coerce'
            )
    return df


# ==================== TICKETS ====================
@st.cache_data(ttl=3600, show_spinner=False)
def _carregar_tickets_cache(token: str) -> pd.DataFrame:
    return _converter_tickets(_requisitar('tickets', token))


def carregar_tickets() -> pd.DataFrame:
    """Carrega a tabela `tickets` via Neon Data API."""
    return _carregar_com_tratamento(_carregar_tickets_cache, 'tickets')


@st.cache_data(ttl=300, show_spinner=False)
def _carregar_ticket_por_id_cache(token: str, ticket_id: int) -> pd.DataFrame:
    return _converter_tickets(
        _requisitar('tickets', token, {'id': f'eq.{ticket_id}'})
    )


def carregar_ticket_por_id(ticket_id) -> pd.DataFrame:
    """Carrega um único ticket pelo ID (usado pela árvore de movimentações)."""
    try:
        ticket_id = int(ticket_id)
    except (TypeError, ValueError):
        st.error('❌ ID de ticket inválido.')
        return pd.DataFrame()

    return _carregar_com_tratamento(
        _carregar_ticket_por_id_cache,
        f'ticket #{ticket_id}',
        ticket_id,
    )


# ==================== MOVIMENTAÇÕES ====================
@st.cache_data(ttl=300, show_spinner=False)
def _carregar_movimentacoes_cache(token: str) -> pd.DataFrame:
    return _converter_movimentacoes(_requisitar('movimentacoes', token))


def carregar_movimentacoes() -> pd.DataFrame:
    """Carrega a tabela `movimentacoes` via Neon Data API."""
    return _carregar_com_tratamento(
        _carregar_movimentacoes_cache, 'movimentações'
    )


@st.cache_data(ttl=300, show_spinner=False)
def _carregar_movimentacoes_por_ticket_cache(
    token: str,
    ticket_id: int,
) -> pd.DataFrame:
    return _converter_movimentacoes(
        _requisitar(
            'movimentacoes',
            token,
            {
                'ticket_id': f'eq.{ticket_id}',
                'order': 'data_movimentacao.asc',
            },
        )
    )


def carregar_movimentacoes_por_ticket(ticket_id) -> pd.DataFrame:
    """Carrega as movimentações de um ticket, em ordem cronológica."""
    try:
        ticket_id = int(ticket_id)
    except (TypeError, ValueError):
        st.error('❌ ID de ticket inválido.')
        return pd.DataFrame()

    return _carregar_com_tratamento(
        _carregar_movimentacoes_por_ticket_cache,
        f'movimentações do ticket #{ticket_id}',
        ticket_id,
    )


# ==================== MENSAGENS ====================
@st.cache_data(ttl=300, show_spinner=False)
def _carregar_mensagens_cache(token: str) -> pd.DataFrame:
    return _converter_mensagens(_requisitar('mensagens', token))


def carregar_mensagens() -> pd.DataFrame:
    """Carrega a tabela `mensagens` via Neon Data API."""
    return _carregar_com_tratamento(_carregar_mensagens_cache, 'mensagens')


# ==================== ANALISTAS ====================
@st.cache_data(ttl=300, show_spinner=False)
def _carregar_analistas_cache(token: str) -> pd.DataFrame:
    return _requisitar('analistas', token)


def carregar_analistas() -> pd.DataFrame:
    """
    Carrega a tabela `analistas` via Neon Data API.
    Usada pela view de Roteamento.
    """
    return _carregar_com_tratamento(_carregar_analistas_cache, 'analistas')
