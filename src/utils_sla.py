# ============================================================
# utils_sla.py — Cálculo de SLA em dias úteis
# ============================================================
"""
Funções para cálculo de SLA considerando:
  - Dias úteis (seg-sex)
  - Feriados nacionais brasileiros + estaduais SP
  - Regra de criticidade:
      Urgente      → 3 dias úteis
      Alta         → 5 dias úteis
      Média 1, 2   → 10 dias úteis
      Baixa 1, 2   → 15 dias úteis
"""

from datetime import datetime, timedelta
from typing import Optional

import holidays
import pandas as pd


# ==================== CONSTANTES ====================
# Mapeamento: criticidade → prazo em dias úteis
PRAZO_POR_CRITICIDADE = {
    'Urgente': 3,
    'Alta': 5,
    'Média': 10,
    'Média 1': 10,
    'Média 2': 10,
    'Média-1': 10,
    'Média-2': 10,
    'Baixa': 15,
    'Baixa 1': 15,
    'Baixa 2': 15,
    'Baixa-1': 15,
    'Baixa-2': 15,
    'Baixa-3': 15,
}

# Cache de feriados
_feriados_cache = None


def _get_feriados(ano_min: int = 2020, ano_max: int = 2030) -> holidays.HolidayBase:
    """
    Retorna objeto com feriados brasileiros + estaduais SP.
    Cacheado para não recarregar toda vez.
    """
    global _feriados_cache

    if _feriados_cache is None:
        _feriados_cache = holidays.Brazil(years=range(ano_min, ano_max + 1),
                                            subdiv='SP')
    return _feriados_cache


def eh_dia_util(data) -> bool:
    """
    Verifica se uma data é dia útil.
    Considera: fins de semana + feriados.
    """
    if pd.isna(data):
        return False

    # Converte para date se for Timestamp
    if isinstance(data, pd.Timestamp):
        data = data.date()
    elif isinstance(data, datetime):
        data = data.date()

    # Fim de semana
    if data.weekday() >= 5:  # 5=sábado, 6=domingo
        return False

    # Feriado
    feriados = _get_feriados()
    if data in feriados:
        return False

    return True


def adicionar_dias_uteis(data_inicio, dias: int) -> Optional[pd.Timestamp]:
    """
    Adiciona N dias úteis a uma data.

    Args:
        data_inicio: data base (Timestamp, datetime ou str)
        dias: número de dias úteis a adicionar

    Returns:
        Timestamp com a data final ou None se inválido
    """
    if pd.isna(data_inicio):
        return None

    # Normaliza
    if isinstance(data_inicio, str):
        data_inicio = pd.to_datetime(data_inicio, dayfirst=True, errors='coerce')
    elif not isinstance(data_inicio, pd.Timestamp):
        data_inicio = pd.Timestamp(data_inicio)

    if pd.isna(data_inicio):
        return None

    data_atual = data_inicio.normalize()
    dias_contados = 0

    while dias_contados < dias:
        data_atual += pd.Timedelta(days=1)
        if eh_dia_util(data_atual):
            dias_contados += 1

    return data_atual


def contar_dias_uteis(data_inicio, data_fim) -> int:
    """
    Conta quantos dias úteis existem entre duas datas (exclusive inicial).

    Args:
        data_inicio: data base
        data_fim: data final

    Returns:
        Inteiro com número de dias úteis
    """
    if pd.isna(data_inicio) or pd.isna(data_fim):
        return 0

    if isinstance(data_inicio, str):
        data_inicio = pd.to_datetime(data_inicio, dayfirst=True, errors='coerce')
    if isinstance(data_fim, str):
        data_fim = pd.to_datetime(data_fim, dayfirst=True, errors='coerce')

    if pd.isna(data_inicio) or pd.isna(data_fim):
        return 0

    data_inicio = pd.Timestamp(data_inicio).normalize()
    data_fim = pd.Timestamp(data_fim).normalize()

    if data_fim < data_inicio:
        return 0

    dias = 0
    data_atual = data_inicio

    while data_atual < data_fim:
        data_atual += pd.Timedelta(days=1)
        if eh_dia_util(data_atual):
            dias += 1

    return dias


def prazo_por_criticidade(criticidade: str) -> Optional[int]:
    """Retorna o prazo em dias úteis para uma dada criticidade."""
    if pd.isna(criticidade):
        return None
    return PRAZO_POR_CRITICIDADE.get(str(criticidade).strip())


def previsao_esperada(criado_data, criticidade: str) -> Optional[pd.Timestamp]:
    """
    Calcula a previsão IDEAL de SLA baseada na criticidade.

    Args:
        criado_data: data de criação do ticket
        criticidade: prioridade/criticidade do ticket

    Returns:
        Timestamp com a previsão ideal ou None
    """
    prazo = prazo_por_criticidade(criticidade)
    if prazo is None:
        return None
    return adicionar_dias_uteis(criado_data, prazo)