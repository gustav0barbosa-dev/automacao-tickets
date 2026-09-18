# ============================================================
# tests/test_utils.py
# ============================================================

import pandas as pd
import pytest
from datetime import datetime


def test_tratar_datas_br():
    from utils_help360 import tratar_datas_excel
    df = pd.DataFrame({'Alterado Data': ['04/09/2026']})
    resultado = tratar_datas_excel(df)
    assert resultado['Alterado Data'].iloc[0] == datetime(2026, 9, 4)


def test_tratar_datas_ignora_coluna_inexistente():
    from utils_help360 import tratar_datas_excel
    df = pd.DataFrame({'ID': [1, 2]})
    resultado = tratar_datas_excel(df)
    # Não deve estourar KeyError
    assert 'ID' in resultado.columns


def test_tratar_datas_valor_invalido_vira_nat():
    from utils_help360 import tratar_datas_excel
    df = pd.DataFrame({'Alterado Data': ['não é data']})
    resultado = tratar_datas_excel(df)
    assert pd.isna(resultado['Alterado Data'].iloc[0])


def test_filtrar_categoria_remove_blacklist():
    from utils_help360 import filtrar_categoria
    df = pd.DataFrame({
        'Categoria': ['Java', 'Folha de Pagamento', 'Cadastro']
    })
    resultado = filtrar_categoria(df)
    assert 'Folha de Pagamento' not in resultado['Categoria'].values
    assert 'Java' in resultado['Categoria'].values


def test_anonimizar_cpf():
    from utils_help360 import anonimizar_dados_lgpd
    texto = "CPF 123.456.789-00 do usuário"
    resultado = anonimizar_dados_lgpd(texto)
    assert '<CPF>' in resultado
    assert '123.456.789-00' not in resultado


def test_anonimizar_email():
    from utils_help360 import anonimizar_dados_lgpd
    texto = "contato: joao@sp.gov.br"
    resultado = anonimizar_dados_lgpd(texto)
    assert '<EMAIL>' in resultado


def test_anonimizar_telefone():
    from utils_help360 import anonimizar_dados_lgpd
    texto = "telefone (11) 98765-4321"
    resultado = anonimizar_dados_lgpd(texto)
    assert '<TELEFONE>' in resultado