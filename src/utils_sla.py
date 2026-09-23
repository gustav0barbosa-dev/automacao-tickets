# ============================================================
# utils_sla.py — Cálculo de SLA em horas úteis
# ============================================================
"""
Novo SLA (baseado na tabela consolidada):

| Critério | Peso | Prazo (horas úteis) |
|----------|------|---------------------|
| Urgente  | 4    | 3                   |
| Alta     | 3    | 24                  |
| Média    | 2    | 48                  |
| Média 2  | 2    | 72                  |
| Baixa    | 1    | 120                 |
| Baixa 2  | 1    | 168                 |

Regras:
  - Expediente: 08h00 às 17h00 (seg-sex)
  - Sábados, domingos e feriados não contam
  - SLA termina em data_resolvido (não em "Fechado")
"""

from datetime import datetime, time, timedelta
from typing import Optional

import holidays
import pandas as pd


# ==================== CONFIGURAÇÃO ====================
HORA_INICIO_EXPEDIENTE = 8    # 08h00
HORA_FIM_EXPEDIENTE = 17      # 17h00
HORAS_POR_DIA_UTIL = HORA_FIM_EXPEDIENTE - HORA_INICIO_EXPEDIENTE  # 9h


# ==================== MAPEAMENTO DE CRITICIDADE ====================
# Criticidade → (peso, prazo em horas úteis)
PRAZO_POR_CRITICIDADE = {
    'Urgente':     (4, 3),
    'Alta':        (3, 24),
    'Média':       (2, 48),    # rotinas mensais
    'Média 1':     (2, 48),
    'Média 2':     (2, 72),    # manutenções / alterações
    'Média-1':     (2, 48),
    'Média-2':     (2, 72),
    'Baixa':       (1, 120),   # demandas de informação
    'Baixa 1':     (1, 120),
    'Baixa 2':     (1, 168),   # nova legislação / força maior
    'Baixa-1':     (1, 120),
    'Baixa-2':     (1, 168),
    'Baixa-3':     (1, 168),
}


# ==================== CACHE DE FERIADOS ====================
_feriados_cache = None


def _get_feriados():
    """Retorna feriados brasileiros + SP (cache)."""
    global _feriados_cache
    if _feriados_cache is None:
        _feriados_cache = holidays.Brazil(subdiv='SP')
    return _feriados_cache


def eh_dia_util(data) -> bool:
    """Verifica se uma data é dia útil (seg-sex e não feriado)."""
    if pd.isna(data):
        return False

    if isinstance(data, pd.Timestamp):
        data = data.date()
    elif isinstance(data, datetime):
        data = data.date()

    # Fim de semana
    if data.weekday() >= 5:
        return False

    # Feriado
    if data in _get_feriados():
        return False

    return True


# ==================== FUNÇÕES DE PRAZO ====================
def prazo_por_criticidade(criticidade: str) -> Optional[int]:
    """Retorna o prazo em HORAS ÚTEIS para uma criticidade."""
    if pd.isna(criticidade):
        return None
    dado = PRAZO_POR_CRITICIDADE.get(str(criticidade).strip())
    return dado[1] if dado else None


def peso_por_criticidade(criticidade: str) -> Optional[int]:
    """Retorna o peso da criticidade (1 a 4)."""
    if pd.isna(criticidade):
        return None
    dado = PRAZO_POR_CRITICIDADE.get(str(criticidade).strip())
    return dado[0] if dado else None


# ==================== ADIÇÃO DE HORAS ÚTEIS ====================
def adicionar_horas_uteis(data_inicio, horas: float) -> pd.Timestamp:
    """
    Adiciona N horas úteis a uma data, respeitando o expediente (8h-17h).

    Exemplos:
        - Começa às 16h de segunda com 3h úteis → termina às 10h de terça
        - Começa às 10h de sexta com 24h úteis → termina às 16h de terça (pula fim de semana)
    """
    if pd.isna(data_inicio):
        return None

    if isinstance(data_inicio, str):
        data_inicio = pd.to_datetime(data_inicio, dayfirst=True, errors='coerce')
    elif not isinstance(data_inicio, pd.Timestamp):
        data_inicio = pd.Timestamp(data_inicio)

    atual = data_inicio
    horas_restantes = float(horas)

    while horas_restantes > 0:
        # 1. Se está fora do expediente, pula para o próximo início
        if atual.hour >= HORA_FIM_EXPEDIENTE or atual.hour < HORA_INICIO_EXPEDIENTE or not eh_dia_util(atual):
            atual = _proximo_inicio_expediente(atual)
            continue

        # 2. Calcula quanto tempo cabe no dia atual
        fim_do_dia = atual.replace(
            hour=HORA_FIM_EXPEDIENTE, minute=0, second=0, microsecond=0
        )
        horas_disponiveis = (fim_do_dia - atual).total_seconds() / 3600

        if horas_disponiveis >= horas_restantes:
            atual = atual + pd.Timedelta(hours=horas_restantes)
            horas_restantes = 0
        else:
            horas_restantes -= horas_disponiveis
            atual = _proximo_inicio_expediente(fim_do_dia)

    return atual


def _proximo_inicio_expediente(data) -> pd.Timestamp:
    """Retorna o próximo início de expediente (08h) em dia útil."""
    data = pd.Timestamp(data)

    # Se já passou do expediente ou está fora, avança um dia
    if data.hour >= HORA_FIM_EXPEDIENTE:
        data = (data + pd.Timedelta(days=1)).replace(
            hour=HORA_INICIO_EXPEDIENTE, minute=0, second=0, microsecond=0
        )
    elif data.hour < HORA_INICIO_EXPEDIENTE:
        data = data.replace(
            hour=HORA_INICIO_EXPEDIENTE, minute=0, second=0, microsecond=0
        )
    else:
        # Está no meio do expediente, mas não é dia útil
        data = data.replace(
            hour=HORA_INICIO_EXPEDIENTE, minute=0, second=0, microsecond=0
        )

    # Pula fins de semana e feriados
    while not eh_dia_util(data):
        data = (data + pd.Timedelta(days=1)).replace(
            hour=HORA_INICIO_EXPEDIENTE, minute=0, second=0, microsecond=0
        )

    return data


# ==================== CÁLCULO DE HORAS ÚTEIS ENTRE DATAS ====================
def contar_horas_uteis(data_inicio, data_fim) -> float:
    """
    Conta quantas HORAS ÚTEIS existem entre duas datas.
    Respeita expediente (8h-17h), fins de semana e feriados.
    """
    if pd.isna(data_inicio) or pd.isna(data_fim):
        return 0

    if isinstance(data_inicio, str):
        data_inicio = pd.to_datetime(data_inicio, dayfirst=True, errors='coerce')
    if isinstance(data_fim, str):
        data_fim = pd.to_datetime(data_fim, dayfirst=True, errors='coerce')

    if pd.isna(data_inicio) or pd.isna(data_fim):
        return 0

    inicio = pd.Timestamp(data_inicio)
    fim = pd.Timestamp(data_fim)

    if fim <= inicio:
        return 0

    # Normaliza para o início do expediente se estiver antes
    if inicio.hour < HORA_INICIO_EXPEDIENTE or not eh_dia_util(inicio):
        inicio = _proximo_inicio_expediente(inicio)
    elif inicio.hour >= HORA_FIM_EXPEDIENTE:
        inicio = _proximo_inicio_expediente(inicio)

    # Se fim caiu fora do expediente, ajusta para o fim do último dia útil
    if not eh_dia_util(fim) or fim.hour < HORA_INICIO_EXPEDIENTE:
        # Retrocede até o último dia útil às 17h
        fim = pd.Timestamp(fim)
        while not eh_dia_util(fim):
            fim = (fim - pd.Timedelta(days=1))
        fim = fim.replace(hour=HORA_FIM_EXPEDIENTE, minute=0, second=0, microsecond=0)
    elif fim.hour > HORA_FIM_EXPEDIENTE:
        fim = fim.replace(hour=HORA_FIM_EXPEDIENTE, minute=0, second=0, microsecond=0)

    if fim <= inicio:
        return 0

    # Conta horas
    total_horas = 0.0
    atual = inicio

    while atual < fim:
        # Se é dia útil e está dentro do expediente
        if eh_dia_util(atual) and HORA_INICIO_EXPEDIENTE <= atual.hour < HORA_FIM_EXPEDIENTE:
            fim_do_dia = atual.replace(
                hour=HORA_FIM_EXPEDIENTE, minute=0, second=0, microsecond=0
            )
            if fim_do_dia > fim:
                fim_do_dia = fim

            total_horas += (fim_do_dia - atual).total_seconds() / 3600
            atual = fim_do_dia

        # Avança para o próximo início de expediente
        atual = _proximo_inicio_expediente(atual + pd.Timedelta(seconds=1))
        if atual > fim:
            break

    return total_horas


# ==================== PREVISÃO ESPERADA ====================
def previsao_esperada(criado_data, criticidade: str) -> Optional[pd.Timestamp]:
    """
    Calcula a data/hora-limite para resolver o ticket,
    baseada na criticidade e em horas úteis.
    """
    prazo_horas = prazo_por_criticidade(criticidade)
    if prazo_horas is None or pd.isna(criado_data):
        return None

    return adicionar_horas_uteis(criado_data, prazo_horas)