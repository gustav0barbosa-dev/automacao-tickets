# ============================================================
# gerar_02_requisitos.py
# ============================================================

from scripts.docs._base import escrever, rodar_sozinho


CONTEUDO = """# 02 — Requisitos

**Documento:** Especificação de Requisitos (SRS)
**Versão:** 2.0
**Público-alvo:** Desenvolvedores, QA, Product Owner

---

## 1. Introdução

Este documento especifica os **requisitos funcionais (RF)** e **não funcionais (RNF)**
do sistema Automação Help360, seguindo o padrão IEEE 830.

### 1.1 Convenções

| Sigla | Significado |
|---|---|
| **RF** | Requisito Funcional |
| **RNF** | Requisito Não Funcional |
| **UC** | Caso de Uso |
| **Prioridade** | 🔴 Essencial / 🟡 Importante / 🟢 Desejável |

### 1.2 Rastreabilidade

Cada requisito tem um **ID único** (ex: `RF-001`) e é rastreado em:
- **Origem:** stakeholder ou documento que originou
- **Status:** planejado / em desenvolvimento / implementado
- **Fase do roadmap:** qual fase entrega

---

## 2. Requisitos Funcionais

### 2.1 Módulo de Coleta (Fase 1)

#### RF-001 — Download da base de tickets 🔴

**Descrição:** O sistema deve baixar a base completa de tickets do Help360 via Selenium.

**Detalhes:**
- Autenticação com credenciais @sp.gov.br
- Navegação até a área de tickets
- Acionamento do botão de exportação
- Salvamento em `~/Downloads/tickets.xlsx`

**Entrada:** credenciais + acesso ao site
**Saída:** arquivo Excel com ~5 anos de tickets
**Frequência:** diária (ou sob demanda)

---

#### RF-002 — Processamento da Tabela Fato 🔴

**Descrição:** O sistema deve ler a planilha `Tickets - Tabela fato.xlsx` (diário
manual de respostas) e gerar `tickets_com_respondido.xlsx`.

**Detalhes:**
- Ler abas `Status` e `Acompanhamento`
- Para cada ticket, extrair a **data mais recente** encontrada nas células
- Ignorar valores `0`, `-`, `#N/A`, `NaN`, vazio
- Converter formatos: `DD/MM/AAAA`, `DD/MM/AAAA HH:MM`, `DD/MM`

**Saída:** `~/Downloads/tickets_com_respondido.xlsx` (colunas `ID` e `Data Respondido`)

---

#### RF-003 — Filtragem inteligente de tickets 🔴

**Descrição:** O sistema deve cruzar `tickets.xlsx` com `tickets_com_respondido.xlsx`
e gerar `acompanhamento.xlsx` com apenas os tickets que precisam de ação.

**Detalhes:** ver [05_Regras_de_Negocio.md](05_REGRAS_DE_NEGOCIO.md)

**Saída:** `~/Downloads/acompanhamento.xlsx`

---

#### RF-004 — Abertura automática em navegador 🔴

**Descrição:** O sistema deve abrir cada ticket do `acompanhamento.xlsx` em uma
aba do Chrome.

**Detalhes:**
- URL: `https://spprev.help360.com.br/tickets/{ID}`
- Agrupamento por status
- Delay de 1.5s entre abas

---

### 2.2 Módulo de Enriquecimento (Fase 2)

#### RF-005 — Identificação de tickets alterados 🟡

**Descrição:** O sistema deve identificar quais tickets sofreram alteração desde
o último snapshot, para evitar raspagem desnecessária.

**Regra:** `alterado_data > último_snapshot_data`

---

#### RF-006 — Scraping de descrição e mensagens 🔴

**Descrição:** O sistema deve raspar, para cada ticket que mudou:
- Título completo
- Descrição completa
- Área de mensagens (histórico de fluxo)

**Detalhes:**
- Acesso via URL individual
- Parser robusto para diferentes formatos de mensagem
- Tratamento de erros (timeout, elemento não encontrado)

---

#### RF-007 — Extração de metadados de encaminhamento 🟡

**Descrição:** A partir da área de mensagens, o sistema deve extrair:
- Data/hora
- Autor
- Área de origem
- Área de destino
- Analista de destino
- Tipo (comentário, encaminhamento, resolução)

---

### 2.3 Módulo de Persistência (Fase 1)

#### RF-008 — Persistência em banco SQLite 🔴

**Descrição:** O sistema deve gravar todos os dados coletados em banco SQLite.

**Tabelas:** ver [04_Modelo_Dados.md](04_MODELO_DADOS.md)

**Frequência:** a cada execução do pipeline

---

#### RF-009 — Controle de snapshots 🔴

**Descrição:** O sistema deve registrar cada execução do pipeline com metadados:
- Data/hora
- Tickets totais
- Tickets novos
- Tickets que mudaram
- Tempo de execução

---

### 2.4 Módulo de Análise (Fase 3)

#### RF-010 — Análise de tempo de resposta 🔴

**Descrição:** O sistema deve calcular e exibir:
- Tempo médio/mediano/P90 de resolução
- Tempo até primeira ação
- Tempo em fila
- Distribuição por categoria e responsável

**Saída:** relatório Excel + gráficos

---

#### RF-011 — Análise de SLA 🔴

**Descrição:** O sistema deve calcular:
- % de SLA cumprido
- % de SLA estourado
- Tickets em risco
- Margem média

---

#### RF-012 — Análise de produtividade 🔴

**Descrição:** O sistema deve calcular por analista:
- Tickets resolvidos/dia
- Tempo médio por ticket
- Backlog atual
- Taxa de reabertura

---

#### RF-013 — Análise de roteamento 🟡

**Descrição:** O sistema deve mapear o fluxo de tickets entre áreas e identificar:
- Caminhos mais comuns
- Encaminhamentos incorretos
- Tempo médio em filas erradas
- Áreas "armadilha"

**Saída:** grafo direcionado + relatório

---

#### RF-014 — Análise de "não retorno" 🔴

**Descrição:** O sistema deve identificar analistas que recebem tickets e demoram
a dar primeira ação.

**Métricas:**
- Tempo até 1ª ação (por analista)
- Tickets "esquecidos" (>2 dias sem ação)
- Ranking de gargalos

---

#### RF-015 — Análise de reincidência 🟢

**Descrição:** O sistema deve identificar solicitantes ou assuntos com múltiplos tickets.

---

#### RF-016 — Análise de tendências 🟢

**Descrição:** O sistema deve calcular:
- Volume por período (dia, semana, mês)
- Comparativo YoY
- Sazonalidade

---

### 2.5 Módulo de Alertas (Fase 4)

#### RF-017 — Alertas configuráveis 🟡

**Descrição:** O sistema deve permitir definir regras de alerta via arquivo YAML.

**Tipos:**
- SLA em risco
- Ticket parado
- Analista sem retorno
- Volume anormal
- Reincidência

---

#### RF-018 — Notificação por email 🟡

**Descrição:** O sistema deve enviar emails aos responsáveis quando alertas forem disparados.

---

#### RF-019 — Webhook para Teams 🟢

**Descrição:** Alternativa ao email — notificação em canal do Teams.

---

### 2.6 Módulo de Interface (Fase 5)

#### RF-020 — Dashboard web 🟡

**Descrição:** O sistema deve oferecer dashboard web com:
- KPIs no topo (total, SLA, backlog)
- Gráficos interativos
- Filtros por período, área, analista
- Tabela detalhada

**Stack:** Streamlit

---

#### RF-021 — Relatórios exportáveis 🟡

**Descrição:** Gerar relatórios em Excel e PDF com:
- Resumo executivo
- Top 10 (por categoria, analista, etc.)
- Gráficos

---

### 2.7 Módulo de NLP (Fase 6)

#### RF-022 — Classificação automática de rotas 🟢

**Descrição:** Dado o título + descrição, sugerir a área correta.

**Técnica:** TF-IDF + Logistic Regression (v1) ou BERTimbau (v2)

---

#### RF-023 — Detecção de urgência 🟢

**Descrição:** Sinalizar tickets urgentes mesmo sem prioridade alta.

---

#### RF-024 — Detecção de duplicatas 🟢

**Descrição:** Identificar tickets similares antes da abertura.

---

## 3. Requisitos Não Funcionais

### 3.1 Desempenho

| ID | Requisito | Métrica |
|---|---|---|
| RNF-001 | Download de tickets | < 2 minutos |
| RNF-002 | Processamento da Tabela fato | < 30 segundos |
| RNF-003 | Filtragem | < 10 segundos |
| RNF-004 | Abertura de 50 tickets | < 2 minutos |
| RNF-005 | Scraping de 50 tickets | < 15 minutos |
| RNF-006 | Geração de relatório | < 30 segundos |
| RNF-007 | Dashboard (load) | < 5 segundos |

### 3.2 Confiabilidade

| ID | Requisito |
|---|---|
| RNF-008 | O sistema deve resistir a falhas de rede sem corromper dados |
| RNF-009 | Cada execução deve ser idempotente |
| RNF-010 | Se um programa falha, o pipeline para sem corromper arquivos |

### 3.3 Usabilidade

| ID | Requisito |
|---|---|
| RNF-011 | Operador novo deve rodar o pipeline em < 10 min de treinamento |
| RNF-012 | Todas as ações destrutivas devem pedir confirmação |
| RNF-013 | Logs claros e em português |

### 3.4 Segurança

| ID | Requisito |
|---|---|
| RNF-014 | Credenciais nunca devem ser hardcoded |
| RNF-015 | Senha deve ser solicitada via `getpass` ou variável de ambiente |
| RNF-016 | Dados sensíveis (CPF, email) devem ser anonimizados antes de relatórios |
| RNF-017 | O banco de dados deve ter acesso restrito |

### 3.5 Manutenibilidade

| ID | Requisito |
|---|---|
| RNF-018 | Código seguindo PEP 8 |
| RNF-019 | Cada função deve ter docstring |
| RNF-020 | Cobertura de testes > 60% |
| RNF-021 | Documentação técnica sempre atualizada |

### 3.6 Portabilidade

| ID | Requisito |
|---|---|
| RNF-022 | Rodar em Windows 10/11 |
| RNF-023 | Rodar em Python 3.10+ |
| RNF-024 | Caminhos via `expanduser`, nunca hardcoded |
| RNF-025 | Sem dependência de serviços em nuvem |

### 3.7 Escalabilidade

| ID | Requisito |
|---|---|
| RNF-026 | Suportar 50.000 tickets sem degradação |
| RNF-027 | Banco SQLite deve crescer linearmente (< 100 MB/ano) |
| RNF-028 | Pipeline deve rodar em < 30 minutos (execução completa) |

### 3.8 Conformidade

| ID | Requisito |
|---|---|
| RNF-029 | Conformidade com LGPD |
| RNF-030 | Conformidade com políticas internas SPPREV |
| RNF-031 | Auditoria completa (log de todas as ações) |

---

## 4. Casos de Uso

### UC-01 — Executar pipeline diário

| Campo | Valor |
|---|---|
| **Ator** | Operador |
| **Pré-condição** | Tabela fato atualizada |
| **Fluxo principal** | 1. Executar `python main.py`<br>2. Confirmar etapas<br>3. Digitar senha<br>4. Tratar os tickets abertos |
| **Pós-condição** | Tickets abertos no navegador, dados persistidos |
| **Requisitos** | RF-001 a RF-004, RF-008 |

### UC-02 — Consultar dashboard

| Campo | Valor |
|---|---|
| **Ator** | Supervisor |
| **Pré-condição** | Dashboard rodando |
| **Fluxo principal** | 1. Acessar `localhost:8501`<br>2. Aplicar filtros<br>3. Analisar KPIs |
| **Pós-condição** | Visão consolidada obtida |
| **Requisitos** | RF-020 |

### UC-03 — Receber alerta de SLA

| Campo | Valor |
|---|---|
| **Ator** | Analista |
| **Pré-condição** | Alertas configurados |
| **Fluxo principal** | 1. Sistema detecta SLA em risco<br>2. Envia email<br>3. Analista age |
| **Pós-condição** | SLA preservado |
| **Requisitos** | RF-017, RF-018 |

### UC-04 — Identificar gargalo

| Campo | Valor |
|---|---|
| **Ator** | Supervisor |
| **Pré-condição** | 30 dias de histórico |
| **Fluxo principal** | 1. Acessar análise de "não retorno"<br>2. Ver ranking de analistas<br>3. Redistribuir carga |
| **Pós-condição** | Gargalo mitigado |
| **Requisitos** | RF-014 |

---

## 5. Matriz de Rastreabilidade

| Requisito | Fase | UC | Status |
|---|---|---|---|
| RF-001 | 1 | UC-01 | ✅ Implementado |
| RF-002 | 1 | UC-01 | ✅ Implementado |
| RF-003 | 1 | UC-01 | ✅ Implementado |
| RF-004 | 1 | UC-01 | ✅ Implementado |
| RF-005 | 2 | — | 📋 Planejado |
| RF-006 | 2 | — | 📋 Planejado |
| RF-007 | 2 | — | 📋 Planejado |
| RF-008 | 1 | UC-01 | 📋 Planejado |
| RF-009 | 1 | — | 📋 Planejado |
| RF-010 | 3 | — | 📋 Planejado |
| RF-011 | 3 | — | 📋 Planejado |
| RF-012 | 3 | — | 📋 Planejado |
| RF-013 | 3 | UC-04 | 📋 Planejado |
| RF-014 | 3 | UC-04 | 📋 Planejado |
| RF-015 | 3 | — | 📋 Planejado |
| RF-016 | 3 | — | 📋 Planejado |
| RF-017 | 4 | UC-03 | 📋 Planejado |
| RF-018 | 4 | UC-03 | 📋 Planejado |
| RF-019 | 4 | — | 📋 Planejado |
| RF-020 | 5 | UC-02 | 📋 Planejado |
| RF-021 | 5 | — | 📋 Planejado |
| RF-022 | 6 | — | 📋 Planejado |
| RF-023 | 6 | — | 📋 Planejado |
| RF-024 | 6 | — | 📋 Planejado |

---

## 6. Referências

- [01_Visao_e_Escopo.md](01_VISAO_E_ESCOPO.md)
- [03_Arquitetura.md](03_ARQUITETURA.md)
- [05_Regras_de_Negocio.md](05_REGRAS_DE_NEGOCIO.md)
- [IEEE 830 - Software Requirements Specifications](https://standards.ieee.org/ieee/830/1222/)
"""


def gerar(forcar=False):
    return escrever('02_REQUISITOS', CONTEUDO, forcar=forcar)


if __name__ == '__main__':
    rodar_sozinho(gerar)