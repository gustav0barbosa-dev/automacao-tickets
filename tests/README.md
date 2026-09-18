# 🧪 Testes Automatizados

Testes da Automação Help360, usando **pytest**.

## Estrutura
tests/
├── conftest.py # Fixtures compartilhadas
├── test_utils.py # Funções do utils_help360
├── test_extrair_data.py # Parser de datas
├── test_diagnostico.py # Matriz de verdade
├── test_carregar_analistas.py # Classificação de empresa
├── test_migrations.py # Migrations SQL
└── test_integracao.py # Fluxo com banco temporário


## Como Rodar

### Instalar dependências

```bash
pip install pytest pytest-cov
Rodar todos os testes
bash
pytest tests/
Rodar com verbose
bash
pytest tests/ -v
Rodar um arquivo específico
bash
pytest tests/test_diagnostico.py -v
Rodar um teste específico
bash
pytest tests/test_diagnostico.py::test_cen_01_spprev_spprev_aguardando -v
Ver cobertura
bash
pytest --cov=src --cov=scripts --cov=dashboard tests/
Gerar relatório HTML
bash
pytest --cov=src --cov-report=html tests/
# Abrir htmlcov/index.html
O que Testar
Módulo	O que é testado
test_utils.py	Conversão de datas, filtros, anonimização LGPD
test_extrair_data.py	Parser de datas do texto da Tabela fato
test_diagnostico.py	Matriz de verdade (12 cenários)
test_carregar_analistas.py	Classificação SPPREV/Atlantic/Outro
test_migrations.py	Aplicação de migrations SQL
test_integracao.py	Inserção + queries no banco
Boas Práticas
✅ Fazer
Um teste por comportamento

Nomes descritivos (test_cen_01_...)

Fixtures para setup repetido

Mocks para dependências externas

Rodar testes antes de cada commit

❌ Não Fazer
Testar múltiplas coisas no mesmo teste

Depender de ordem de execução

Fazer chamadas reais à internet

Ignorar testes falhando

Testar código de terceiros (Pandas, Selenium)

Cobertura Atual
Módulo	Cobertura
utils_help360.py	✅ Alta
programa0_preprocessar.py	✅ Alta
scripts/diagnosticar_tickets.py	✅ Média
scripts/carregar_analistas.py	✅ Alta
programa5_enriquecer.py	⚠️ Baixa (Selenium)
Meta: 80% de cobertura nos módulos puros.

CI/CD (futuro)
Integração com GitHub Actions:

yaml
# .github/workflows/tests.yml
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
Referências
Documentação do Pytest

docs/10_TESTES.md