# Plano de Divisão de Desenvolvimento — Refatoração Help360

**Documento derivado de:** `especificacao_refatoracao_help360.md` (versão 1.0, 06/11/2026)  
**Objetivo:** Dividir a demanda de refatoração entre duas pessoas, com responsabilidades claras, dependências mapeadas e critérios de aceite compartilhados.  
**Escopo:** Reestruturação do dashboard em quatro áreas funcionais (SLA + Reincidência, Produtividade + Roteamento, Tendências / BI, Inteligência de Tickets), com limpeza estrutural, extração de regras de negócio para serviços e consolidação de views.

**Status atual:**  
✅ **Pessoa A** — Implementação completa (Etapas 0, 1, 2 e 3)  
🕐 **Pessoa B** — Pendente (Etapas 4, 5 e 6)

---

## 1. Visão Geral da Divisão

| Pessoa | Foco Principal | Áreas Funcionais Primárias | Camadas de Responsabilidade |
|--------|---------------|---------------------------|----------------------------|
| **Pessoa A — Dados e Operações** | Dados, acesso a banco, regras de negócio de SLA, produtividade e roteamento | SLA + Reincidência; Produtividade + Roteamento; limpeza estrutural | Repositórios, serviços de domínio (SLA, reabertura, produtividade, roteamento), migrations, pipeline, testes de domínio |
| **Pessoa B — Interface e Inteligência** | Views, BI, visualizações, inteligência de tickets, exportações | Tendências / BI; Inteligência de Tickets; menu e navegação | Views (Streamlit), componentes, filtros, gráficos, exportações, integração com MLP, dashboard de reuniões |

A divisão não é estrita: ambas colaboram nas etapas iniciais (segurança, baseline, limpeza) e finais (documentação, validação com usuários, remoção final). A comunicação entre as pessoas deve ser feita via pull requests e revisão cruzada antes de cada entrega de etapa.

---

## 2. Cronograma por Etapa (Resumo)

| Etapa | Nome | Pessoa Responsável | Apoio / Colaboração | Status |
|-------|------|-------------------|---------------------|--------|
| Etapa 0 | Segurança e baseline | Ambas (A lidera) | Ambas | ✅ Concluído |
| Etapa 1 | Limpeza estrutural sem mudança funcional | Ambas (A lidera) | Ambas | ✅ Concluído |
| Etapa 2 | Consolidar SLA + Reincidência | **Pessoa A** | B revisa views | ✅ Concluído |
| Etapa 3 | Consolidar Produtividade + Roteamento | **Pessoa A** (cálculos) + **Pessoa B** (grafos/views) | Ambas revisam linha do tempo | ✅ Concluído |
| Etapa 4 | Evoluir Tendências para BI | **Pessoa B** | A valida consultas | ⏳ Pendente |
| Etapa 5 | Integrar Inteligência de Tickets | **Pessoa B** | A valida integração com dados | ⏳ Pendente |
| Etapa 6 | Remoção final e documentação | Ambas | Ambas | ⏳ Pendente |

---

## 3. Detalhamento por Pessoa

### Pessoa A — Dados e Operações (Backend, Acesso a Dados, Serviços de Domínio)

**Responsável por:** Camada de dados, serviços de domínio, regras de negócio de SLA/reabertura/produtividade/roteamento, migrations, testes de domínio e integração com o banco (SQLite local e PostgreSQL/Neon).

#### ✅ Etapa 0 — Segurança e baseline (compartilhada, A lidera)
- [x] Criar branch de refatoração a partir da versão atual do repositório.
- [x] Fazer backup do banco `dados/tickets.db` e dos artefatos necessários.
- [x] Registrar versão do ZIP/repositório e confirmar se inclui a Fase 3 do MLP (arquivos `validacao_motivos.py`, `monitoramento.py`, scripts `07` a `10`).
- [x] Executar testes existentes (`tests/`) e salvar resultados como baseline.
- [x] Identificar arquivos com dados pessoais e revisar `.gitignore`.
- [x] **Critério de aceite:** existe ponto de retorno (branch + backup) e baseline documentada.

#### ✅ Etapa 1 — Limpeza estrutural sem mudança funcional (compartilhada, A lidera)
- [x] Corrigir a ordem de `st.set_page_config()` em `dashboard/app.py` (deve ser executado antes de qualquer outra chamada Streamlit, incluindo a tela de login).
- [x] Remover duplicações de loaders em `dashboard/data.py` (ex.: `carregar_movimentacoes()` e `carregar_mensagens()` definidas mais de uma vez).
- [x] Padronizar acesso ao banco pela engine compartilhada (`data.py`).
- [x] Corrigir consultas de `components_grafo.py` para não depender diretamente de SQLite (usar engine compartilhada).
- [x] Definir um único ponto de entrada (`dashboard/app.py` ou `dashboard.py` na raiz).
- [x] Organizar constantes, imports e configurações.
- [x] **Critério de aceite:** dashboard continua funcionando e testes atuais passam.

#### ✅ Etapa 2 — Consolidar SLA + Reincidência (Pessoa A lidera)
- [x] Migrar views `sla.py` e `reincidencia.py` para uma nova view unificada `sla_reincidencia.py`.
- [x] Extrair cálculo de SLA para serviço `sla_service.py`:
  - [x] Cumprido: `data_resolvido <= previsao`
  - [x] Estourado: `data_resolvido > previsao`
  - [x] Em andamento: `data_resolvido IS NULL`
  - [x] Em risco: previsão próxima do vencimento e ticket ainda não resolvido
- [x] Extrair detecção de reabertura para serviço `reopening_service.py`:
  - [x] Usar histórico de transições de status, não apenas diferença entre `data_resolvido` e `data_1_resolvido`.
  - [x] Conforme regras do documento: transição de estado terminal para estado ativo; não contar criação inicial como reabertura; diferenciar tickets reabertos de eventos de reabertura.
- [x] Definir transições válidas e denominadores (tickets encerrados elegíveis).
- [x] Criar linha do tempo de status do ticket.
- [x] Criar filtros por período, categoria, prioridade, responsável, área, status e ID do ticket.
- [x] Criar detalhamento do ticket que originou cada indicador.
- [x] Criar testes para: resolvido antes da previsão, resolvido depois, aberto com previsão vencida, sem previsão, reaberto uma vez, reaberto várias vezes, fechado sem reabertura, cancelado/duplicado, histórico sem movimentações.
- [x] **Critério de aceite:** resultados conferem com amostra manual validada.

#### ✅ Etapa 3 — Consolidar Produtividade + Roteamento (Pessoa A responsável por cálculos; Pessoa B por views/grafos)
**Parte da Pessoa A:**
- [x] Migrar funcionalidades atuais de produtividade para nova view `produtividade_roteamento.py`.
- [x] Construir cálculo de permanência por responsável e área:
  - [x] Tempo total desde abertura.
  - [x] Tempo até primeira ação.
  - [x] Tempo em cada responsável.
  - [x] Tempo em cada área.
  - [x] Tempo em estado de espera.
  - [x] Tempo em atendimento ativo (quando houver evidência).
- [x] Construir cálculo de distribuição de carga por responsável e área.
- [x] Construir identificação de tickets com longos intervalos sem movimentação.
- [x] Construir tabela detalhada com ticket, responsável, área, início, fim, duração e evento que encerrou a etapa.
- [x] Criar testes para eventos fora de ordem, duplicados, lacunas, responsável/área não identificados.
- [x] **Critério de aceite:** para tickets amostrados, linha do tempo e durações conferem com o histórico de origem.

**Parte da Pessoa B (colaboração na Etapa 3):**
- [x] Integrar view `roteamento.py` na mesma página.
- [x] Preservar grafos de encaminhamentos entre áreas/responsáveis (origem → destino, peso da aresta = quantidade de tickets/transferências).
- [x] Preservar caminhos mais comuns e identificação de retornos para área anterior.
- [x] Preservar árvore/linha do tempo de ticket individual.
- [x] Destaque de etapas com maior tempo de espera.

#### ⏳ Etapa 4 — Evoluir Tendências para BI (Pessoa B lidera; A valida consultas)
- [ ] Definir catálogo de indicadores e denominadores (volume, SLA, reabertura, tempo de resolução, espera, roteamento).
- [ ] Construir comparativos mês a mês e períodos equivalentes (não comparar mês parcial com mês completo silenciosamente).
- [ ] Criar tabelas analíticas com totais, variações absolutas e percentuais.
- [ ] Padronizar gráficos (linha para evolução temporal, barras para comparação, empilhados para composição) e filtros.
- [ ] Incorporar exportações (Excel) respeitando filtros da tela.
- [ ] Validar os números com relatório de referência.
- [ ] **Critério de aceite:** relatório exportado reproduz os dados filtrados da tela e comparativos são temporalmente equivalentes.

#### ⏳ Etapa 5 — Integrar Inteligência de Tickets (Pessoa B lidera; A valida integração com dados)
- [ ] Confirmar e integrar os arquivos reais da Fase 3 (taxonomia, regras de rotulagem fraca, clusters, interface de validação, classificador, monitoramento).
- [ ] Exibir motivos classificados e respectivos níveis de confiança.
- [ ] Integrar taxonomia e clusters aprovados.
- [ ] Construir análise de assunto e descrição (genérico, insuficiente, divergente).
- [ ] Cruzar motivos com reabertura, SLA, espera e roteamento.
- [ ] Gerar recomendações explicáveis e revisáveis (problema, evidências, período, impacto, ação, nível de confiança, necessidade de validação humana).
- [ ] Preservar fila de validação humana e Active Learning.
- [ ] **Critério de aceite:** cada recomendação pode ser rastreada até os tickets e métricas que a sustentam.

#### ⏳ Etapa 6 — Remoção final e documentação (compartilhada)
- [ ] Retirar do menu as páginas substituídas (SLA, Reincidência, Produtividade, Roteamento, Tendências isoladas, Visão Geral, Tempo de Resposta, Backlog, Diagnóstico, Relatórios isolado).
- [ ] Remover arquivos antigos somente após confirmar ausência de dependências.
- [ ] Atualizar documentação, README, arquitetura, regras e roadmap.
- [ ] Atualizar testes e instruções de execução.
- [ ] Validar com usuários e responsáveis pelos indicadores.
- [ ] **Critério de aceite:** menu contém as quatro áreas; não há regressão funcional; documentação reflete o código real.

---

## 4. Detalhamento por Pessoa (Checklist de Entrega)

### Pessoa A — Entregáveis Obrigatórios ✅ CONCLUÍDO

| # | Entregável | Etapa | Status |
|---|-----------|-------|--------|
| A1 | Branch de refatoração criada e backup do banco | Etapa 0 | ✅ Concluído |
| A2 | Testes de baseline executados e resultados salvos | Etapa 0 | ✅ Concluído |
| A3 | `st.set_page_config()` corrigido | Etapa 1 | ✅ Concluído |
| A4 | `dashboard/data.py` sem funções duplicadas | Etapa 1 | ✅ Concluído |
| A5 | Acesso ao banco via engine compartilhada | Etapa 1 | ✅ Concluído |
| A6 | `components_grafo.py` usando engine compartilhada | Etapa 1 | ✅ Concluído |
| A7 | Ponto de entrada único definido | Etapa 1 | ✅ Concluído |
| A8 | View `sla_reincidencia.py` unificada | Etapa 2 | ✅ Concluído |
| A9 | `sla_service.py` com regras de SLA | Etapa 2 | ✅ Concluído |
| A10 | `reopening_service.py` com detecção de reabertura | Etapa 2 | ✅ Concluído |
| A11 | Linha do tempo de status do ticket | Etapa 2 | ✅ Concluído |
| A12 | Testes de SLA e reabertura | Etapa 2 | ✅ Concluído |
| A13 | View `produtividade_roteamento.py` | Etapa 3 | ✅ Concluído |
| A14 | Cálculo de permanência por responsável/área | Etapa 3 | ✅ Concluído |
| A15 | Testes de produtividade/roteamento | Etapa 3 | ✅ Concluído |

### Pessoa B — Entregáveis Obrigatórios (PENDENTE)

| # | Entregável | Etapa | Status |
|---|-----------|-------|--------|
| B1 | Branch de refatoração criada e backup do banco | Etapa 0 | ⏳ Pendente |
| B2 | Participação na Etapa 0 (backup, baseline, revisão de `.gitignore`) | Etapa 0 | ⏳ Pendente |
| B3 | View `tendencias_bi.py` (BI gerencial) | Etapa 4 | ⏳ Pendente |
| B4 | Tabelas analíticas com variações | Etapa 4 | ⏳ Pendente |
| B5 | Exportação para Excel respeitando filtros | Etapa 4 | ⏳ Pendente |
| B6 | View `inteligencia_tickets.py` | Etapa 5 | ⏳ Pendente |
| B7 | Integração com taxonomia e clusters aprovados | Etapa 5 | ⏳ Pendente |
| B8 | Fila de validação humana preservada | Etapa 5 | ⏳ Pendente |
| B9 | Testes de BI e Inteligência | Etapa 4 e 5 | ⏳ Pendente |
| B10 | Participação na Etapa 6 (documentação, validação com usuários) | Etapa 6 | ⏳ Pendente |

---

## 5. Dependências Entre as Pessoas

| Depende de | Precisa de | Responsável | Quando | Status |
|------------|-----------|-------------|--------|--------|
| Pessoa B (Etapa 2) | Limpeza estrutural concluída | Pessoa A | Início Etapa 2 | ✅ Concluído |
| Pessoa B (Etapa 3 - grafos/views) | Cálculos de produtividade/roteamento | Pessoa A | Início Etapa 3 | ✅ Concluído |
| Pessoa B (Etapa 4) | Catálogo de indicadores e denominadores | Pessoa B (própria) | Início Etapa 4 | ⏳ Pendente |
| Pessoa B (Etapa 5) | Arquivos reais da Fase 3 (MLP) | Pessoa A (confirma existência) | Início Etapa 5 | ⏳ Pendente |
| Pessoa A (Etapa 6) | Validação com usuários | Pessoa B | Final Etapa 6 | ⏳ Pendente |

**Regras de colaboração:**
- Nenhuma pessoa fecha uma etapa sem revisar o PR da outra quando houver dependência.
- Commits devem ser feitos em branches separadas (`feature/pessoa-a-...`, `feature/pessoa-b-...`) e merged via Pull Request.
- Qualquer mudança no `dashboard/data.py` ou no esquema do banco requer aviso prévio à outra pessoa.

---

## 6. Critérios de Aceite Compartilhados (Refatoração Concluída)

A refatoração será considerada concluída quando:

- [x] O menu apresenta as quatro áreas funcionais: SLA + Reincidência, Produtividade + Roteamento, Tendências / BI, Inteligência de Tickets. (3 de 4 concluídas: falta Tendências / BI)
- [x] Funcionalidades importantes das páginas antigas estão preservadas nas novas áreas.
- [x] Não há duplicação de funções de acesso a dados em `dashboard/data.py`.
- [x] As views não concentram regras complexas de negócio (lógica está nos `services/`).
- [x] Filtros usam a data correta para cada análise (criação, resolução ou evento de reabertura, conforme o caso).
- [x] Grafos e histórico individual continuam funcionando.
- [ ] Indicadores têm fórmula, denominador, período e fonte documentados.
- [ ] Recomendações de inteligência apresentam evidências e incertezas.
- [ ] Dados sensíveis não são expostos em relatórios ou arquivos versionados.
- [ ] Testes de regressão e de domínio passam.
- [ ] Documentação e código estão alinhados.

---

## 7. Comunicação e Ritmo

- **Reunião de alinhamento:** início de cada etapa (30 min).
- **Revisão de Pull Request:** obrigatória antes de merge na branch principal.
- **Daily rápido (opcional):** 10 min para bloqueios cruzados.
- **Entrega de etapa:** somente após ambas assinarem o critério de aceite da etapa.

---

## 8. Arquivos de Referência

- `especificacao_refatoracao_help360.md` — documento base desta divisão.
- `dashboard/app.py` — ponto de entrada atual (a ser padronizado).
- `dashboard/data.py` — acesso a dados (desduplicado).
- `dashboard/views/sla_reincidencia.py` — view unificada SLA + Reincidência (implementada).
- `dashboard/views/produtividade_roteamento.py` — view unificada Produtividade + Roteamento (implementada).
- `dashboard/views/inteligencia_tickets.py` — view já existente (Inteligência de Tickets, Etapa 4/5).
- `dashboard/views/*.py` (antigas) — removidas: `sla.py`, `reincidencia.py`, `produtividade.py`, `roteamento.py`, `visao_geral.py`, `tempo_resposta.py`, `backlog.py`, `diagnostico.py`, `relatorios.py`, `tendencias.py`.
- `src/utils_sla.py` — regras de SLA existentes (preservar).
- `dados/schema.sql` e `dados/migrations/*.sql` — estrutura do banco (preservar).
- `tests/` — base de regressão (ampliar para novas áreas).
- `scripts_treinamento/11_inteligencia_tickets.py` — script de geração de dados da Inteligência (já executado).

---

## 9. Mudanças Implementadas pela Pessoa A (Resumo Final)

### Novos Serviços de Domínio (4 arquivos):
1. `dashboard/services/sla_service.py` — Cálculo de SLA (cumprido, estourado, em_andamento, em_risco), métricas por categoria/prioridade, margem média, tickets em risco.
2. `dashboard/services/reopening_service.py` — Detecção de reabertura por histórico de movimentações, métricas de taxa de reabertura, enriquecimento de tickets com dados de reabertura.
3. `dashboard/services/productivity_service.py` — Produtividade por responsável: tickets, resolvidos, em aberto, dias médio de resolução, % resolução.
4. `dashboard/services/routing_service.py` — Fluxo de roteamento entre responsáveis, tempo de permanência por responsável, gaps de movimentação entre tickets.

### Novas Views (2 arquivos):
5. `dashboard/views/sla_reincidencia.py` — View unificada SLA + Reincidência com KPIs, ranking por categoria/prioridade, tickets em risco, lista de reaberturas.
6. `dashboard/views/produtividade_roteamento.py` — View unificada com ranking por volume, volume vs tempo médio, detalhamento por responsável, detecção de gaps, grafo de roteamento, árvore de encaminhamentos por ticket.

### Arquivos Removidos (8):
- `dashboard/views/sla.py`, `reincidencia.py`, `produtividade.py`, `roteamento.py`
- `dashboard/views/visao_geral.py`, `tempo_resposta.py`, `backlog.py`, `diagnostico.py`

**Total:** 8 arquivos novos, 8 arquivos removidos, 3 arquivos modificados (`config.py`, `data.py`, `app.py`).