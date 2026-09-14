# 06 — Análises e Métricas

**Documento:** Catálogo de Análises e Métricas
**Versão:** 2.0
**Público-alvo:** Desenvolvedores, Analistas de Dados, Supervisores

---

## 1. Introdução

Este documento cataloga **todas as análises** que a Automação Help360 deve gerar,
com fórmulas, fontes de dados, visualizações e insights esperados.

### 1.1 Organização

Cada análise é apresentada no formato:

| Campo | Descrição |
|---|---|
| **Objetivo** | O que queremos descobrir |
| **Métrica** | Fórmula de cálculo |
| **Fonte** | De onde vêm os dados |
| **Frequência** | Quando é calculada |
| **Visualização** | Como é apresentada |
| **Insight** | Que decisão habilita |

### 1.2 Priorização

| Nível | Significado |
|---|---|
| 🥇 **Prioridade 1** | Crítico — alto impacto, baixa complexidade |
| 🥈 **Prioridade 2** | Importante — alto impacto, média complexidade |
| 🥉 **Prioridade 3** | Complementar — impacto moderado |
| ⏳ **Futuro** | NLP/predição — requer histórico |

---

## 2. Tempo de Resposta

### 2.1 Tempo Médio de Resolução

| Campo | Valor |
|---|---|
| **Objetivo** | Quanto tempo, em média, levamos para resolver um ticket |
| **Métrica** | `AVG(data_resolvido - criado_data)` |
| **Fonte** | `tickets` |
| **Frequência** | Diária |
| **Prioridade** | 🥇 1 |

**Variações:**
- Tempo **mediano** (P50) — mais robusto a outliers
- Tempo **P90** — pior caso realista
- Tempo **P99** — pior caso extremo

**Visualizações:**
- Histograma de distribuição
- Boxplot por categoria
- Evolução temporal (semanal)

---

### 2.2 Tempo até 1ª Resposta

| Campo | Valor |
|---|---|
| **Objetivo** | Quanto tempo até o primeiro atendimento |
| **Métrica** | `AVG(data_1_resolvido - criado_data)` |
| **Fonte** | `tickets` |
| **Prioridade** | 🥇 1 |

**Insight:** mede a **agilidade inicial** (o quão rápido o cliente é atendido).

---

### 2.3 Tempo em Fila

| Campo | Valor |
|---|---|
| **Objetivo** | Quanto tempo o ticket fica esperando antes de ser pego |
| **Métrica** | `data_1_resolvido - criado_data` (antes de qualquer ação) |
| **Fonte** | `tickets`, `mensagens` |
| **Prioridade** | 🥈 2 |

---

## 3. SLA (Service Level Agreement)

### 3.1 % de SLA Cumprido

| Campo | Valor |
|---|---|
| **Objetivo** | Estamos cumprindo os prazos acordados? |
| **Métrica** | `COUNT(resolvido <= previsao) / COUNT(*) * 100` |
| **Fonte** | `tickets` |
| **Frequência** | Diária |
| **Prioridade** | 🥇 1 |

**Variações:**
- Por categoria
- Por prioridade
- Por responsável
- Por período

**Visualizações:**
- Semáforo (verde/amarelo/vermelho)
- Evolução semanal
- Ranking por categoria

---

### 3.2 Tickets em Risco de Estouro

| Campo | Valor |
|---|---|
| **Objetivo** | Tickets que vão estourar SLA nas próximas 24h |
| **Métrica** | `previsao < hoje + 1 dia` **E** `data_resolvido IS NULL` |
| **Fonte** | `tickets` |
| **Frequência** | Diária |
| **Prioridade** | 🥇 1 |
| **Ação** | Alerta automático |

---

### 3.3 Margem Média

| Campo | Valor |
|---|---|
| **Objetivo** | Quanto "sobra" ou "falta" em média antes do prazo |
| **Métrica** | `AVG(previsao - data_resolvido)` |
| **Fonte** | `tickets` |

**Interpretação:**
- Positiva → resolvemos antes do prazo
- Negativa → estouramos SLA

---

## 4. Produtividade

### 4.1 Tickets Resolvidos por Analista

| Campo | Valor |
|---|---|
| **Objetivo** | Quem resolve mais tickets |
| **Métrica** | `COUNT(tickets WHERE responsavel_atual = X)` |
| **Fonte** | `tickets` |
| **Frequência** | Semanal |
| **Prioridade** | 🥇 1 |

**⚠️ Cuidado ético:** volume **não** é produtividade.
Tickets complexos valem mais que simples. Sempre comparar com o perfil.

---

### 4.2 Backlog Atual

| Campo | Valor |
|---|---|
| **Objetivo** | Quantos tickets estão abertos por analista |
| **Métrica** | `COUNT(status != 'Resolvido') GROUP BY responsavel_atual` |
| **Fonte** | `tickets` |

**Insight:** identificar **sobrecarga** (alguém com backlog muito maior).

---

### 4.3 Taxa de Reabertura

| Campo | Valor |
|---|---|
| **Objetivo** | % de tickets que voltaram após resolvidos |
| **Métrica** | `COUNT(data_resolvido != data_1_resolvido) / COUNT(*)` |
| **Fonte** | `tickets` |

**Insight:** indica **qualidade** da resolução.

---

## 5. Roteamento ⭐

### 5.1 % de Encaminhamentos Incorretos

| Campo | Valor |
|---|---|
| **Objetivo** | Quantos tickets foram para área errada |
| **Métrica** | `COUNT(encaminhamentos errados) / COUNT(total)` |
| **Fonte** | `mensagens` |
| **Prioridade** | 🥇 1 |

**Como detectar "errado":**
- Se o ticket **voltou** da área destino
- Se foi redirecionado para outra área antes de resolver

---

### 5.2 Número de Pulos por Ticket

| Campo | Valor |
|---|---|
| **Objetivo** | Quantas áreas o ticket passou até ser resolvido |
| **Métrica** | `COUNT(mensagens tipo='encaminhamento')` por ticket |
| **Fonte** | `mensagens` |

**Interpretação:**
- 0-1 pulos → ótimo
- 2 pulos → aceitável
- 3+ pulos → **roteamento ruim**

---

### 5.3 Caminhos Mais Comuns

| Campo | Valor |
|---|---|
| **Objetivo** | Mapear os caminhos que os tickets percorrem |
| **Métrica** | `COUNT` agrupado por `(origem, destino)` |
| **Fonte** | `mensagens` |

**Visualização:** grafo direcionado (networkx + pyvis).

**Exemplo:**
Triagem → Java → Resolvido 45 tickets (0.9 dia)
Triagem → Folha → Financeiro → Folha 23 tickets (8.2 dias) ⚠️

text

---

### 5.4 Áreas "Armadilha"

| Campo | Valor |
|---|---|
| **Objetivo** | Onde os tickets ficam presos |
| **Métrica** | Áreas com maior `AVG(tempo entre envio e próxima ação)` |
| **Fonte** | `mensagens` |

---

## 6. Gargalos (Não Retorno) ⭐

### 6.1 Tempo até 1ª Ação do Responsável

| Campo | Valor |
|---|---|
| **Objetivo** | Depois de receber o ticket, quanto tempo o analista demora para agir |
| **Métrica** | `AVG(1a_mensagem_do_analista - recebimento)` |
| **Fonte** | `mensagens` |
| **Prioridade** | 🥇 1 |

**Como calcular:**
1. Identificar quando o ticket foi atribuído a um analista
2. Identificar a primeira mensagem desse analista
3. Diferença = tempo até 1ª ação

---

### 6.2 Tickets Esquecidos

| Campo | Valor |
|---|---|
| **Objetivo** | Tickets que receberam alguém mas ninguém agiu |
| **Métrica** | `COUNT(tempo_ate_1a_acao > 2 dias)` |
| **Fonte** | `mensagens` |
| **Prioridade** | 🥇 1 |

**Ação:** alerta por email ao responsável + supervisor.

---

### 6.3 Ranking de Analistas por Gargalo

| Campo | Valor |
|---|---|
| **Objetivo** | Quem está com mais tickets "esquecidos" |
| **Métrica** | `COUNT(tickets_esquecidos) GROUP BY analista` |
| **Fonte** | `mensagens` |
| **Visualização** | Ranking (top 10) |

**⚠️ Cuidado:** não usar para punição.
Usar para **identificar sobrecarga** e redistribuir.

---

## 7. Reincidência

### 7.1 Taxa de Reincidência

| Campo | Valor |
|---|---|
| **Objetivo** | O mesmo problema está voltando? |
| **Métrica** | `COUNT(solicitantes com > 1 ticket) / COUNT(distintos)` |
| **Fonte** | `tickets` |
| **Prioridade** | 🥈 2 |

---

### 7.2 Top 10 Solicitantes

| Campo | Valor |
|---|---|
| **Objetivo** | Quem abre mais tickets |
| **Métrica** | `COUNT(*) GROUP BY solicitante ORDER BY DESC LIMIT 10` |
| **Fonte** | `tickets` |

**Insight:** pode indicar problema **sistêmico** (não é o usuário, é o processo).

---

## 8. Backlog e Tendências

### 8.1 Backlog Total

| Campo | Valor |
|---|---|
| **Métrica** | `COUNT(status NOT IN ('Resolvido', 'Fechado'))` |
| **Frequência** | Diária |

---

### 8.2 Aging Médio

| Campo | Valor |
|---|---|
| **Objetivo** | Idade média dos tickets abertos |
| **Métrica** | `AVG(hoje - criado_data) WHERE status != Resolvido` |
| **Fonte** | `tickets` |

**Interpretação:**
- Aging baixo → estamos dando conta
- Aging alto → backlog antigo acumulando

---

### 8.3 Taxa Entrada vs. Saída

| Campo | Valor |
|---|---|
| **Métrica** | `novos_hoje / resolvidos_hoje` |

**Interpretação:**
- > 1 → backlog crescendo ⚠️
- = 1 → estável
- < 1 → estamos reduzindo ✅

---

### 8.4 Projeção de Fechamento

| Campo | Valor |
|---|---|
| **Métrica** | `backlog_atual / média_resolvidos_por_dia` |
| **Resultado** | Dias estimados para zerar backlog |

---

## 9. Sazonalidade

### 9.1 Volume por Dia da Semana

| Campo | Valor |
|---|---|
| **Métrica** | `COUNT(*) GROUP BY dia_semana` |
| **Fonte** | `tickets` |

**Insight:** identifica padrões (ex: "segundas têm 40% mais tickets").

---

### 9.2 Volume por Hora

| Campo | Valor |
|---|---|
| **Métrica** | `COUNT(*) GROUP BY HOUR(criado_data)` |

**Insight:** dimensionar equipe por turno.

---

### 9.3 Comparativo YoY

| Campo | Valor |
|---|---|
| **Métrica** | Volume mensal atual vs. mesmo mês do ano passado |

---

## 10. NLP (Processamento de Linguagem Natural)

### 10.1 Classificação Automática de Rotas ⏳

| Campo | Valor |
|---|---|
| **Objetivo** | Dado título + descrição, sugerir área correta |
| **Técnica** | TF-IDF + Logistic Regression (v1) ou BERTimbau (v2) |
| **Prioridade** | ⏳ Futuro |

**Treinamento:** tickets resolvidos → área final que resolveu.

**Impacto esperado:** redução de 40-60% nos pulos.

---

### 10.2 Detecção de Urgência ⏳

| Campo | Valor |
|---|---|
| **Objetivo** | Sinalizar tickets urgentes mesmo sem prioridade alta |
| **Técnica** | Palavras-chave + sentimento |

**Palavras-gatilho:**
- "urgente", "prazo", "hoje"
- "judicial", "prazo legal"
- Sentimento negativo extremo

---

### 10.3 Detecção de Duplicatas ⏳

| Campo | Valor |
|---|---|
| **Objetivo** | Identificar tickets similares antes da abertura |
| **Técnica** | Similaridade de cosseno entre descrições |

---

### 10.4 Sumarização ⏳

| Campo | Valor |
|---|---|
| **Objetivo** | Gerar resumo de tickets com histórico longo |
| **Técnica** | LLM (via API) |

---

## 11. Alertas Automáticos

| # | Alerta | Condição | Canal | Prioridade |
|---|---|---|---|---|
| A1 | SLA em risco | `previsao < hoje + 1d` | Email | 🥇 |
| A2 | SLA estourado | `data_resolvido > previsao` | Email | 🥇 |
| A3 | Ticket parado | `hoje - alterado_data > 7d` | Email | 🥇 |
| A4 | Analista sem retorno | `recebido > 3d sem ação` | Email | 🥇 |
| A5 | Volume anormal | `hoje > média + 2σ` | Email | 🥈 |
| A6 | Backlog crescendo | `novos > resolvidos` por 3d | Email | 🥈 |
| A7 | Reincidência | 3+ tickets mesmo CPF em 30d | Email | 🥉 |

---

## 12. Matriz de Priorização

| Análise | Impacto | Esforço | Prioridade |
|---|---|---|---|
| Tempo de resposta | Alto | Baixo | 🥇 |
| SLA | Alto | Baixo | 🥇 |
| Gargalos (não retorno) | Alto | Médio | 🥇 |
| Roteamento | Alto | Médio | 🥇 |
| Produtividade | Médio | Baixo | 🥈 |
| Backlog | Médio | Baixo | 🥈 |
| Reincidência | Médio | Médio | 🥉 |
| Sazonalidade | Baixo | Baixo | 🥉 |
| NLP | Alto | Alto | ⏳ |

---

## 13. Roadmap de Implementação

| Fase | Análises entregues |
|---|---|
| **Fase 3** | Tempo de resposta, SLA, Produtividade, Gargalos |
| **Fase 4** | Roteamento, Backlog, Reincidência, Sazonalidade |
| **Fase 5** | Alertas automáticos |
| **Fase 6** | NLP e predição |

---

## 14. Referências

- [04_Modelo_Dados.md](04_MODELO_DADOS.md)
- [05_Regras_de_Negocio.md](05_REGRAS_DE_NEGOCIO.md)
- [07_Interfaces.md](07_INTERFACES.md)
"""

---