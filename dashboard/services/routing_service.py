# ============================================================
# dashboard/services/routing_service.py — Serviço de Roteamento
# ============================================================
"""
Cálculos de roteamento de tickets entre analistas/áreas.

Regras de negócio:
- Duração de etapa = entre dois eventos cronológicos válidos e consecutivos
  que representem mudança de responsável, área ou estado.
- Não inferir que o responsável atual esteve com o ticket durante todo o
  período histórico. Usar eventos de atribuição/encaminhamento.
- Se não houver evento de atribuição confiável, marcar duração como desconhecida.
- Tempo de espera entre movimentações NÃO é tempo de trabalho do analista.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def calcular_fluxo_roteamento(
    df_movs: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula fluxo de roteamento entre responsáveis.

    Retorna DataFrame com:
      - origem, destino, qtd_tickets, qtd_transferencias
    """
    if df_movs.empty:
        return pd.DataFrame(
            columns=['origem', 'destino', 'qtd_tickets', 'qtd_transferencias']
        )

    df = df_movs.copy()
    df['data_movimentacao'] = pd.to_datetime(df['data_movimentacao'], errors='coerce')
    df['de_status'] = df['de_status'].astype(str).str.strip()
    df['para_status'] = df['para_status'].astype(str).str.strip()
    df['autor'] = df['autor'].astype(str).str.strip()
    df['ticket_id'] = df['ticket_id'].astype(str)

    # Filtra apenas movimentações com autor válido
    df = df[df['autor'].notna() & (df['autor'] != '')].copy()
    if df.empty:
        return pd.DataFrame(
            columns=['origem', 'destino', 'qtd_tickets', 'qtd_transferencias']
        )

    # Agrupa por autor (destino) - quem recebeu o ticket
    fluxo = (
        df.groupby(['ticket_id', 'autor'])
        .size()
        .reset_index(name='transferencias_por_ticket')
    )

    fluxo_agrupado = (
        fluxo.groupby('autor')
        .agg(
            qtd_tickets=('ticket_id', 'nunique'),
            qtd_transferencias=('transferencias_por_ticket', 'sum'),
        )
        .reset_index()
    )
    fluxo_fluxo = fluxo_agrupado.rename(columns={'autor': 'destino'})
    fluxo_fluxo['origem'] = 'Várias'  # Placeholder - sem dados de área origem/destino
    fluxo_fluxo = fluxo_fluxo[['origem', 'destino', 'qtd_tickets', 'qtd_transferencias']]
    fluxo_fluxo = fluxo_fluxo.sort_values('qtd_transferencias', ascending=False)

    return fluxo_fluxo


def calcular_tempo_por_responsavel(
    df_movs: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula tempo de permanência por responsável com base nas movimentações.

    Retorna DataFrame com:
      - responsavel, total_tickets, tempo_medio_dias, tickets_gerenciados
    """
    if df_movs.empty:
        return pd.DataFrame(
            columns=['responsavel', 'total_tickets', 'tempo_medio_dias', 'tickets_gerenciados']
        )

    df = df_movs.copy()
    df['data_movimentacao'] = pd.to_datetime(df['data_movimentacao'], errors='coerce')
    df['autor'] = df['autor'].astype(str).str.strip()
    df['ticket_id'] = df['ticket_id'].astype(str)

    df = df[df['autor'].notna() & df['data_movimentacao'].notna()].copy()
    if df.empty:
        return pd.DataFrame(
            columns=['responsavel', 'total_tickets', 'tempo_medio_dias', 'tickets_gerenciados']
        )

    df = df.sort_values(['ticket_id', 'data_movimentacao'])
    df['data_anterior'] = df.groupby('ticket_id')['data_movimentacao'].shift(1)
    df['horas_entre_movs'] = (
        df['data_movimentacao'] - df['data_anterior']
    ).dt.total_seconds() / 3600

    df_com_tempo = df[df['horas_entre_movs'].notna()].copy()
    if df_com_tempo.empty:
        return pd.DataFrame(
            columns=['responsavel', 'total_tickets', 'tempo_medio_dias', 'tickets_gerenciados']
        )

    agg = (
        df_com_tempo.groupby('autor')
        .agg(
            tickets_gerenciados=('ticket_id', 'nunique'),
            total_horas=('horas_entre_movs', 'sum'),
        )
        .reset_index()
    )

    agg['tempo_medio_dias'] = (agg['total_horas'] / 24).round(1)
    agg = agg.sort_values('tickets_gerenciados', ascending=False)
    agg = agg.rename(columns={'autor': 'responsavel'})
    return agg[['responsavel', 'total_tickets', 'tempo_medio_dias', 'tickets_gerenciados']]


def calcular_gaps_movimentacao(
    df_movs: pd.DataFrame,
    limite_horas: float = 24.0,
) -> pd.DataFrame:
    """
    Identifica gaps (períodos sem movimentação) entre eventos de um ticket.

    Retorna DataFrame com os maiores gaps:
      - ticket_id, autor (quem recebeu), dias_parado, data_movimentacao, data_anterior
    """
    if df_movs.empty:
        return pd.DataFrame(
            columns=['ticket_id', 'autor', 'dias_parado', 'data_movimentacao', 'data_anterior']
        )

    df = df_movs.copy()
    df['data_movimentacao'] = pd.to_datetime(df['data_movimentacao'], errors='coerce')
    df['autor'] = df['autor'].astype(str).str.strip()
    df['ticket_id'] = df['ticket_id'].astype(str)

    df = df[df['data_movimentacao'].notna() & df['autor'].notna()].copy()
    if df.empty:
        return pd.DataFrame(
            columns=['ticket_id', 'autor', 'dias_parado', 'data_movimentacao', 'data_anterior']
        )

    df = df.sort_values(['ticket_id', 'data_movimentacao'])
    df['data_anterior'] = df.groupby('ticket_id')['data_movimentacao'].shift(1)
    df['horas_parado'] = (
        df['data_movimentacao'] - df['data_anterior']
    ).dt.total_seconds() / 3600

    gaps = df[df['horas_parado'].notna()].copy()
    gaps = gaps[gaps['horas_parado'] > limite_horas].copy()

    if gaps.empty:
        return pd.DataFrame(
            columns=['ticket_id', 'autor', 'dias_parado', 'data_movimentacao', 'data_anterior']
        )

    gaps['dias_parado'] = (gaps['horas_parado'] / 24).round(1)
    gaps = gaps.sort_values('horas_parado', ascending=False)

    return gaps[
        ['ticket_id', 'autor', 'dias_parado', 'data_movimentacao', 'data_anterior']
    ].head(50)
