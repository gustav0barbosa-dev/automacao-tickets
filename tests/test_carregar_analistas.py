# ============================================================
# tests/test_carregar_analistas.py
# ============================================================

import pytest


def classificar_empresa(email):
    """Replica a lógica de scripts/carregar_analistas.py."""
    import pandas as pd
    if not email or pd.isna(email):
        return 'Outro'
    email = str(email).lower()
    if '@atlanticsolutions.com.br' in email:
        return 'Atlantic'
    if '@sp.gov.br' in email:
        return 'SPPREV'
    return 'Outro'


def test_classificar_spprev():
    assert classificar_empresa('joao@sp.gov.br') == 'SPPREV'


def test_classificar_atlantic():
    assert classificar_empresa('maria@atlanticsolutions.com.br') == 'Atlantic'


def test_classificar_outro():
    assert classificar_empresa('teste@lab360.com.br') == 'Outro'


def test_classificar_vazio():
    assert classificar_empresa('') == 'Outro'
    assert classificar_empresa(None) == 'Outro'


def test_classificar_case_insensitive():
    assert classificar_empresa('JOAO@SP.GOV.BR') == 'SPPREV'
    assert classificar_empresa('MARIA@ATLANTICSOLUTIONS.COM.BR') == 'Atlantic'