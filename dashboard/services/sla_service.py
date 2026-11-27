# ============================================================
# dashboard/services/sla_service.py — Serviço de SLA
# ============================================================
"""
Regras de negócio para cálculo de SLA, conforme especificação de refatoração.

Regras:
- Cumprido: data_resolvido <= previsao
- Estourado: data_resolvido > previsao
- Em andamento: data_resolvido IS NULL
- Em risco: previsão próxima do vencimento e ticket ainda não resolvido
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd


def calcular_sla_status(
    data_resolvido: Optional[datetime],
    previsao: Optional[datetime],
) -> Optional[str]:
    """
    Retorna o status do SLA para um ticket.

    Regras:
      - 'cumprido': resolvido dentro do prazo (data_resolvido <= previsao)
      - 'estourado': resolvido após o prazo (data_resolvido > previsao)
      - 'em_andamento': ainda não resolvido (data_resolvido IS NULL)
      - None: sem previsão válida para cálculo
    """
    if previsao is None or pd.isna(previsao):
        return None

    if data_resolvido is None or pd.isna(data_resolvido):
        return 'em_andamento'

    if data_resolvido <= previsao:
        return 'cumprido'

    return 'estourado'


def aplicar_sla_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona a coluna 'sla_status' ao DataFrame de tickets com base nas
    colunas 'data_resolvido' e 'previsao'.

    Não modifica o DataFrame original; retorna uma cópia.
    """
    df = df.copy()

    if 'data_resolvido' not in df.columns or 'previsao' not in df.columns:
        df['sla_status'] = None
        return df

    df['data_resolvido'] = pd.to_datetime(df['data_resolvido'], errors='coerce')
    df['previsao'] = pd.to_datetime(df['previsao'], errors='coerce')

    df['sla_status'] = df.apply(
        lambda r: calcular_sla_status(r['data_resolvido'], r['previsao']),
        axis=1,
    )

    return df


def calcular_metricas_sla(df: pd.DataFrame) -> dict:
    """
    Calcula métricas agregadas de SLA a partir de um DataFrame já com
    coluna 'sla_status'.

    Retorna dicionário com totais e percentuais.
    """
    if df.empty or 'sla_status' not in df.columns:
        return {
            'total': 0,
            'cumpridos': 0,
            'estourados': 0,
            'em_andamento': 0,
            'sem_previsao': 0,
            'percentual_cumprido': 0.0,
            'percentual_estourado': 0.0,
        }

    df_sla = df[df['sla_status'].isin(['cumprido', 'estourado'])].copy()

    total = len(df_sla)
    cumpridos = int((df_sla['sla_status'] == 'cumprido').sum())
    estourados = int((df_sla['sla_status'] == 'estourado').sum())
    em_andamento = int((df['sla_status'] == 'em_andamento').sum())
    sem_previsao = int(df['sla_status'].isna().sum())

    perc_cumprido = (cumpridos / total * 100) if total > 0 else 0.0
    perc_estourado = (estourados / total * 100) if total > 0 else 0.0

    return {
        'total': total,
        'cumpridos': cumpridos,
        'estourados': estourados,
        'em_andamento': em_andamento,
        'sem_previsao': sem_previsao,
        'percentual_cumprido': round(perc_cumprido, 1),
        'percentual_estourado': round(perc_estourado, 1),
    }


def calcular_sla_por_categoria(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna DataFrame com SLA por categoria.
    Colunas: categoria, total, cumpridos, percentual.
    """
    if df.empty or 'sla_status' not in df.columns or 'categoria' not in df.columns:
        return pd.DataFrame(columns=['categoria', 'total', 'cumpridos', 'percentual'])

    df_sla = df[df['sla_status'].isin(['cumprido', 'estourado'])].copy()
    if df_sla.empty:
        return pd.DataFrame(columns=['categoria', 'total', 'cumpridos', 'percentual'])

    agg = (
        df_sla.groupby('categoria')
        .agg(total=('id', 'count'), cumpridos=('sla_status', lambda x: (x == 'cumprido').sum()))
        .reset_index()
    )
    agg['percentual'] = (agg['cumpridos'] / agg['total'] * 100).round(1)
    agg = agg.sort_values('percentual')
    return agg


def calcular_sla_por_prioridade(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna DataFrame com SLA por prioridade.
    Colunas: prioridade, total, cumpridos, percentual.
    """
    if df.empty or 'sla_status' not in df.columns or 'prioridade' not in df.columns:
        return pd.DataFrame(columns=['prioridade', 'total', 'cumpridos', 'percentual'])

    df_sla = df[df['sla_status'].isin(['cumprido', 'estourado'])].copy()
    if df_sla.empty:
        return pd.DataFrame(columns=['prioridade', 'total', 'cumpridos', 'percentual'])

    agg = (
        df_sla.groupby('prioridade')
        .agg(total=('id', 'count'), cumpridos=('sla_status', lambda x: (x == 'cumprido').sum()))
        .reset_index()
    )
    agg['percentual'] = (agg['cumpridos'] / agg['total'] * 100).round(1)

    ordem = ['Urgente', 'Alta', 'Média', 'Média-1', 'Média-2', 'Baixa', 'Baixa-1', 'Baixa-2', 'Baixa-3']
    agg['ordem'] = agg['prioridade'].map({p: i for i, p in enumerate(ordem)}).fillna(99)
    agg = agg.sort_values('ordem').drop(columns=['ordem'])
    return agg


def calcular_margem_media(df: pd.DataFrame) -> float:
    """
    Calcula a margem média (previsao - data_resolvido) em dias.
    Positivo = terminou antes do prazo; Negativo = estourado.
    """
    if df.empty or 'data_resolvido' not in df.columns or 'previsao' not in df.columns:
        return 0.0

    df_sla = df[
        df['data_resolvido'].notna() & df['previsao'].notna()
    ].copy()
    if df_sla.empty:
        return 0.0

    df_sla['data_resolvido'] = pd.to_datetime(df_sla['data_resolvido'], errors='coerce')
    df_sla['previsao'] = pd.to_datetime(df_sla['previsao'], errors='coerce')

    margem = (df_sla['previsao'] - df_sla['data_resolvido']).dt.days
    return float(margem.mean()) if not margem.empty else 0.0


def tickets_em_risco(df: pd.DataFrame, dias_limite: int = 2) -> pd.DataFrame:
    """
    Retorna tickets abertos (não resolvidos) cuja previsão está próxima
    do vencimento (dentro de dias_limite dias) ou já vencida.
    """
    if df.empty or 'previsao' not in df.columns or 'data_resolvido' not in df.columns or 'status' not in df.columns:
        return pd.DataFrame()

    agora = pd.Timestamp.now()
    limite = agora + pd.Timedelta(days=dias_limite)

    em_andamento = df[
        df['data_resolvido'].isna() &
        df['previsao'].notna() &
        (df['previsao'] <= limite)
    ].copy()

    return em_andamento.sort_values('previsao')
