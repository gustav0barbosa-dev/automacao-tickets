# 🤖 Automação Help360

Plataforma de automação, monitoramento e análise de tickets do sistema **Help360** (SPPREV).

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-3-green)](https://sqlite.org/)

---

## 🎯 Objetivo

Transformar o processo manual de acompanhamento de tickets em um **pipeline inteligente** com:

- **Coleta** automática da base de tickets (5 anos) via Selenium
- **Enriquecimento** com descrição, movimentações e mensagens
- **Persistência** em banco de dados SQLite
- **Detecção** de backlog, empresa do responsável e status de resposta
- **Análise** de tempo, SLA, produtividade, roteamento e gargalos
- **Diagnóstico** com matriz de verdade (12 cenários)
- **Visualização** em dashboard interativo (Streamlit)

---

## 📊 Funcionalidades

### Pipeline de Coleta

| Programa | O que faz |
|---|---|
| **Programa0** | Processa a Tabela fato (respostas manuais) |
| **Programa1** | Baixa tickets do Help360 |
| **Programa2** | Filtra tickets por status/previsão/categoria |
| **Programa3** | Abre os tickets no navegador |
| **Programa4** | Persiste no banco SQLite |
| **Programa5** | Enriquece com movimentações, mensagens e backlog |

### Análises Suportadas

| Análise | Pergunta que responde |
|---|---|
| **Tempo de Resposta** | Quanto tempo levamos para resolver? |
| **SLA** | Estamos cumprindo prazos? |
| **Produtividade** | Quem resolve mais? Quem acumula? |
| **Roteamento** | Tickets vão direto para a área correta? |
| **Gargalos** | Onde os tickets ficam "esquecidos"? |
| **Diagnóstico** | Tickets SPPREV travados (matriz de verdade) |
| **Reincidência** | O mesmo problema volta? |
| **Backlog** | Quantos estão na fila de backlog? |

### Regras de Negócio Aplicadas

- **Classificação de empresa** por domínio de email (`@sp.gov.br` = SPPREV, `@atlanticsolutions.com.br` = Atlantic)
- **Detecção de backlog** (não gera alerta falso)
- **Tickets travados** — apenas responsáveis SPPREV geram alerta
- **Matriz de verdade** — 12 cenários classificando `responsável × alterador × status`
- **Filtro de resposta** — tickets já respondidos via Tabela fato

---

## 🚀 Início Rápido

### Requisitos

- Windows 10/11
- Python 3.10+
- Google Chrome atualizado
- Conta @sp.gov.br com acesso ao Help360

### Instalação

```powershell
# 1. Clonar
git clone https://github.com/gustav0barbosa-dev/automacao-tickets.git
cd automacao-tickets

# 2. Criar venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Aplicar migrations
python scripts\aplicar_migration.py

# 5. Carregar analistas
python scripts\carregar_analistas.py
Execução Diária
powershell
# Pipeline principal
python main.py

# Atualizar banco
python src\programa4_persistir.py
python src\programa5_enriquecer.py --dias 7

# Aplicar regras de negócio
python scripts\marcar_respondidos.py
python scripts\marcar_empresa_responsavel.py
python scripts\diagnosticar_tickets.py

# Ver dashboard
python -m streamlit run dashboard/app.py
📁 Estrutura do Projeto
text
automacao-tickets/
│
├── main.py                       # Orquestrador
├── requirements.txt
├── README.md
│
├── src/                          # Programas do pipeline
│   ├── programa0_preprocessar.py
│   ├── programa1_download.py
│   ├── programa2_filtrar.py
│   ├── programa3_abrir.py
│   ├── programa4_persistir.py
│   ├── programa5_enriquecer.py
│   └── utils_help360.py
│
├── dashboard/                    # Dashboard modular
│   ├── app.py                    # Entrada
│   ├── config.py                 # Constantes
│   ├── theme.py                  # CSS
│   ├── components.py             # Componentes reutilizáveis
│   ├── data.py                   # Carregamento
│   ├── filters.py                # Filtros sidebar
│   └── views/                    # 8 páginas
│       ├── visao_geral.py
│       ├── tempo_resposta.py
│       ├── sla.py
│       ├── produtividade.py
│       ├── backlog.py
│       ├── roteamento.py
│       ├── reincidencia.py
│       └── diagnostico.py
│
├── scripts/                      # Utilitários
│   ├── aplicar_migration.py
│   ├── carregar_analistas.py
│   ├── marcar_respondidos.py
│   ├── marcar_empresa_responsavel.py
│   ├── diagnosticar_tickets.py
│   ├── verificar_banco.py
│   ├── verificar_ticket.py
│   ├── explorar_ticket.py
│   └── teste.py
│
├── dados/                        # Dados (não versionados)
│   ├── tickets.db
│   ├── migrations/               # SQL de evolução do schema
│   ├── historicos/               # Excel baixados
│   ├── logs/                     # Logs
│   └── backup/                   # Backups
│
├── config/                       # Configurações
│   ├── settings.yaml
│   └── categorias_fora.txt
│
└── docs/                         # Documentação técnica
    ├── README.md                 # Índice
    ├── 01_VISAO_E_ESCOPO.md
    ├── 02_REQUISITOS.md
    ├── 03_ARQUITETURA.md
    ├── 04_MODELO_DADOS.md
    ├── 05_REGRAS_DE_NEGOCIO.md
    ├── 06_ANALISES_E_METRICAS.md
    ├── 07_INTERFACES.md
    ├── 08_INSTALACAO_E_CONFIG.md
    ├── 09_OPERACAO_E_MANUTENCAO.md
    ├── 10_TESTES.md
    ├── 11_ROADMAP.md
    ├── 12_GLOSSARIO.md
    └── 13_CHANGELOG.md
📊 Dashboard — 8 Abas
Aba	O que mostra
🏠 Visão Geral	KPIs gerais, status, prioridade, categorias
⏱️ Tempo de Resposta	Distribuição, P50/P90/P99, por categoria
📊 SLA	Cumprimento, ranking, margem
👥 Produtividade	Ranking por analista, dispersão, sobrecarga
📋 Backlog	Aging, distribuição, tickets mais antigos
🔄 Roteamento	Pulos, gargalos, gaps entre movimentações
🔁 Reincidência	Solicitantes recorrentes, categorias
🚨 Diagnóstico	Matriz de verdade, tickets travados, ação interna
Filtros Disponíveis
Período (criado em)

Status (Em atendimento, Resolvido, etc.)

Categoria (Acessos SIGEPREV, Cadastro, etc.)

Responsável (por nome)

Tipo de Empresa (SPPREV, Atlantic, Externo, Outro)

Status de Resposta (Todos, Respondidos, Não respondidos)

Backlog (Todos, Em backlog, Fora do backlog)

Ação Interna (Todos, Resp. = Alterador, Resp. ≠ Alterador)

🗄️ Banco de Dados
SQLite em dados/tickets.db.

Tabelas
Tabela	Registros	O que guarda
tickets	~10.000	Cadastro + status + análise
movimentacoes	~3.000	Histórico de mudanças
mensagens	~500	Área de mensagens
analistas	~410	Cadastro de pessoas
areas	~30	Áreas padronizadas
snapshots	~50	Execuções do pipeline
Views
vw_tempo_resposta — tempos de resolução

vw_sla — cumprimento de SLA

vw_nao_retorno — analistas que demoram a agir

Detalhes: 04_Modelo_Dados.md

🔧 Scripts Auxiliares
Script	Uso
scripts/aplicar_migration.py	Aplica migrations SQL
scripts/carregar_analistas.py	Popula tabela analistas
scripts/marcar_respondidos.py	Marca tickets respondidos
scripts/marcar_empresa_responsavel.py	Classifica por empresa
scripts/diagnosticar_tickets.py	Aplica matriz de verdade
scripts/verificar_banco.py	Verifica schema
scripts/verificar_ticket.py <ID>	Detalhes de um ticket
scripts/explorar_ticket.py --id <ID>	Explora HTML de um ticket
🎯 Estado Atual
✅ Implementado
Pipeline completo (coleta → enriquecimento → análise)

Dashboard com 8 abas

14 colunas analíticas em tickets

Matriz de verdade (12 cenários)

Detecção de backlog

Classificação SPPREV/Atlantic

Filtros globais avançados

📋 Roadmap
Fase 5: Alertas automáticos por email

Fase 6: NLP (classificação de rotas, sumarização)

Fase 7: Relatórios PDF para supervisão

Fase 8: Análise de SLA por criticidade (dias úteis)

Detalhes: 11_Roadmap.md

📚 Documentação
Documento	Conteúdo
01 — Visão e Escopo	Objetivo, problema, público
02 — Requisitos	RF e RNF
03 — Arquitetura	Camadas, componentes, ADRs
04 — Modelo de Dados	Schema SQLite
05 — Regras de Negócio	Regras do domínio
06 — Análises	Catálogo de métricas
07 — Interfaces	Contratos, arquivos, URLs
08 — Instalação	Setup do ambiente
09 — Operação	Guia de uso e troubleshooting
10 — Testes	Estratégia de testes
11 — Roadmap	Fases de evolução
12 — Glossário	Termos técnicos
13 — Changelog	Histórico de versões
⚠️ Segurança e LGPD
❌ Nunca commitar .db ou .xlsx no Git

❌ Nunca expor CPF, email ou telefone em relatórios

✅ Sempre usar getpass para senhas

✅ Sempre anonimizar dados sensíveis antes de compartilhar

Detalhes: 05_Regras_de_Negocio.md#lgpd

🛠️ Tecnologias
Camada	Tecnologia
Linguagem	Python 3.10+
Automação web	Selenium + webdriver-manager
Dados	Pandas + openpyxl
Banco	SQLite 3
Dashboard	Streamlit + Plotly
Versionamento	Git + GitHub
📞 Contato
Papel	Nome
Product Owner	Marilia Amaral Marcondes | Gustavo Henrique Barbosa da Silva
Mantenedor	Gustavo Henrique Barbosa da Silva
Equipe	DIO/SPRO — SPPREV
Repositório: github.com/gustav0barbosa-dev/automacao-tickets