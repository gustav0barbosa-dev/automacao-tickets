# 11 — Roadmap

**Documento:** Roadmap de Evolução
**Versão:** 2.0
**Público-alvo:** Todos os envolvidos

---

## 1. Visão Geral

O projeto evolui em **8 fases incrementais**, cada uma entregando valor concreto:
Fase 0 ─ Fase 1 ─ Fase 2 ─ Fase 3 ─ Fase 4 ─ Fase 5 ─ Fase 6 ─ Fase 7
Fundação Persist. Enriq. Análises Roteam. Alertas Dashboard NLP
✅ 📋 📋 📋 📋 📋 📋 📋

text

---

## 2. Fase 0 — Fundação ✅ (concluída)

**Objetivo:** Pipeline funcionando do zero.

**Entregas:**
- Pipeline coleta + filtragem + abertura
- Estrutura de pastas organizada
- Versionamento com Git
- Documentação inicial

**Marco:** `python main.py` roda sem erros.

---

## 3. Fase 1 — Persistência

**Duração estimada:** 1 mês
**Prioridade:** 🥇 Crítica

### Entregas

- [ ] Modelo de dados SQLite implementado
- [ ] Script `programa4_persistir.py`
- [ ] Tabelas: `tickets`, `movimentacoes`, `snapshots`
- [ ] Backup automático do banco

### Marco

**Métrica de sucesso:** banco com **30 dias de histórico** (~1.500 tickets).

### Pré-requisitos

- Pipeline atual funcionando
- Banco SQLite instalado (nativo)

---

## 4. Fase 2 — Enriquecimento

**Duração estimada:** 1 mês
**Prioridade:** 🥇 Crítica
**Depende de:** Fase 1

### Entregas

- [ ] Script `programa5_enriquecer.py`
- [ ] Scraper de descrição + área de mensagens
- [ ] Lógica de "raspar só o que mudou"
- [ ] Tabelas: `mensagens`, `analistas`, `areas`

### Marco

**Métrica de sucesso:** 90% dos tickets alterados enriquecidos.

### Riscos

- Site do Help360 pode mudar HTML
- Scraping pode ser bloqueado

---

## 5. Fase 3 — Análises Básicas

**Duração estimada:** 1 mês
**Prioridade:** 🥇 Crítica
**Depende de:** Fases 1 e 2

### Entregas

- [ ] Script `programa6_analises.py`
- [ ] Análise de **tempo de resposta**
- [ ] Análise de **SLA**
- [ ] Análise de **produtividade**
- [ ] Análise de **gargalos (não retorno)** ⭐
- [ ] Exportação para Excel

### Marco

**Métrica de sucesso:** primeiro relatório semanal validado pela chefia.

### Impacto esperado

Redução de 30% no tempo médio de resolução.

---

## 6. Fase 4 — Análises Avançadas

**Duração estimada:** 1 mês
**Prioridade:** 🥈 Importante
**Depende de:** Fase 3

### Entregas

- [ ] Grafo de roteamento (networkx + pyvis)
- [ ] Análise de reincidência
- [ ] Sazonalidade
- [ ] Comparativo temporal
- [ ] Relatórios em PDF

### Marco

**Métrica de sucesso:** 5+ caminhos problemáticos identificados.

### Impacto esperado

Redução de 40% nos pulos de tickets.

---

## 7. Fase 5 — Alertas

**Duração estimada:** 1 mês
**Prioridade:** 🥈 Importante
**Depende de:** Fase 3

### Entregas

- [ ] Script `programa7_alertas.py`
- [ ] Regras configuráveis em YAML
- [ ] Envio por email (`smtplib`)
- [ ] Webhook para Teams (opcional)

### Regras de alerta

| Alerta | Condição |
|---|---|
| SLA em risco | `previsao < hoje + 1d` |
| Ticket parado | `hoje - alterado > 7d` |
| Analista sem retorno | `recebido > 3d sem ação` |
| Volume anormal | `hoje > média + 2σ` |

### Marco

**Métrica de sucesso:** 3+ alertas ativos em produção.

---

## 8. Fase 6 — Dashboard

**Duração estimada:** 1 mês
**Prioridade:** 🥈 Importante
**Depende de:** Fases 3, 4, 5

### Entregas

- [ ] `dashboard.py` com Streamlit
- [ ] KPIs no topo (tempo, SLA, backlog)
- [ ] Gráficos interativos
- [ ] Filtros (período, área, analista)
- [ ] Tabela detalhada

### Marco

**Métrica de sucesso:** equipe usa diariamente.

### Stack

- Streamlit
- Plotly
- SQLite (leitura)

---

## 9. Fase 7 — NLP e Predição

**Duração estimada:** 2+ meses
**Prioridade:** 🥉 Complementar
**Depende de:** Fases 2, 3

### Entregas

- [ ] Classificador de rotas (TF-IDF + LR)
- [ ] Detecção de urgência
- [ ] Sumarização automática
- [ ] Detecção de duplicatas
- [ ] Previsão de volume (séries temporais)

### Marco

**Métrica de sucesso:** sugestão de rota com > 80% de acerto.

### Impacto esperado

Redução de 60% nos pulos desnecessários.

---

## 10. Fase 8 — Refinamentos Contínuos

**Duração:** contínua

### Itens

- [ ] Migração para PostgreSQL (se volume crescer)
- [ ] Autenticação no dashboard
- [ ] CI/CD com GitHub Actions
- [ ] Testes automatizados (cobertura > 60%)
- [ ] Integração com Teams
- [ ] Treinamento da equipe

---

## 11. Cronograma Consolidado

| Mês | Fase | Marco principal |
|---|---|---|
| Mês 0 | Fase 0 | Pipeline funciona ✅ |
| Mês 1 | Fase 1 | 30 dias de histórico no banco |
| Mês 2 | Fase 2 | 90% dos tickets enriquecidos |
| Mês 3 | Fase 3 | Primeiro relatório |
| Mês 4 | Fase 4 | Análise de roteamento |
| Mês 5 | Fase 5 | Alertas automáticos |
| Mês 6 | Fase 6 | Dashboard em produção |
| Mês 7+ | Fase 7 | NLP funcionando |

---

## 12. Matriz de Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Site do Help360 mudar | Alta | Alto | Seletores robustos + fallback |
| Baixa adesão da equipe | Média | Alto | Envolver chefia desde o início |
| Vazamento de dados (LGPD) | Média | Alto | Anonimização + controle de acesso |
| Dependência de uma pessoa | Alta | Alto | Documentação + treinamento |
| Volume crescer além do esperado | Baixa | Médio | Migrar para PostgreSQL |
| Selenium quebrar em produção | Média | Alto | Testes E2E + monitoramento |

---

## 13. Métricas de Sucesso do Projeto

| Métrica | Baseline | Meta (6 meses) |
|---|---|---|
| Tempo de abertura de tickets | 2h/dia manual | 5 min (automático) |
| % SLA cumprido | Não medido | > 95% |
| Tempo médio de resolução | Não medido | Reduzir 30% |
| Pulos por ticket | Não medido | Reduzir 40% |
| Tickets esquecidos (>3d) | Não medido | Zero |
| Cobertura de análise | 0% | 100% dos tickets |

---

## 14. Cronograma Detalhado — Fase 1

**Semana 1:**
- [ ] Criar `schema.sql`
- [ ] Criar `programa4_persistir.py`
- [ ] Testar com dados de homologação

**Semana 2:**
- [ ] Rodar diariamente
- [ ] Validar integridade dos dados
- [ ] Corrigir bugs

**Semana 3:**
- [ ] Implementar backup automático
- [ ] Documentar uso
- [ ] Coletar feedback

**Semana 4:**
- [ ] Consolidar aprendizados
- [ ] Planejar Fase 2

---

## 15. Referências

- [02_Requisitos.md](02_REQUISITOS.md)
- [03_Arquitetura.md](03_ARQUITETURA.md)
- [06_Analises_e_Metricas.md](06_ANALISES_E_METRICAS.md)
"""


---