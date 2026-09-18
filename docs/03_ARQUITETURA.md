# 03 — Arquitetura

**Documento:** Arquitetura de Software (SDD)
**Versão:** 3.0
**Última atualização:** Setembro/2026
**Público-alvo:** Desenvolvedores, arquitetos, DevOps

---

## 1. Visão Geral

A Automação Help360 evoluiu para **três camadas** com responsabilidades distintas:
┌──────────────────────────────────────────────────────────────────┐
│ CAMADA 1 — COLETA │
│ (Selenium + Pandas → Excel) │
│ │
│ Baixa, processa, filtra e abre tickets │
└──────────────────────────────────────────────────────────────────┘
│
▼
┌──────────────────────────────────────────────────────────────────┐
│ CAMADA 2 — PERSISTÊNCIA E ENRIQUECIMENTO │
│ (SQLite + Selenium) │
│ │
│ Grava no banco, enriquece com movs + mensagens + backlog │
└──────────────────────────────────────────────────────────────────┘
│
▼
┌──────────────────────────────────────────────────────────────────┐
│ CAMADA 3 — ANÁLISE │
│ (SQL + Pandas + Streamlit) │
│ │
│ Aplica regras de negócio, diagnóstico e visualização │
└──────────────────────────────────────────────────────────────────┘

text

**Princípio:** cada camada é **independente**. A camada 3 pode rodar sozinha (com dados históricos), e as camadas 1 e 2 continuam funcionando mesmo se a 3 falhar.

---

## 2. Diagrama de Blocos — Visão Completa
┌─────────────────────────────────────────────────────────────────────────┐
│ ENTRADAS │
│ │
│ 📄 Tabela fato.xlsx 🌐 Site Help360 📊 usuario_empresa.xlsx │
│ (manual, operador) (5 anos de tickets) (lista de analistas) │
└───────┬──────────────────────────┬────────────────────────┬──────────────┘
│ │ │
▼ ▼ ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ PROGRAMA 0 │ │ PROGRAMA 1 │ │ SCRIPT │
│ processa │ │ Selenium │ │ carregar_ │
│ Tabela fato │ │ download │ │ analistas │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
│ │ │
▼ ▼ ▼
tickets_com_respondido.xlsx tickets.xlsx tabela analistas
│ │ │
└──────────────┬───────────┘ │
▼ │
┌───────────────┐ │
│ PROGRAMA 2 │ │
│ 6 filtros │ │
└───────┬───────┘ │
│ │
▼ │
acompanhamento.xlsx │
│ │
▼ │
┌───────────────┐ │
│ PROGRAMA 3 │ │
│ abre no │ │
│ navegador │ │
└───────────────┘ │
│
══════════════════════════════════════════════╪════════
FIM DA CAMADA 1 │
══════════════════════════════════════════════╪════════
│
┌───────────────┐ │
│ PROGRAMA 4 │ │
│ persiste em │ │
│ SQLite │ │
└───────┬───────┘ │
│ │
▼ │
tickets.db │
│ │
▼ │
┌───────────────┐ │
│ PROGRAMA 5 │ │
│ enriquece: │ │
│ - movs │ │
│ - msgs │ │
│ - backlog │ │
└───────┬───────┘ │
│ │
▼ │
tickets.db ◄────────────────────────┘
│
═══════════════════════════════════════════════════════
FIM DA CAMADA 2
═══════════════════════════════════════════════════════
│
▼
┌─────────────────────┐
│ SCRIPTS ANÁLISE │
│ - carregar_analistas
│ - marcar_respondidos
│ - marcar_empresa
│ - diagnosticar │
└─────────┬───────────┘
│
▼
┌─────────────────┐
│ DASHBOARD │
│ (8 páginas) │
└─────────────────┘

text

---

## 3. Camadas Detalhadas

### 3.1 Camada 1 — Coleta

**Responsabilidade:** obter, processar e filtrar tickets do Help360.

**Stack:** Python + Selenium + Pandas + openpyxl

| Programa | Entrada | Saída | Tipo |
|---|---|---|---|
| `programa0_preprocessar.py` | Tabela fato | `tickets_com_respondido.xlsx` | Batch |
| `programa1_download.py` | Site Help360 | `tickets.xlsx` | Batch |
| `programa2_filtrar.py` | 2 arquivos Excel | `acompanhamento.xlsx` | Batch |
| `programa3_abrir.py` | `acompanhamento.xlsx` | Abas no Chrome | Interativo |

**Duração típica:** 5-15 minutos.

### 3.2 Camada 2 — Persistência e Enriquecimento

**Responsabilidade:** gravar no banco e enriquecer com dados adicionais.

**Stack:** Python + SQLite + Selenium + Pandas

| Programa | Entrada | Saída | Tipo |
|---|---|---|---|
| `programa4_persistir.py` | `tickets.xlsx` | SQLite (`tickets`) | Batch |
| `programa5_enriquecer.py` | Site + SQLite | SQLite (`movimentacoes`, `mensagens`, `backlog`) | Batch |

**Duração típica:** 5 minutos (persistir) + 30-60 min (enriquecer 100 dias).

### 3.3 Camada 3 — Análise

**Responsabilidade:** aplicar regras, gerar métricas e visualizar.

**Stack:** Python + SQLite + Pandas + Streamlit

| Script | Entrada | Saída | Tipo |
|---|---|---|---|
| `carregar_analistas.py` | `usuario_empresa.xlsx` | SQLite (`analistas`) | Batch |
| `marcar_respondidos.py` | `tickets_com_respondido.xlsx` | SQLite (`respondido`) | Batch |
| `marcar_empresa_responsavel.py` | SQLite | SQLite (`responsavel_empresa`) | Batch |
| `diagnosticar_tickets.py` | SQLite | SQLite (`diagnostico`, `acao_interna`) | Batch |
| `dashboard/app.py` | SQLite | Web app | Contínuo |

---

## 4. Componentes Arquiteturais

### 4.1 Componente de Coleta (Selenium)
┌────────────────────────────────────────┐
│ Selenium WebDriver │
│ │
│ ┌──────────────┐ ┌──────────────┐ │
│ │ Login │→ │ Navegação │ │
│ └──────────────┘ └──────┬───────┘ │
│ │ │
│ ▼ │
│ ┌──────────────┐ │
│ │ Extração │ │
│ │ (seletores) │ │
│ └──────────────┘ │
└────────────────────────────────────────┘

text

**Padrões:**
- Page Object Model (POM) — cada página é uma classe
- Esperas explícitas em vez de `sleep()`
- Retry com backoff

### 4.2 Componente de Persistência (SQLite)
┌────────────────────────────────────────┐
│ SQLite │
│ │
│ tickets.db │
│ ├── tickets (28 colunas) │
│ ├── movimentacoes │
│ ├── mensagens │
│ ├── analistas (10 colunas) │
│ ├── areas │
│ └── snapshots │
│ │
│ + Views (tempo_resposta, sla, nao_ret)│
└────────────────────────────────────────┘

text

**Padrões:**
- **Migrations** versionadas em `dados/migrations/*.sql`
- **Idempotência** — `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN` com tratamento de erro
- Índices em colunas de filtro

### 4.3 Componente de Análise
┌────────────────────────────────────────┐
│ Camada 3 — Análises │
│ │
│ ┌────────────────────────────────┐ │
│ │ Regras de Negócio │ │
│ │ ├── Classificação de empresa │ │
│ │ ├── Detecção de backlog │ │
│ │ ├── Matriz de verdade │ │
│ │ └── Tickets travados │ │
│ └────────────────────────────────┘ │
│ │
│ ┌────────────────────────────────┐ │
│ │ Métricas │ │
│ │ ├── Tempo de resposta │ │
│ │ ├── SLA │ │
│ │ ├── Produtividade │ │
│ │ └── Roteamento │ │
│ └────────────────────────────────┘ │
└────────────────────────────────────────┘

text

### 4.4 Componente de Visualização (Streamlit)
dashboard/
├── app.py # Entrada
├── config.py # Constantes
├── theme.py # CSS
├── components.py # Componentes reutilizáveis
├── data.py # Carregamento
├── filters.py # Filtros sidebar
└── views/ # 8 páginas
├── visao_geral.py
├── tempo_resposta.py
├── sla.py
├── produtividade.py
├── backlog.py
├── roteamento.py
├── reincidencia.py
└── diagnostico.py

text

**Padrões:**
- **Modularização** — uma página por arquivo
- **Cache** com `@st.cache_data(ttl=300)`
- **Componentes HTML** customizados (kpi, hbar_list, callout)
- **Sem CSS inline** — tudo em `theme.py`

---

## 5. Fluxos Detalhados

### 5.1 Fluxo de Coleta (Camada 1)
Operador atualiza Tabela fato
↓

Programa0 lê Tabela fato
→ gera tickets_com_respondido.xlsx
↓

Programa1 faz login
→ baixa tickets.xlsx
↓

Programa2 cruza os dois
→ gera acompanhamento.xlsx
↓

Programa3 abre tickets no Chrome

text

### 5.2 Fluxo de Análise (Camadas 2 e 3)
Programa4 lê tickets.xlsx
→ persiste em SQLite
↓

Programa5 para cada ticket novo:
→ abre ticket no Chrome
→ raspa detalhes + backlog
→ baixa histórico Excel
→ extrai mensagens HTML
→ persiste em movimentacoes/mensagens
↓

Carregar_analistas
→ popula tabela analistas
↓

Marcar_respondidos
→ preenche respondido
↓

Marcar_empresa_responsavel
→ preenche responsavel_empresa
↓

Diagnosticar_tickets
→ aplica matriz de verdade
→ preenche diagnostico, acao_interna, pendente_usuario
↓

Dashboard
→ visualização

text

---

## 6. Padrões Arquiteturais Adotados

| Padrão | Onde | Motivo |
|---|---|---|
| **Pipeline** | Toda a Camada 1 | Processamento em etapas |
| **Layered** | 3 camadas | Separação de responsabilidades |
| **Repository** | SQLite | Isolar persistência |
| **Page Object Model** | Selenium | Manutenibilidade |
| **Idempotência** | Migrations + scripts | Rodar 2x não quebra |
| **Config externalizada** | `settings.yaml` | Não hardcodar |
| **Modularização** | Dashboard | Fácil manutenção |
| **Cache** | Streamlit | Performance |

---

## 7. Decisões Arquiteturais (ADRs)

### ADR-001 — SQLite em vez de PostgreSQL

| Campo | Valor |
|---|---|
| **Contexto** | Precisamos de banco para histórico |
| **Decisão** | SQLite (arquivo local) |
| **Motivo** | Zero configuração, volume adequado |
| **Consequências** | Sem concorrência real; migração se crescer |

### ADR-002 — Enriquecimento sob demanda

| Campo | Valor |
|---|---|
| **Contexto** | Raspar 10.000 tickets é caro |
| **Decisão** | Raspar só os que mudaram |
| **Motivo** | Reduz tempo de 33h para 40min |
| **Consequências** | Precisa controlar `enriquecido` |

### ADR-003 — Excel como transporte entre camadas

| Campo | Valor |
|---|---|
| **Contexto** | Como passar dados entre programas |
| **Decisão** | Arquivos `.xlsx` |
| **Motivo** | Compatível com fluxo manual |
| **Consequências** | Limitação de 1M linhas/aba |

### ADR-004 — Streamlit em vez de React

| Campo | Valor |
|---|---|
| **Contexto** | Precisamos de dashboard |
| **Decisão** | Streamlit (Python puro) |
| **Motivo** | Curva baixa; reuso do Pandas |
| **Consequências** | Menos customização |

### ADR-005 — Migrations em SQL puro

| Campo | Valor |
|---|---|
| **Contexto** | Schema muda ao longo do tempo |
| **Decisão** | Arquivos `.sql` versionados |
| **Alternativas** | Alembic, Flyway |
| **Motivo** | Simples; sem dependências |
| **Consequências** | Sem versionamento automático |

### ADR-006 — Dashboard modularizado

| Campo | Valor |
|---|---|
| **Contexto** | `dashboard.py` monolítico (1000+ linhas) |
| **Decisão** | 1 arquivo por página + componentes |
| **Motivo** | Colaboração e manutenibilidade |
| **Consequências** | Mais arquivos, mais imports |

### ADR-007 — Matriz de verdade em SQL/Python

| Campo | Valor |
|---|---|
| **Contexto** | 12 cenários a classificar |
| **Decisão** | Python com função `classificar()` |
| **Alternativas** | Tabela de-para em SQL |
| **Motivo** | Flexibilidade; fácil ajustar |
| **Consequências** | Não é declarativo |

---

## 8. Diagrama de Implantação
┌───────────────────────────────────────────────┐
│ Notebook/Desktop do Operador │
│ (Windows 10/11) │
│ │
│ ┌───────────────────────────────────────┐ │
│ │ Python 3.10+ │ │
│ │ │ │
│ │ ┌──────────────┐ ┌──────────────┐ │ │
│ │ │ Pipeline │ │ Dashboard │ │ │
│ │ │ (scripts) │ │ (Streamlit) │ │ │
│ │ └──────┬───────┘ └──────┬───────┘ │ │
│ │ │ │ │ │
│ │ ▼ ▼ │ │
│ │ ┌───────────────────────────────┐ │ │
│ │ │ SQLite (tickets.db) │ │ │
│ │ │ ~50 MB │ │ │
│ │ └───────────────────────────────┘ │ │
│ └───────────────────────────────────────┘ │
│ │
│ ┌───────────────┐ │
│ │ Chrome │ ← Selenium │
│ └───────────────┘ │
└───────────────────────────────────────────────┘
│
│ HTTPS
▼
┌───────────────────┐
│ Help360 (site) │
└───────────────────┘

text

---

## 9. Considerações de Escalabilidade

### 9.1 Volume Atual

| Recurso | Volume |
|---|---|
| Tickets | ~10.000 |
| Movimentações | ~3.000 |
| Mensagens | ~500 |
| Analistas | ~410 |
| Tamanho do banco | ~50 MB |

### 9.2 Limites

| Recurso | Limite | Ação |
|---|---|---|
| SQLite | ~1 TB | Migrar para Postgres |
| Streamlit | ~10 usuários | Migrar para React |
| Excel | 1M linhas/aba | Migrar para Parquet |

### 9.3 Plano de Crescimento
Fase 1-4: SQLite (atual)
Fase 5-6: SQLite (aguenta)
Fase 7+: Postgres (se > 500 MB)

text

---

## 10. Considerações de Segurança

| Aspecto | Medida |
|---|---|
| Credenciais | Variáveis de ambiente / `getpass` |
| Dados sensíveis | Anonimização antes de logs |
| Banco | Local, sem exposição em rede |
| Dashboard | Restrito ao time |
| Auditoria | Logs em `dados/logs/` |

---

## 11. Considerações de Testabilidade

| Tipo | Ferramenta | Cobertura |
|---|---|---|
| Unitário | `pytest` | Funções puras |
| Integração | `pytest` + SQLite em memória | Persistência |
| E2E | `pytest` + Selenium | Fluxo completo |
| Carga | `locust` | 10k tickets |

---

## 12. Considerações de Observabilidade

| Aspecto | Implementação |
|---|---|
| Logs | `logging` em `dados/logs/` |
| Métricas | Snapshot em `snapshots` |
| Tracing | Timestamps entre etapas |
| Alertas | Email para falhas críticas |

---

## 13. Referências

- [02_Requisitos.md](02_REQUISITOS.md)
- [04_Modelo_Dados.md](04_MODELO_DADOS.md)
- [05_Regras_de_Negocio.md](05_REGRAS_DE_NEGOCIO.md)
- [07_Interfaces.md](07_INTERFACES.md)
- [11_Roadmap.md](11_ROADMAP.md)