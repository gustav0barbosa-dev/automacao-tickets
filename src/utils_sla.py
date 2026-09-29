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
    """Adiciona N horas úteis a uma data."""
    if pd.isna(data_inicio):
        return None

    if isinstance(data_inicio, str):
        data_inicio = pd.to_datetime(data_inicio, dayfirst=True, errors='coerce')
    elif not isinstance(data_inicio, pd.Timestamp):
        data_inicio = pd.Timestamp(data_inicio)

    # PROTEÇÃO 1: ano fora do range
    if data_inicio.year < 2000 or data_inicio.year > 2100:
        return None

    atual = data_inicio
    horas_restantes = float(horas)
    iteracoes = 0
    MAX_ITERACOES = 10000

    while horas_restantes > 0:
        iteracoes += 1
        if iteracoes > MAX_ITERACOES:
            return atual  # retorna o que tem

        if atual.hour >= HORA_FIM_EXPEDIENTE or atual.hour < HORA_INICIO_EXPEDIENTE or not eh_dia_util(atual):
            atual = _proximo_inicio_expediente(atual)
            continue

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

    Versão SIMPLES e ROBUSTA:
      - Itera dia a dia (não hora a hora)
      - Sem loops aninhados
      - Sem risco de loop infinito
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

    # Proteções
    if fim <= inicio:
        return 0
    if inicio.year < 2000 or inicio.year > 2100:
        return 0
    if fim.year < 2000 or fim.year > 2100:
        return 0
    if (fim - inicio).days > 3650:
        return 0

    total_horas = 0.0
    dia_atual = inicio.normalize()  # Zera horas
    dia_fim = fim.normalize()

    # Itera dia a dia
    while dia_atual <= dia_fim:
        # Pula fins de semana e feriados
        if not eh_dia_util(dia_atual):
            dia_atual += pd.Timedelta(days=1)
            continue

        # Define o início do expediente neste dia
        h_inicio = dia_atual.replace(
            hour=HORA_INICIO_EXPEDIENTE, minute=0, second=0, microsecond=0
        )
        h_fim = dia_atual.replace(
            hour=HORA_FIM_EXPEDIENTE, minute=0, second=0, microsecond=0
        )

        # Ajusta no primeiro dia: não conta antes de `inicio`
        if dia_atual == inicio.normalize() and inicio > h_inicio:
            h_inicio = inicio

        # Ajusta no último dia: não conta depois de `fim`
        if dia_atual == fim.normalize() and fim < h_fim:
            h_fim = fim

        # Se o intervalo é válido (dentro do expediente)
        if h_inicio < h_fim:
            horas_dia = (h_fim - h_inicio).total_seconds() / 3600
            total_horas += horas_dia

        dia_atual += pd.Timedelta(days=1)

    return round(total_horas, 2)


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