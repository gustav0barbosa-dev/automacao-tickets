# ============================================================
# gerar_03_arquitetura.py
# ============================================================

from scripts.docs._base import escrever, rodar_sozinho


CONTEUDO = """# 03 — Arquitetura

**Documento:** Arquitetura de Software (SDD)
**Versão:** 2.0
**Público-alvo:** Desenvolvedores, arquitetos, DevOps

---

## 1. Visão Geral

A Automação Help360 é organizada em **duas camadas independentes**, comunicando-se
via **arquivos** e **banco de dados**:

┌──────────────────────────────────────────────────────────────────┐
│ CAMADA 1 — COLETA │
│ (Selenium + Pandas → Excel) │
│ │
│ Baixa, processa, filtra e abre tickets │
└──────────────────────────────────────────────────────────────────┘
│
│ dados
▼
┌──────────────────────────────────────────────────────────────────┐
│ CAMADA 2 — ANÁLISE │
│ (SQLite + Pandas + Streamlit) │
│ │
│ Persiste, enriquece, analisa, alerta e visualiza │
└──────────────────────────────────────────────────────────────────┘

**Princípio:** cada camada é **independente**. A camada 2 pode rodar sozinha (com
dados históricos), e a camada 1 continua funcionando mesmo se a 2 falhar.

---

## 2. Diagrama de Blocos — Visão Completa

┌──────────────────────────────────────────────────────────────────────────┐
│ ENTRADAS │
│ │
│ 📄 Tabela fato.xlsx 🌐 Site Help360 👤 Operador │
│ (manual, operador) (5 anos de tickets) (credenciais) │
└───────┬──────────────────────────────┬────────────────────────────┬──────┘
│ │ │
▼ ▼ ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ PROGRAMA 0 │ │ PROGRAMA 1 │ │ PROGRAMA 2 │
│ processa │ │ Selenium │ │ 6 filtros │
│ Tabela fato │ │ download │ │ cruzamento │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
│ │ ▲
▼ ▼ │
tickets_com_respondido.xlsx tickets.xlsx │
│ │ │
└──────────────┬───────────────┘ │
│ │
└──────────────────────────────────────────┘
│
▼
acompanhamento.xlsx
│
▼
┌───────────────┐
│ PROGRAMA 3 │
│ abre no │
│ navegador │
└───────────────┘


---

## 3. Camadas Detalhadas

### 3.1 Camada 1 — Coleta

**Responsabilidade:** obter, processar e filtrar tickets do Help360.

**Stack:** Python + Selenium + Pandas + openpyxl

**Programas:**

| Programa | Entrada | Saída | Tipo |
|---|---|---|---|
| `programa0_preprocessar.py` | Tabela fato | `tickets_com_respondido.xlsx` | Batch |
| `programa1_download.py` | Site Help360 | `tickets.xlsx` | Batch |
| `programa2_filtrar.py` | 2 arquivos Excel | `acompanhamento.xlsx` | Batch |
| `programa3_abrir.py` | `acompanhamento.xlsx` | Abas no Chrome | Interativo |

### 3.2 Camada 2 — Análise

**Responsabilidade:** persistir, enriquecer, analisar e visualizar.

**Stack:** Python + SQLite + Pandas + Streamlit

| Programa | Entrada | Saída | Tipo |
|---|---|---|---|
| `programa4_persistir.py` | `acompanhamento.xlsx` | SQLite | Batch |
| `programa5_enriquecer.py` | SQLite + site | SQLite | Batch |
| `programa6_analises.py` | SQLite | Relatórios | Batch |
| `programa7_alertas.py` | SQLite | Emails | Batch |
| `dashboard.py` | SQLite | Web app | Contínuo |

---

## 4. Padrões Arquiteturais Adotados

| Padrão | Onde é aplicado | Motivo |
|---|---|---|
| **Pipeline** | Toda a camada 1 | Processamento em etapas |
| **Repository** | Acesso a SQLite | Isolar a lógica de persistência |
| **Page Object Model** | Selenium | Manutenibilidade dos seletores |
| **Idempotência** | Todos os scripts | Rodar 2x não quebra |
| **Config externalizada** | `settings.yaml` | Não hardcodar parâmetros |
| **Layered Architecture** | Camada 1 vs 2 | Separação de responsabilidades |

---

## 5. Decisões Arquiteturais (ADRs)

### ADR-001 — Uso de SQLite em vez de PostgreSQL

| Campo | Valor |
|---|---|
| **Contexto** | Precisamos de banco de dados para histórico |
| **Decisão** | Usar SQLite (arquivo local) |
| **Alternativas** | PostgreSQL, MySQL, MongoDB |
| **Motivo** | Zero configuração, portabilidade, volume adequado |
| **Consequências** | Sem acesso concorrente real; migração futura se necessário |

### ADR-002 — Enriquecimento sob demanda

| Campo | Valor |
|---|---|
| **Contexto** | Raspar 10.000 tickets é caro |
| **Decisão** | Raspar só os que mudaram desde o último snapshot |
| **Alternativas** | Raspar tudo sempre; raspar em lotes fixos |
| **Motivo** | Reduz tempo de 4h para 15min |
| **Consequências** | Precisa controlar o que já foi raspado |

### ADR-003 — Excel como transporte entre camadas

| Campo | Valor |
|---|---|
| **Contexto** | Como passar dados entre programas da camada 1 |
| **Decisão** | Arquivos `.xlsx` |
| **Alternativas** | Banco direto, JSON, Parquet |
| **Motivo** | Compatível com o fluxo manual; inspecionável |
| **Consequências** | Um pouco mais lento; limitação de 1M linhas por aba |

### ADR-004 — Streamlit em vez de React

| Campo | Valor |
|---|---|
| **Contexto** | Precisamos de dashboard web |
| **Decisão** | Streamlit (Python puro) |
| **Alternativas** | React, Vue, Dash, Power BI |
| **Motivo** | Curva de aprendizado baixa; reuso do Pandas |
| **Consequências** | Menos customização; sem autenticação robusta nativa |

### ADR-005 — Separação em camadas 1 e 2

| Campo | Valor |
|---|---|
| **Contexto** | Fluxo único ficou grande demais |
| **Decisão** | Separar em "coleta" (camada 1) e "análise" (camada 2) |
| **Alternativas** | Um monolito; microserviços |
| **Motivo** | Permite evoluir análise sem quebrar coleta |
| **Consequências** | Precisa sincronizar entre camadas |

---

## 6. Diagrama de Implantação

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


---

## 7. Referências

- [02_Requisitos.md](02_REQUISITOS.md)
- [04_Modelo_Dados.md](04_MODELO_DADOS.md)
- [05_Regras_de_Negocio.md](05_REGRAS_DE_NEGOCIO.md)
- [11_Roadmap.md](11_ROADMAP.md)
"""


def gerar(forcar=False):
    return escrever('03_ARQUITETURA', CONTEUDO, forcar=forcar)


if __name__ == '__main__':
    rodar_sozinho(gerar)