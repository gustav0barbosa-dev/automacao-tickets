# 06 — Análises e Métricas

**Documento:** Catálogo de Análises e Métricas
**Versão:** 3.0
**Última atualização:** Setembro/2026
**Público-alvo:** Desenvolvedores, Analistas de Dados, Supervisores

---

## 1. Introdução

Este documento cataloga **todas as análises** geradas pela Automação Help360, com fórmulas, fontes, visualizações e insights esperados.

### 1.1 Organização

Cada análise é apresentada em:

| Campo | Descrição |
|---|---|
| **Objetivo** | O que queremos descobrir |
| **Métrica** | Fórmula de cálculo |
| **Fonte** | De onde vêm os dados |
| **Visualização** | Como é apresentada |
| **Insight** | Que decisão habilita |

### 1.2 Priorização

| Nível | Significado |
|---|---|
| 🥇 **P1** | Crítico — alto impacto, baixa complexidade |
| 🥈 **P2** | Importante — alto impacto, média complexidade |
| 🥉 **P3** | Complementar — impacto moderado |
| ⏳ **Futuro** | NLP/predição — requer histórico |

---

## 2. Tempo de Resposta

### 2.1 Tempo Médio de Resolução 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Quanto tempo, em média, levamos para resolver um ticket |
| **Métrica** | `AVG(data_resolvido - criado_data)` |
| **Fonte** | `tickets` |
| **Frequência** | Diária |
| **Prioridade** | 🥇 P1 |

**Variações:**
- **Mediana (P50)** — robusta a outliers
- **P90** — pior caso realista
- **P99** — pior caso extremo

**Visualizações:**
- Histograma de distribuição
- Boxplot por categoria
- Evolução temporal semanal

---

### 2.2 Tempo até 1ª Resposta 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Quanto tempo até o primeiro atendimento |
| **Métrica** | `AVG(data_1_resolvido - criado_data)` |
| **Fonte** | `tickets` |

**Insight:** mede a **agilidade inicial** (o quão rápido o cliente é atendido).

---

### 2.3 Tempo em Fila 🥈

| Campo | Valor |
|---|---|
| **Objetivo** | Quanto tempo o ticket fica esperando antes de ser pego |
| **Métrica** | `data_1_resolvido - criado_data` |
| **Fonte** | `tickets`, `mensagens` |

---

## 3. SLA

### 3.1 % de SLA Cumprido 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Estamos cumprindo os prazos acordados? |
| **Métrica** | `COUNT(resolvido <= previsao) / COUNT(*) * 100` |
| **Fonte** | `tickets` |
| **Frequência** | Diária |

**Variações:** por categoria, prioridade, responsável, período.

**Visualizações:**
- Semáforo (verde/amarelo/vermelho)
- Evolução semanal
- Ranking por categoria

---

### 3.2 Tickets em Risco de Estouro 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Tickets que vão estourar SLA nas próximas 24h |
| **Métrica** | `previsao < hoje + 1 dia` **E** `data_resolvido IS NULL` |
| **Fonte** | `tickets` |
| **Ação** | Alerta automático |

---

### 3.3 SLA por Criticidade (roadmap)

| Campo | Valor |
|---|---|
| **Objetivo** | Validar se o SLA real segue a matriz de criticidade |
| **Regra** | Urgente=3d, Alta=5d, Média=10d, Baixa=15d (dias úteis) |
| **Status** | ⏳ Precisa implementar cálculo em dias úteis |

---

## 3.5 SLA por Criticidade

### 3.5.1 Definição

O SLA oficial (definido pela Atlantic + SPPREV) segue regras por criticidade:

| Criticidade | Prazo | Ação em caso de inércia |
|---|---|---|
| **Urgente** | 3 dias úteis | Fechamento automático |
| **Alta** | 5 dias úteis | Fechamento automático |
| **Média 1 e 2** | 10 dias úteis | Fechamento automático |
| **Baixa 1 e 2** | 15 dias úteis | Fechamento automático |

### 3.5.2 Regra de Cálculo

**Dias úteis** = dias entre criação e resolução, excluindo:
- Sábados e domingos
- Feriados nacionais e estaduais (SP)

**Implementação:**
python:
from utils_sla import contar_dias_uteis, adicionar_dias_uteis
from holidays import Brazil

dias_uteis = contar_dias_uteis(criado_data, data_resolvido)
previsao_ideal = adicionar_dias_uteis(criado_data, prazo_criticidade)
### 3.5.3 Colunas do Banco
Adicionadas via script scripts/analisar_sla_criticidade.py:

Coluna	Tipo	Descrição
previsao_esperada	DATETIME	Data calculada com base na criticidade
dias_uteis_resolucao	INTEGER	Dias úteis entre criação e resolução
sla_criticidade_ok	INTEGER	1=cumprido, 0=estourado, NULL=em aberto
3.5.4 Métricas
Métrica	Fórmula
% Cumprimento por criticidade	COUNT(sla_criticidade_ok=1) / COUNT(*) * 100
Média dias úteis	AVG(dias_uteis_resolucao) GROUP BY prioridade
Tickets fora do prazo	COUNT(sla_criticidade_ok=0)
3.5.5 Visualizações
Gráfico de barras: % cumprimento por criticidade

Gráfico de barras: dias úteis médios vs. ideal

KPIs no topo: total, % cumprido, média dias

### 3.5.6 Insights Automáticos
⚠️ Se Urgente < 90% → alerta crítico

⚠️ Se qualquer criticidade < 70% → alerta

✅ Se todas > 85% → OK

### 3.5.7 Resultados Observados
Distribuição dos tickets (base 2024-2026):

Criticidade	Total	Cumpridos	%
Média-2	1.782	1.173	65.8% ⚠️
Baixa-2	2.258	1.616	71.6% ⚠️
Alta	404	306	75.7%
Urgente	67	53	79.1% ⚠️
Baixa	777	618	79.5%
Média	4.536	3.667	80.8% ✅
Insight: Prioridades Média-2 e Baixa-2 são as que mais estouram. Urgente abaixo de 80% é crítico.

---


## 4. Produtividade

### 4.1 Tickets Resolvidos por Analista 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Quem resolve mais tickets |
| **Métrica** | `COUNT(tickets WHERE responsavel_atual = X)` |
| **Fonte** | `tickets` |
| **Frequência** | Semanal |

⚠️ **Cuidado ético:** volume **não** é produtividade. Tickets complexos valem mais.

---

### 4.2 Backlog Atual 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Quantos tickets abertos por analista |
| **Métrica** | `COUNT(status NOT IN (Resolvido/Fechado/Cancelado)) GROUP BY responsavel_atual` |
| **Fonte** | `tickets` |

**Insight:** identificar **sobrecarga**.

---

### 4.3 Taxa de Reabertura 🥈

| Campo | Valor |
|---|---|
| **Objetivo** | % de tickets que voltaram após resolvidos |
| **Métrica** | `COUNT(data_resolvido != data_1_resolvido) / COUNT(*)` |

**Insight:** indica **qualidade** da resolução.

---

## 5. Roteamento ⭐

### 5.1 % de Encaminhamentos Incorretos 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Quantos tickets foram para área errada |
| **Métrica** | `COUNT(encaminhamentos errados) / COUNT(total)` |
| **Fonte** | `mensagens` |

**Como detectar "errado":**
- Se o ticket **voltou** da área destino
- Se foi redirecionado antes de resolver

---

### 5.2 Número de Pulos por Ticket 🥇

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

### 5.3 Caminhos Mais Comuns 🥈

| Campo | Valor |
|---|---|
| **Objetivo** | Mapear caminhos entre áreas |
| **Métrica** | `COUNT` agrupado por `(origem, destino)` |
| **Fonte** | `mensagens` |

**Visualização:** grafo direcionado (networkx + pyvis).

**Exemplo:**
Triagem → Java → Resolvido 45 tickets (0.9 dia)
Triagem → Folha → Financeiro → Folha 23 tickets (8.2 dias) ⚠️

text

---

### 5.4 Áreas "Armadilha" 🥈

| Campo | Valor |
|---|---|
| **Objetivo** | Onde os tickets ficam presos |
| **Métrica** | Áreas com maior `AVG(tempo entre envio e próxima ação)` |

---

## 6. Gargalos (Não Retorno) ⭐

### 6.1 Tempo até 1ª Ação do Responsável 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Depois de receber, quanto tempo o analista demora para agir |
| **Métrica** | `AVG(1a_mensagem_do_analista - recebimento)` |
| **Fonte** | `mensagens` |

**Como calcular:**
1. Quando o ticket foi atribuído a um analista
2. Primeira mensagem desse analista
3. Diferença = tempo até 1ª ação

---

### 6.2 Tickets Esquecidos 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Tickets que receberam alguém mas ninguém agiu |
| **Métrica** | `COUNT(tempo_ate_1a_acao > 2 dias)` |
| **Fonte** | `mensagens` |

**Ação:** alerta por email ao responsável + supervisor.

---

### 6.3 Ranking de Analistas por Gargalo 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Quem está com mais tickets "esquecidos" |
| **Métrica** | `COUNT(tickets_esquecidos) GROUP BY analista` |

⚠️ **Cuidado:** não usar para punição. Usar para **identificar sobrecarga**.

---

## 7. Diagnóstico (Matriz de Verdade) 

### 7.1 Distribuição dos 12 Cenários 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Classificar cada ticket em um dos 12 cenários da matriz |
| **Métrica** | `COUNT(tickets) GROUP BY diagnostico` |
| **Fonte** | `tickets` (coluna `diagnostico`) |

**Saída esperada:**
CEN-01: X CEN-07: X
CEN-02: X CEN-08: X
CEN-03: X CEN-09: X
CEN-04: X CEN-10: X
CEN-05: X CEN-11: X
CEN-06: X CEN-12: X
OUTRO: X
SEM_DADOS: X

text

---

### 7.2 Ação Interna vs Externa 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | % de tickets em que o responsável foi quem mexeu por último |
| **Métrica** | `COUNT(acao_interna = 1) / COUNT(*)` |
| **Fonte** | `tickets` (coluna `acao_interna`) |

**Interpretação:**
- Alto % → equipe ativa
- Baixo % → tickets parados ou terceirizados

---

### 7.3 Tickets Travados SPPREV 🥇

| Campo | Valor |
|---|---|
| **Objetivo** | Tickets SPPREV em aberto sem ação por > 3 dias |
| **Métrica** | `COUNT(tickets travados)` |
| **Regra** | Ver [05_Regras_de_Negocio.md](05_REGRAS_DE_NEGOCIO.md#6-tickets-travados) |

**Aplicação:**

sql
SELECT id, titulo, responsavel_atual, dias_aberto
FROM tickets
WHERE status IN ('Em atendimento', 'Aguardando confirmação do usuário')
  AND responsavel_empresa = 'SPPREV'
  AND acao_interna = 1
  AND backlog = 0
  AND (julianday('now') - julianday(criado_data)) > 3
ORDER BY dias_aberto DESC;
Visualizações:

Ranking por responsável

Lista detalhada (Top 30)

Aging médio

### 7.4 Tickets Atlantic (Informativo) 🥈
Campo	Valor
Objetivo	Atlantic em situação similar (não gera alerta)
Métrica	COUNT(tickets onde resp=Atlantic E acao_interna=1 E dias>3)
Ação	Informativo apenas
Motivo: não compete ao SPPREV cobrar. Mas é útil saber a extensão.

### 7.5 Distribuição SPPREV vs Atlantic 🥇
Campo	Valor
Objetivo	Quanto cada empresa está com carga
Métrica	COUNT(tickets) GROUP BY responsavel_empresa
Fonte	tickets
Saída esperada:

text
SPPREV:   3.911
Atlantic: 2.805
Externo:  1.155
Outro:    2.187
Insight: se Atlantic tem > 50% dos tickets, indica dependência externa alta.

### 8. Backlog
### 8.1 Tickets em Backlog 🥇
Campo	Valor
Objetivo	Quantos tickets estão na fila do backlog
Métrica	COUNT(backlog = 1)
Fonte	tickets
Insight: backlog grande pode indicar capacidade insuficiente.

### 8.2 Tickets Fora do Backlog 🥇
Campo	Valor
Objetivo	Tickets que deveriam estar em atendimento mas não estão
Métrica	COUNT(backlog = 0 E status em aberto)
Insight: se muitos tickets estão fora do backlog sem ação → problema de triagem.

## 8.5 Grafo de Roteamento 

### 8.5.1 Objetivo

Visualizar o **fluxo de encaminhamentos** entre analistas.

### 8.5.2 Como Funciona

**Fonte dos dados:** tabela `movimentacoes`

**Extração de encaminhamentos:**
Para cada ticket:
Ordena movimentações por data
Para cada par consecutivo (autor_A, autor_B):
Se autor_A ≠ autor_B:
incrementa aresta A → B

text

**Contagem:** cada par (origem, destino) tem um peso = número de vezes que ocorreu.

### 8.5.3 Visualização

- **Nós** = analistas (tamanho = volume de encaminhamentos)
- **Arestas** = encaminhamentos (espessura = quantidade)
- **Cor do nó** = empresa (SPPREV dourado, Atlantic verde)
- **Interativo** (arrastar, zoom, tooltip)

### 8.5.4 Filtros Disponíveis

| Filtro | Valores |
|---|---|
| Período | Data inicial/final |
| Top N | 5 a 50 analistas |
| Empresa | Todas, SPPREV, Atlantic, Externo |

### 8.5.5 Stack

- `networkx` — análise de grafos
- `pyvis` — visualização interativa

### 8.5.6 Insights

| Padrão | Significado |
|---|---|
| **Hub** | Nó grande = analista central |
| **Ciclo** | A → B → A (retrabalho) |
| **Ponte** | Conecta 2 áreas isoladas |
| **Isolado** | Nó periférico com poucas conexões |

---

## 8.6 Árvore de Encaminhamentos ⭐ NOVO

### 8.6.1 Objetivo

Visualizar o **fluxo completo** de um ticket específico.

### 8.6.2 Como Funciona

**Input:** ID do ticket
**Fonte:** `movimentacoes` filtradas por `ticket_id`

**Layout:** Vertical em cascata
[Solicitante]
↓
[Autor 1]
↓
[Autor 2]
↓
[Autor N]

text

### 8.6.3 Elementos Visuais

- **Círculo colorido** por empresa
- **Box ao lado** com autor + data + status
- **Setas** indicando sequência temporal
- **Alternância** esquerda/direita para clareza

### 8.6.4 Stack

- `networkx` — construção do grafo
- `matplotlib` — renderização (sem precisar de Graphviz)

### 8.6.5 Quando Usar

- Investigar tickets com muitos pulos
- Entender o caminho do ticket
- Auditoria de fluxo
- Apresentar histórico para chefia

### 9. Reincidência
### 9.1 Taxa de Reincidência 🥈
Campo	Valor
Objetivo	O mesmo problema está voltando?
Métrica	COUNT(solicitantes com > 1 ticket) / COUNT(distintos)
Fonte	tickets
### 9.2 Top 10 Solicitantes 🥈
Campo	Valor
Objetivo	Quem abre mais tickets
Métrica	COUNT(*) GROUP BY solicitante ORDER BY DESC LIMIT 10
Insight: pode indicar problema sistêmico.

### 10. Backlog e Tendências
### 10.1 Aging Médio 🥈
Campo	Valor
Métrica	AVG(hoje - criado_data) WHERE status != Resolvido
Fonte	tickets
Interpretação:

Aging baixo → dando conta

Aging alto → backlog antigo acumulando

### 10.2 Taxa Entrada vs. Saída 🥈
Campo	Valor
Métrica	novos_hoje / resolvidos_hoje
Interpretação:

1 → backlog crescendo ⚠️

= 1 → estável

< 1 → reduzindo ✅

### 10.3 Projeção de Fechamento 🥈
Campo	Valor
Métrica	backlog_atual / média_resolvidos_por_dia
Resultado	Dias estimados para zerar
### 11. Sazonalidade
### 11.1 Volume por Dia da Semana 🥉
Campo	Valor
Métrica	COUNT(*) GROUP BY dia_semana
Insight: identifica padrões (ex: "segundas têm 40% mais tickets").

### 11.2 Volume por Hora 🥉
Campo	Valor
Métrica	COUNT(*) GROUP BY HOUR(criado_data)
Insight: dimensionar equipe por turno.

11.3 Comparativo YoY 🥉
Campo	Valor
Métrica	Volume mensal atual vs. mesmo mês do ano passado
12. Análises Futuras (NLP)
12.1 Classificação Automática de Rotas ⏳
Campo	Valor
Objetivo	Dado título + descrição, sugerir área correta
Técnica	TF-IDF + Logistic Regression (v1) ou BERTimbau (v2)
Prioridade	⏳ Futuro
Treinamento: tickets resolvidos → área final que resolveu.

Impacto esperado: redução de 40-60% nos pulos.

12.2 Detecção de Urgência ⏳
Campo	Valor
Técnica	Palavras-chave + sentimento
Palavras-gatilho:

"urgente", "prazo", "hoje"

"judicial", "prazo legal"

Sentimento negativo extremo

12.3 Detecção de Duplicatas ⏳
Campo	Valor
Técnica	Similaridade de cosseno entre descrições
12.4 Sumarização ⏳
Campo	Valor
Técnica	LLM (via API)
Objetivo: gerar resumo de tickets com histórico longo para supervisão.

13. Alertas Automáticos
#	Alerta	Condição	Canal	Prioridade
A1	SLA em risco	previsao < hoje + 1d	Email	🥇
A2	SLA estourado	data_resolvido > previsao	Email	🥇
A3	Ticket parado	hoje - alterado_data > 7d	Email	🥇
A4	Ticket travado SPPREV	acao_interna=1 E dias>3 E resp_emp=SPPREV E backlog=0	Email	🥇
A5	Volume anormal	hoje > média + 2σ	Email	🥈
A6	Backlog crescendo	novos > resolvidos por 3d	Email	🥈
A7	Reincidência	3+ tickets mesmo CPF em 30d	Email	🥉
14. Matriz de Priorização
Análise	Impacto	Esforço	Prioridade
Tempo de resposta	Alto	Baixo	🥇
SLA	Alto	Baixo	🥇
Diagnóstico (travados)	Alto	Médio	🥇
Gargalos (não retorno)	Alto	Médio	🥇
Roteamento	Alto	Médio	🥇
Distribuição SPPREV/Atlantic	Alto	Baixo	🥇
Backlog	Médio	Baixo	🥈
Produtividade	Médio	Baixo	🥈
Reincidência	Médio	Médio	🥉
Sazonalidade	Baixo	Baixo	🥉
NLP	Alto	Alto	⏳
15. Roadmap de Implementação
Fase	Análises entregues
Fase 3	Tempo de resposta, SLA, Produtividade, Gargalos
Fase 4	Diagnóstico, Roteamento, Backlog
Fase 5	Reincidência, Sazonalidade, Alertas
Fase 6	NLP e predição
16. Referências
04_Modelo_Dados.md

05_Regras_de_Negocio.md

07_Interfaces.md