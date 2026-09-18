# ============================================================
# tests/test_diagnostico.py
# ============================================================

import pandas as pd
import pytest


def classificar_simples(responsavel, alterado_por, status, mapa_empresa):
    """
    Versão simplificada da função classificar() para testes.
    Replica a lógica de scripts/diagnosticar_tickets.py.
    """
    pendente_usuario = (status == 'Aguardando confirmação do usuário')

    if pd.isna(alterado_por):
        return (None, int(pendente_usuario), 'SEM_DADOS')

    resp_emp = mapa_empresa.get(responsavel, 'Externo')
    alt_emp = mapa_empresa.get(alterado_por, 'Externo')

    def tipo(e):
        if e == 'SPPREV': return 'SPPREV'
        if e == 'Atlantic': return 'Atlantic'
        return 'OUTRO'

    resp_t = tipo(resp_emp)
    alt_t = tipo(alt_emp)
    acao_interna = (responsavel == alterado_por)

    if resp_t == 'SPPREV':
        if pendente_usuario and alt_t == 'SPPREV':     diag = 'CEN-01'
        elif pendente_usuario and alt_t == 'Atlantic': diag = 'CEN-02'
        elif status == 'Em atendimento' and alt_t == 'SPPREV': diag = 'CEN-03'
        elif status == 'Em atendimento' and alt_t == 'Atlantic': diag = 'CEN-04'
        elif status == 'Resolvido' and alt_t == 'SPPREV': diag = 'CEN-05'
        elif status == 'Resolvido' and alt_t == 'Atlantic': diag = 'CEN-06'
        else: diag = 'OUTRO'
    elif resp_t == 'Atlantic':
        if pendente_usuario and alt_t == 'SPPREV':     diag = 'CEN-07'
        elif pendente_usuario and alt_t == 'Atlantic': diag = 'CEN-08'
        elif status == 'Em atendimento' and alt_t == 'SPPREV': diag = 'CEN-09'
        elif status == 'Em atendimento' and alt_t == 'Atlantic': diag = 'CEN-10'
        elif status == 'Resolvido' and alt_t == 'SPPREV': diag = 'CEN-11'
        elif status == 'Resolvido' and alt_t == 'Atlantic': diag = 'CEN-12'
        else: diag = 'OUTRO'
    else:
        diag = 'OUTRO'

    return (int(acao_interna), int(pendente_usuario), diag)


@pytest.fixture
def mapa_empresa():
    return {
        'João SPPREV': 'SPPREV',
        'Maria Atlantic': 'Atlantic',
    }


# ==================== CENÁRIOS ====================
def test_cen_01_spprev_spprev_aguardando(mapa_empresa):
    r = classificar_simples('João SPPREV', 'João SPPREV',
                             'Aguardando confirmação do usuário', mapa_empresa)
    assert r[2] == 'CEN-01'
    assert r[0] == 1  # ação interna


def test_cen_02_spprev_atlantic_aguardando(mapa_empresa):
    r = classificar_simples('João SPPREV', 'Maria Atlantic',
                             'Aguardando confirmação do usuário', mapa_empresa)
    assert r[2] == 'CEN-02'
    assert r[0] == 0  # ação externa


def test_cen_03_spprev_spprev_em_atendimento(mapa_empresa):
    r = classificar_simples('João SPPREV', 'João SPPREV',
                             'Em atendimento', mapa_empresa)
    assert r[2] == 'CEN-03'


def test_cen_10_atlantic_atlantic_em_atendimento(mapa_empresa):
    r = classificar_simples('Maria Atlantic', 'Maria Atlantic',
                             'Em atendimento', mapa_empresa)
    assert r[2] == 'CEN-10'


def test_cen_12_atlantic_atlantic_resolvido(mapa_empresa):
    r = classificar_simples('Maria Atlantic', 'Maria Atlantic',
                             'Resolvido', mapa_empresa)
    assert r[2] == 'CEN-12'


def test_sem_dados_quando_alterado_por_nan(mapa_empresa):
    r = classificar_simples('João SPPREV', None, 'Em atendimento', mapa_empresa)
    assert r[2] == 'SEM_DADOS'
    assert r[0] is None


def test_outro_quando_status_nao_mapeado(mapa_empresa):
    r = classificar_simples('João SPPREV', 'João SPPREV',
                             'Fechado', mapa_empresa)
    assert r[2] == 'OUTRO'