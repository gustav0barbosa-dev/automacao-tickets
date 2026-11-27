# ============================================================
# dashboard/services/productivity_service.py — Serviço de Produtividade
# ============================================================
"""
Cálculos de produtividade por responsável e área.

Regras de negócio:
- Duração de etapa = entre dois eventos cronológicos válidos e consecutivos
  que representem mudança de responsável, área ou estado.
- Não inferir que o responsável atual esteve com o ticket durante todo o
  período histórico. Usar eventos de atribuição/encaminhamento.
- Se não houver evento de atribuição confiável, marcar duração como desconhecida
  (não preencher com zero).
- Tempo de espera entre movimentações NÃO é tempo de trabalho do analista.
- Distinguir: tempo total do ticket, tempo sob responsabilidade de uma pessoa,
  tempo sob responsabilidade de uma área, tempo em estado de espera,
  intervalo sem movimentação registrada.
- Volume de tickets não equivale isoladamente a produtividade.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def calcular_produtividade_por_responsavel(
    df_tickets: pd.DataFrame,
    df_movs: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula métricas de produtividade por responsável.

    Colunas de saída:
      - responsavel_atual
      - total_tickets
      - resolvidos
      - em_aberto
      - dias_medio_resolucao
      - percentual_resolucao
    """
    if df_tickets.empty:
        return pd.DataFrame(
            columns=[
                'responsavel_atual', 'total_tickets', 'resolvidos',
                'em_aberto', 'dias_medio_resolucao', 'percentual_resolucao',
            ]
        )

    df = df_tickets.copy()
    df['criado_data'] = pd.to_datetime(df['criado_data'], errors='coerce')
    df['data_resolvido'] = pd.to_datetime(df['data_resolvido'], errors='coerce')

    # Tempo de resolução em dias
    df['dias_resolucao_calc'] = (
        df['data_resolvido'] - df['criado_data']
    ).dt.total_seconds() / 86400

    responsaveis_validos = df[
        df['responsavel_atual'].notna()
        & (df['responsavel_atual'] != '')
        & (df['responsavel_atual'] != 'Não informado')
    ].copy()

    if responsaveis_validos.empty:
        return pd.DataFrame(
            columns=[
                'responsavel_atual', 'total_tickets', 'resolvidos',
                'em_aberto', 'dias_medio_resolucao', 'percentual_resolucao',
            ]
        )

    status_resolvidos = {'Resolvido', 'Fechado'}

    agg = (
        responsaveis_validos.groupby('responsavel_atual')
        .agg(
            total_tickets=('id', 'count'),
            resolvidos=('status', lambda x: (x.isin(status_resolvidos)).sum()),
            em_aberto=('status', lambda x: (~x.isin(status_resolvidos | {'Cancelado', 'Duplicado'})).sum()),
            dias_medio_resolucao=('dias_resolucao_calc', 'mean'),
        )
        .reset_index()
    )

    agg['percentual_resolucao'] = (
        agg['resolvidos'] / agg['total_tickets'] * 100
    ).round(1)
    agg['dias_medio_resolucao'] = agg['dias_medio_resolucao'].round(1)

    agg = agg.sort_values('total_tickets', ascending=False)
    return agg


def calcular_tempo_por_responsavel(
    df_movs: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula tempo de permanência por responsável com base nas movimentações.

    Usa eventos de atribuição/encaminhamento para calcular quanto tempo
    cada responsável ficou com cada ticket.

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

    # Remove linhas sem autor ou data
    df = df[df['autor'].notna() & df['data_movimentacao'].notna()].copy()
    if df.empty:
        return pd.DataFrame(
            columns=['responsavel', 'total_tickets', 'tempo_medio_dias', 'tickets_gerenciados']
        )

    # Ordena por ticket e data
    df = df.sort_values(['ticket_id', 'data_movimentacao'])

    # Calcula diferença de tempo entre movimentações consecutivas do mesmo ticket
    df['data_anterior'] = df.groupby('ticket_id')['data_movimentacao'].shift(1)
    df['horas_entre_movs'] = (
        df['data_movimentacao'] - df['data_anterior']
    ).dt.total_seconds() / 3600

    # Remove primeira movimentação de cada ticket (não tem tempo anterior)
    df_com_tempo = df[df['horas_entre_movs'].notna()].copy()

    if df_com_tempo.empty:
        return pd.DataFrame(
            columns=['responsavel', 'total_tickets', 'tempo_medio_dias', 'tickets_gerenciados']
        )

    # Agrupa por autor (quem ficou responsável durante o intervalo)
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


def calcular_tempo_por_area(
    df_movs: pd.DataFrame,
) -> pd.DataFrame:
    """
    Placeholder para cálculo de tempo por área.
    Requer que movimentações tenham coluna de área origem/destino.
    """
    if df_movs.empty or 'area_origem' not in df_movs.columns:
        return pd.DataFrame(
            columns=['area', 'total_tickets', 'tempo_medio_dias']
        )

    df = df_movs.copy()
    df['data_movimentacao'] = pd.to_datetime(df['data_movimentacao'], errors='coerce')
    df['area_origem'] = df['area_origem'].astype(str).str.strip()

    df = df[df['area_origem'].notna() & df['data_movimentacao'].notna()].copy()
    if df.empty:
        return pd.DataFrame(columns=['area', 'total_tickets', 'tempo_medio_dias'])

    df = df.sort_values(['ticket_id', 'data_movimentacao'])
    df['data_anterior'] = df.groupby('ticket_id')['data_movimentacao'].shift(1)
    df['horas_entre_movs'] = (
        df['data_movimentacao'] - df['data_anterior']
    ).dt.total_seconds() / 3600

    df_com_tempo = df[df['horas_entre_movs'].notna()].copy()
    if df_com_tempo.empty:
        return pd.DataFrame(columns=['area', 'total_tickets', 'tempo_medio_dias'])

    agg = (
        df_com_tempo.groupby('area_origem')
        .agg(
            total_tickets=('ticket_id', 'nunique'),
            total_horas=('horas_entre_movs', 'sum'),
        )
        .reset_index()
    )
    agg['tempo_medio_dias'] = (agg['total_horas'] / 24).round(1)
    agg = agg.sort_values('total_tickets', ascending=False)
    agg = agg.rename(columns={'area_origem': 'area'})
    return agg[['area', 'total_tickets', 'tempo_medio_dias']]
