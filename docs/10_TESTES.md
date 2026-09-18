# 10 — Testes

**Documento:** Estratégia e Plano de Testes
**Versão:** 3.0
**Última atualização:** Setembro/2026
**Público-alvo:** Desenvolvedores, QA

---

## 1. Introdução

Este documento define a **estratégia de testes** da Automação Help360, cobrindo:

- **Testes unitários** — funções isoladas
- **Testes de integração** — módulos combinados
- **Testes end-to-end** — fluxo completo (roadmap)
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

**Meta atual:** 90% unitários + 10% integração.

### 1.2 Status Atual

| Tipo | Qtde | Status |
|---|---|---|
| Unitários | 25 | ✅ Implementados |
| Integração | 5 | ✅ Implementados |
| Migrations | 5 | ✅ Implementados |
| **Total** | **33** | ✅ Todos passando |

---

## 2. Ferramentas

| Ferramenta | Uso |
|---|---|
| **pytest** | Framework principal |
| **pytest-cov** | Cobertura de código |
| **pytest-mock** | Mocks e stubs |
| **unittest.mock** | Mocks nativos |
| **SQLite `:memory:`** ou `tmp_path` | Banco temporário |

### 2.1 Instalação

```bash
pip install -r requirements-dev.txt
Ou individualmente:

bash
pip install pytest pytest-cov pytest-mock
3. Estrutura dos Testes
text
tests/
├── __init__.py
├── conftest.py                  # Fixtures compartilhadas
├── README.md                    # Guia rápido
├── test_utils.py                # Funções do utils_help360
├── test_extrair_data.py         # Parser de datas
├── test_diagnostico.py          # Matriz de verdade
├── test_carregar_analistas.py   # Classificação de empresa
├── test_migrations.py           # Migrations SQL
└── test_integracao.py           # Fluxo com banco temporário
4. Testes Unitários
4.1 test_extrair_data.py (6 testes)
Valida o parser de datas da Tabela fato.

Teste	O que valida
test_data_completa_com_hora	"04/09/2026 - 14:03"
test_data_completa_sem_hora	"04/09/2026"
test_celula_zero_retorna_none	Ignora 0
test_celula_vazia_retorna_none	Ignora ''
test_multiplas_datas_retorna_maior	Pega a maior data
test_data_curta_sem_ano	"31/08" usa ano atual
4.2 test_utils.py (7 testes)
Valida funções do utils_help360.

Teste	O que valida
test_tratar_datas_br	Conversão DD/MM/AAAA
test_tratar_datas_ignora_coluna_inexistente	Não estoura KeyError
test_tratar_datas_valor_invalido_vira_nat	Erro vira NaT
test_filtrar_categoria_remove_blacklist	Remove categorias fora
test_anonimizar_cpf	CPF → <CPF>
test_anonimizar_email	Email → <EMAIL>
test_anonimizar_telefone	Telefone → <TELEFONE>
4.3 test_diagnostico.py (7 testes)
Valida a matriz de verdade dos 12 cenários.

Teste	Cenário
test_cen_01_spprev_spprev_aguardando	CEN-01
test_cen_02_spprev_atlantic_aguardando	CEN-02
test_cen_03_spprev_spprev_em_atendimento	CEN-03
test_cen_10_atlantic_atlantic_em_atendimento	CEN-10
test_cen_12_atlantic_atlantic_resolvido	CEN-12
test_sem_dados_quando_alterado_por_nan	SEM_DADOS
test_outro_quando_status_nao_mapeado	OUTRO
4.4 test_carregar_analistas.py (5 testes)
Valida a classificação de empresa.

Teste	Classificação
test_classificar_spprev	@sp.gov.br → SPPREV
test_classificar_atlantic	@atlanticsolutions.com.br → Atlantic
test_classificar_outro	Outro domínio → Outro
test_classificar_vazio	Vazio → Outro
test_classificar_case_insensitive	Case-insensitive
5. Testes de Integração
5.1 test_migrations.py (5 testes)
Valida as migrations SQL.

Teste	O que valida
test_pasta_migrations_existe	Pasta dados/migrations
test_migrations_sao_arquivos_sql	Todas com .sql
test_migrations_tem_numeracao	Prefixo numérico
test_migration_001_adiciona_colunas	Colunas extras em tickets
test_migration_002_adiciona_sprint_features	Backlog, respondido, etc.
5.2 test_integracao.py (3 testes)
Valida operações reais no banco.

Teste	O que valida
test_popular_analistas	INSERT + SELECT em analistas
test_inserir_tickets	INSERT de tickets
test_tickets_travados_spprev	Query de tickets travados (só SPPREV)
6. Fixtures (conftest.py)
Fixture	Retorno
banco_temporario	SQLite em tmp_path com schema mínimo
df_tickets_basico	DataFrame com 5 tickets de exemplo
df_analistas	DataFrame com 3 analistas
7. Como Rodar
7.1 Rodar todos
bash
pytest tests/
7.2 Verbose
bash
pytest tests/ -v
7.3 Arquivo específico
bash
pytest tests/test_diagnostico.py -v
7.4 Teste específico
bash
pytest tests/test_diagnostico.py::test_cen_01_spprev_spprev_aguardando -v
7.5 Por padrão (marker)
bash
pytest -m "not slow" tests/
7.6 Para no primeiro erro
bash
pytest tests/ -x
7.7 Só os últimos falhados
bash
pytest tests/ --lf
8. Cobertura de Código
8.1 Medir
bash
pytest --cov=src --cov=scripts tests/
8.2 Relatório HTML
bash
pytest --cov=src --cov-report=html tests/
# Abrir htmlcov/index.html
8.3 Meta
Módulo	Meta
utils_help360.py	80%
programa0_preprocessar.py	80%
scripts/diagnosticar_tickets.py	80%
scripts/carregar_analistas.py	80%
programa5_enriquecer.py	40% (Selenium)
programa1_download.py	40% (Selenium)
8.4 Exemplo de Saída
text
Name                              Stmts   Miss  Cover
-----------------------------------------------------
src/utils_help360.py                150     15    90%
src/programa0_preprocessar.py        85     10    88%
scripts/diagnosticar_tickets.py     120     20    83%
scripts/carregar_analistas.py        60      5    92%
-----------------------------------------------------
TOTAL                               415     50    88%
9. Boas Práticas
9.1 ✅ Fazer
Um teste por comportamento

Nomes descritivos (test_cen_01_...)

Fixtures para setup repetido

Mocks para chamadas externas (Selenium, rede)

Rodar testes antes de cada commit

Simular estado ANTES da migration (não depois)

Testar valores-limite (0, vazio, negativo)

9.2 ❌ Não Fazer
Testar múltiplas coisas no mesmo teste

Depender de ordem de execução

Fazer chamadas reais à internet

Ignorar testes falhando

Testar código de terceiros (Pandas, Selenium)

Criar tabelas que a migration vai criar

Deixar dados entre testes (usar fixtures com cleanup)

10. Como Adicionar um Novo Teste
10.1 Cenário: Testar função nova foo()
Passo 1: Identifique o arquivo de teste apropriado.

Passo 2: Escreva o teste:

python
def test_foo_retorna_esperado():
    from meu_modulo import foo
    resultado = foo("entrada")
    assert resultado == "saída esperada"
Passo 3: Rode:

bash
pytest tests/test_meu_modulo.py -v
Passo 4: Se passar, commit.

10.2 Cenário: Testar erro
python
def test_foo_erro_quando_entrada_invalida():
    from meu_modulo import foo
    with pytest.raises(ValueError):
        foo(None)
10.3 Cenário: Usar fixture
python
def test_com_banco(banco_temporario):
    conn = banco_temporario
    conn.execute("INSERT INTO analistas VALUES ('X', 'x@x.com', 'SPPREV')")
    conn.commit()
    assert conn.execute('SELECT COUNT(*) FROM analistas').fetchone()[0] == 1
11. Testes Manuais
11.1 Checklist de Release
Antes de commitar mudanças significativas:

□ Rodar pytest — todos passando
□ Rodar pytest --cov — cobertura não caiu
□ Rodar python main.py em ambiente de teste
□ Verificar acompanhamento.xlsx gerado
□ Confirmar que o Chrome abriu as abas corretas
□ Verificar dashboard (todas as 8 abas)
11.2 Teste de Regressão
Ao corrigir um bug:

Escrever um teste que reproduz o bug

Rodar — deve falhar

Corrigir o código

Rodar de novo — deve passar

Commitar código + teste juntos

12. Roadmap de Testes
12.1 Curto Prazo
□ Testes para programa2_filtrar.py
□ Testes para programa4_persistir.py
□ Testes para programa5_enriquecer.py (com mocks do Selenium)
□ Testes para o dashboard (Streamlit testing)
12.2 Médio Prazo
□ Testes E2E com Selenium (navegador headless)
□ Testes de carga (locust com 10k tickets)
□ CI/CD com GitHub Actions
12.3 Longo Prazo
□ Testes de integração contínua
□ Cobertura > 90% em todos os módulos
□ Testes de regressão automatizados
13. CI/CD (Futuro)
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
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ -v --cov=src
14. Referências
pytest Documentation

pytest-cov

09_Operacao_e_Manutencao.md

tests/README.md