# ============================================================
# dashboard/services/reopening_service.py — Detecção de Reabertura
# ============================================================
"""
Detecção de reabertura de tickets usando histórico de movimentações.

Regras de negócio:
- Uma reabertura ocorre quando há transição de um estado terminal
  (Resolvido, Fechado, Cancelado) para um estado ativo
  (Em atendimento, Aguardando confirmação do usuário, etc.).
- Não conta a criação inicial do ticket como reabertura.
- Um ticket pode ser reaberto mais de uma vez.
- Métricas distintas:
    * Tickets reabertos: quantidade de IDs que tiveram ao menos uma reabertura
    * Eventos de reabertura: quantidade total de transições de retorno
    * Taxa de reabertura: tickets reabertos / tickets encerrados elegíveis
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

# Estados considerados "terminais" (fechamento)
STATUSS_FECHADOS = {'Resolvido', 'Fechado', 'Cancelado', 'Duplicado'}

# Estados considerados "ativos" (reabertura)
STATUSS_ATIVOS = {
    'Em atendimento',
    'Aguardando confirmação do usuário',
    'Aberto',
    'Reaberto',
}


def detectar_reaberturas(df_movs: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta tickets reabertos a partir do histórico de movimentações.

    Parâmetros
    ----------
    df_movs : pd.DataFrame
        DataFrame com colunas: ticket_id, data_movimentacao, de_status, para_status.

    Retorna
    -------
    pd.DataFrame
        Colunas: ticket_id, reaberto_vezes, data_primeira_reabertura,
        data_ultima_reabertura.
    """
    if df_movs.empty:
        return pd.DataFrame(
            columns=[
                'ticket_id', 'reaberto_vezes',
                'data_primeira_reabertura', 'data_ultima_reabertura',
            ]
        )

    df = df_movs.copy()
    df['data_movimentacao'] = pd.to_datetime(df['data_movimentacao'], errors='coerce')
    df['de_status'] = df['de_status'].astype(str).str.strip()
    df['para_status'] = df['para_status'].astype(str).str.strip()
    df['ticket_id'] = df['ticket_id'].astype(str)

    # Filtro de reabertura: de_status terminal -> para_status ativo
    df_reab = df[
        df['de_status'].isin(STATUSS_FECHADOS)
        & df['para_status'].isin(STATUSS_ATIVOS)
    ].copy()

    if df_reab.empty:
        return pd.DataFrame(
            columns=[
                'ticket_id', 'reaberto_vezes',
                'data_primeira_reabertura', 'data_ultima_reabertura',
            ]
        )

    resultado = df_reab.groupby('ticket_id').agg(
        reaberto_vezes=('id', 'count'),
        data_primeira_reabertura=('data_movimentacao', 'min'),
        data_ultima_reabertura=('data_movimentacao', 'max'),
    ).reset_index()

    return resultado


def calcular_metricas_reabertura(
    df_tickets: pd.DataFrame,
    df_reaberturas: pd.DataFrame,
) -> dict:
    """
    Calcula métricas agregadas de reabertura.

    Parâmetros
    ----------
    df_tickets : pd.DataFrame
        DataFrame de tickets (deve conter coluna 'id' e 'status').
    df_reaberturas : pd.DataFrame
        Resultado de detectar_reaberturas().

    Retorna
    -------
    dict
        total_tickets, tickets_reabertos, total_reaberturas,
        taxa_reabertura, media_reaberturas_por_ticket.
    """
    if df_tickets.empty:
        return {
            'total_tickets': 0,
            'tickets_reabertos': 0,
            'total_reaberturas': 0,
            'taxa_reabertura': 0.0,
            'media_reaberturas_por_ticket': 0.0,
        }

    total_tickets = len(df_tickets)

    if df_reaberturas.empty:
        return {
            'total_tickets': total_tickets,
            'tickets_reabertos': 0,
            'total_reaberturas': 0,
            'taxa_reabertura': 0.0,
            'media_reaberturas_por_ticket': 0.0,
        }

    # Normaliza ticket_id para string para comparação
    df_reab = df_reaberturas.copy()
    df_reab['ticket_id'] = df_reab['ticket_id'].astype(str)
    df_tickets = df_tickets.copy()
    df_tickets['ticket_id_str'] = df_tickets['id'].astype(str)

    ids_filtrados = set(df_tickets['ticket_id_str'].unique())
    df_reab_filtrado = df_reab[df_reab['ticket_id'].isin(ids_filtrados)].copy()

    tickets_reabertos = len(df_reab_filtrado)
    total_reaberturas = int(df_reab_filtrado['reaberto_vezes'].sum())
    taxa_reabertura = (tickets_reabertos / total_tickets * 100) if total_tickets else 0.0
    media_reaberturas = (
        df_reab_filtrado['reaberto_vezes'].mean() if not df_reab_filtrado.empty else 0.0
    )

    return {
        'total_tickets': total_tickets,
        'tickets_reabertos': tickets_reabertos,
        'total_reaberturas': total_reaberturas,
        'taxa_reabertura': round(taxa_reabertura, 1),
        'media_reaberturas_por_ticket': round(float(media_reaberturas), 2),
    }


def enriquecer_tickets_com_reaberturas(
    df_tickets: pd.DataFrame,
    df_reaberturas: pd.DataFrame,
) -> pd.DataFrame:
    """
    Junta informações de reabertura ao DataFrame de tickets.

    Adiciona colunas: reaberto_vezes, data_primeira_reabertura,
    data_ultima_reabertura.
    """
    if df_reaberturas.empty:
        df = df_tickets.copy()
        df['reaberto_vezes'] = 0
        df['data_primeira_reabertura'] = pd.NaT
        df['data_ultima_reabertura'] = pd.NaT
        return df

    df_reab = df_reaberturas.copy()
    df_reab['ticket_id'] = df_reab['ticket_id'].astype(str)

    df = df_tickets.copy()
    df['ticket_id_str'] = df['id'].astype(str)

    df = df.merge(
        df_reab[['ticket_id', 'reaberto_vezes', 'data_primeira_reabertura', 'data_ultima_reabertura']],
        left_on='ticket_id_str',
        right_on='ticket_id',
        how='left',
    )

    df['reaberto_vezes'] = df['reaberto_vezes'].fillna(0).astype(int)
    df = df.drop(columns=['ticket_id_str', 'ticket_id_y'], errors='ignore')
    df = df.rename(columns={'ticket_id_x': 'ticket_id'})

    return df
