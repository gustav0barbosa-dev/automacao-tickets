# 10 — Testes

**Documento:** Estratégia e Plano de Testes
**Versão:** 2.0
**Público-alvo:** Desenvolvedores, QA

---

## 1. Introdução

Este documento define a **estratégia de testes** da Automação Help360, cobrindo:

- **Testes unitários** — funções isoladas
- **Testes de integração** — módulos combinados
- **Testes end-to-end** — fluxo completo
- **Testes de carga** — comportamento sob volume
- **Testes manuais** — validação humana

### 1.1 Pirâmide de Testes
▲
╱ ╲ E2E (poucos, lentos)
╱───╲
╱ ╲ Integração (médios)
╱───────╲
╱ ╲ Unitários (muitos, rápidos)
╱───────────╲

text

**Meta:** 60% unitários, 30% integração, 10% E2E.

---

## 2. Ferramentas

| Ferramenta | Uso |
|---|---|
| **pytest** | Framework principal de testes |
| **pytest-cov** | Cobertura de código |
| **pytest-mock** | Mocks e stubs |
| **unittest.mock** | Mocks nativos |
| **Selenium** | Testes E2E de scraping |
| **SQLite `:memory:`** | Banco temporário para testes |

### 2.1 Instalação

```powershell
pip install pytest pytest-cov pytest-mock
3. Testes Unitários
3.1 O que testar
Funções puras (mesma entrada → mesma saída):

Módulo	Função	O que valida
utils_help360	tratar_datas_excel	Conversão de datas BR/ISO
utils_help360	filtrar_categoria	Remoção de categorias
utils_help360	anonimizar_dados_lgpd	Regex de CPF/email/telefone
programa0	extrair_ultima_data	Parsing de texto com datas
programa2	aplicar_filtros	Lógica dos 6 filtros
3.2 Exemplo — Teste de extrair_ultima_data
python
# tests/test_extrair_data.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from programa0_preprocessar import extrair_ultima_data
from datetime import datetime


def test_data_completa_com_hora():
    texto = "04/09/2026 - 14:03: Enviado Teams"
    resultado = extrair_ultima_data(texto)
    assert resultado == datetime(2026, 9, 4, 14, 3)


def test_data_completa_sem_hora():
    texto = "04/09/2026: Enviado Teams"
    resultado = extrair_ultima_data(texto)
    assert resultado == datetime(2026, 9, 4, 0, 0)


def test_data_curta():
    texto = "31/08: Enviado Teams"
    resultado = extrair_ultima_data(texto, ano_referencia=2026)
    assert resultado == datetime(2026, 8, 31, 0, 0)


def test_multiplas_datas_retorna_maior():
    texto = "04/09/2026 - Enviado\n06/09/2026 - Respondido"
    resultado = extrair_ultima_data(texto)
    assert resultado.day == 6


def test_celula_zero_retorna_none():
    assert extrair_ultima_data(0) is None
    assert extrair_ultima_data("0") is None


def test_celula_vazia_retorna_none():
    assert extrair_ultima_data("") is None
    assert extrair_ultima_data(None) is None


def test_celula_na_retorna_none():
    assert extrair_ultima_data("#N/A") is None
    assert extrair_ultima_data("-") is None
3.3 Exemplo — Teste de tratar_datas_excel
python
# tests/test_datas.py
import pandas as pd
from datetime import datetime
from utils_help360 import tratar_datas_excel


def test_converte_data_br():
    df = pd.DataFrame({'Alterado Data': ['04/09/2026']})
    resultado = tratar_datas_excel(df)
    assert resultado['Alterado Data'].iloc[0] == datetime(2026, 9, 4)


def test_converte_data_com_hora():
    df = pd.DataFrame({'Alterado Data': ['04/09/2026 14:30']})
    resultado = tratar_datas_excel(df)
    assert resultado['Alterado Data'].iloc[0] == datetime(2026, 9, 4, 14, 30)


def test_ignora_coluna_inexistente():
    df = pd.DataFrame({'ID': [1, 2]})
    resultado = tratar_datas_excel(df)
    # Não deve estourar KeyError
    assert 'ID' in resultado.columns


def test_valor_invalido_vira_nat():
    df = pd.DataFrame({'Alterado Data': ['não é data']})
    resultado = tratar_datas_excel(df)
    assert pd.isna(resultado['Alterado Data'].iloc[0])
3.4 Como rodar
powershell
pytest tests/ -v
Saída esperada:

text
tests/test_extrair_data.py::test_data_completa_com_hora PASSED
tests/test_extrair_data.py::test_celula_zero_retorna_none PASSED
...
======================== 12 passed in 0.42s ========================
4. Testes de Integração
4.1 O que testar
Combinações de módulos:

Cenário	Módulos envolvidos
Ler Tabela fato → gerar tickets_com_respondido.xlsx	Programa0
Carregar 2 Excels → aplicar filtros → gerar acompanhamento.xlsx	Programa2
Persistir DataFrame → consultar SQLite	Programa4
4.2 Exemplo — Teste do Programa2
python
# tests/test_programa2.py
import pandas as pd
import sqlite3
import pytest
from programa2_filtrar import aplicar_filtros


@pytest.fixture
def tickets_df():
    return pd.DataFrame({
        'ID': [1, 2, 3, 4],
        'Status': ['Em atendimento', 'Resolvido', 'Em atendimento', 'Resolvido'],
        'Alterado Data': pd.to_datetime([
            '2026-09-10', '2026-09-05', '2026-08-01', '2026-09-12'
        ]),
        'Previsão': pd.to_datetime([
            '2026-09-15', None, '2026-09-01', None
        ]),
        'Categoria': ['Java', 'Folha', 'Java', 'Rubricas'],
        'Responsável': ['Ana', 'Bruno', 'Carlos', 'Diana']
    })


@pytest.fixture
def respondidos_df():
    return pd.DataFrame({
        'ID': ['1', '2', '3'],
        'Data Respondido': pd.to_datetime([
            '2026-09-08', '2026-09-06', '2026-08-05'
        ])
    })


def test_filtro_status_temporal(tickets_df, respondidos_df):
    resultado = aplicar_filtros(tickets_df, respondidos_df)
    # Ticket 4 é Resolvido recente → deve passar
    assert 4 in resultado['ID'].values


def test_filtro_categoria(tickets_df, respondidos_df):
    resultado = aplicar_filtros(tickets_df, respondidos_df)
    # Ticket 4 é "Rubricas" → deve ser removido
    assert 4 not in resultado['ID'].values or 'Rubricas' not in resultado['Categoria'].values


def test_filtro_respondido(tickets_df, respondidos_df):
    resultado = aplicar_filtros(tickets_df, respondidos_df)
    # Ticket 2 foi respondido DEPOIS de alterado → não deve passar
    assert 2 not in resultado['ID'].values
5. Testes End-to-End (E2E)
5.1 O que testar
Fluxo completo, de ponta a ponta:

Ler Tabela fato

Processar

Filtrar

Persistir

5.2 Exemplo com dados sintéticos
python
# tests/test_e2e.py
import pandas as pd
import os
import tempfile
from programa0_preprocessar import extrair_anotacoes
from programa2_filtrar import aplicar_filtros


def test_fluxo_completo(tmp_path):
    # Setup: cria planilhas de teste
    df_status = pd.DataFrame({'ID': [1, 2, 3]})
    df_acomp = pd.DataFrame({
        'ID': [1, 2, 3],
        'Semana1': ['04/09/2026 - Enviado', 0, 0],
        'Semana2': [0, '05/09/2026 - Enviado', 0],
    })

    # Executa
    anotacoes = extrair_anotacoes(df_acomp, df_status)

    # Valida
    assert len(anotacoes) == 3
    assert anotacoes[anotacoes['ID'] == '1']['Data Respondido'].notna().any()
    assert anotacoes[anotacoes['ID'] == '3']['Data Respondido'].isna().any()
6. Testes Manuais
6.1 Checklist de release
Antes de commitar uma mudança significativa:

□ Rodar pytest — todos os testes passando
□ Rodar python main.py em ambiente de teste
□ Verificar acompanhamento.xlsx gerado
□ Confirmar que o Chrome abriu as abas corretas
□ Verificar logs por warnings
6.2 Teste de regressão
Sempre que corrigir um bug:

Escrever um teste que reproduz o bug

Rodar o teste — deve falhar

Corrigir o código

Rodar o teste novamente — deve passar

Commitar código + teste juntos

7. Cobertura de Código
7.1 Medir cobertura
powershell
pytest --cov=src tests/
Saída:

text
Name                       Stmts   Miss  Cover
----------------------------------------------
src/programa0_preprocessar.py   85     12    86%
src/programa1_download.py       45     30    33%
src/programa2_filtrar.py       120      8    93%
src/utils_help360.py           150     45    70%
----------------------------------------------
TOTAL                          400     95    76%
7.2 Meta
Módulo	Meta
utils_help360.py	80%
programa0_preprocessar.py	80%
programa2_filtrar.py	80%
programa1_download.py	40% (Selenium é difícil de testar)
programa3_abrir.py	40%
7.3 Gerar relatório HTML
powershell
pytest --cov=src --cov-report=html tests/
Abre htmlcov/index.html no navegador.

8. Estrutura de Testes
text
tests/
├── __init__.py
├── conftest.py                  # Fixtures compartilhadas
├── test_extrair_data.py
├── test_datas.py
├── test_filtros.py
├── test_lgpd.py
├── test_programa0.py
├── test_programa2.py
└── test_e2e.py
8.1 conftest.py exemplo
python
# tests/conftest.py
import sys
import os

# Adiciona src/ ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
9. Boas Práticas
9.1 ✅ Fazer
Um teste por comportamento

Nomes descritivos (test_celula_zero_retorna_none)

Fixtures para setup repetido

Mock para chamadas externas (Selenium, rede)

Rodar testes antes de cada commit

9.2 ❌ Não fazer
Testar múltiplas coisas no mesmo teste

Depender de ordem de execução

Fazer chamadas reais à internet

Ignorar testes falhando

Testar código de terceiros (Pandas, Selenium)

10. Automação de Testes (CI/CD)
10.1 GitHub Actions (futuro)
Criar .github/workflows/tests.yml:

yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/ -v
11. Referências
02_Requisitos.md

05_Regras_de_Negocio.md

pytest Documentation
"""