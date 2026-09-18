# ============================================================
# tests/test_extrair_data.py
# ============================================================

from datetime import datetime
import pandas as pd
import pytest


# Importa do módulo real
from Programa0_preprocessar import extrair_ultima_data


def test_data_completa_com_hora():
    texto = "04/09/2026 - 14:03: Enviado Teams"
    resultado = extrair_ultima_data(texto)
    assert resultado == datetime(2026, 9, 4, 14, 3)


def test_data_completa_sem_hora():
    texto = "04/09/2026: Enviado"
    resultado = extrair_ultima_data(texto)
    assert resultado == datetime(2026, 9, 4, 0, 0)


def test_celula_zero_retorna_none():
    assert extrair_ultima_data(0) is None
    assert extrair_ultima_data("0") is None


def test_celula_vazia_retorna_none():
    assert extrair_ultima_data("") is None
    assert extrair_ultima_data(None) is None


def test_multiplas_datas_retorna_maior():
    texto = "04/09/2026 - Enviado\n06/09/2026 - Respondido"
    resultado = extrair_ultima_data(texto)
    assert resultado.day == 6


def test_data_curta_sem_ano():
    texto = "31/08: Enviado Teams"
    resultado = extrair_ultima_data(texto, ano_referencia=2026)
    assert resultado == datetime(2026, 8, 31, 0, 0)