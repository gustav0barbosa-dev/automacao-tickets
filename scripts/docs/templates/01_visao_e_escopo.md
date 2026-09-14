# 01 — Visão e Escopo

**Documento:** Visão Geral, Objetivos e Limites do Sistema
**Versão:** 2.0
**Público-alvo:** Todos os envolvidos no projeto

---

## 1. Contexto

A SPPREV (São Paulo Previdência) opera o sistema **Help360** para gestão de chamados
internos e externos. Atualmente, o acompanhamento dos tickets é feito de forma
**manual** e **fragmentada**:

- Operadores abrem ticket por ticket no navegador
- Não há visão consolidada do volume, tempo de resposta ou SLA
- Não há registro histórico estruturado de decisões
- Não há identificação de gargalos ou padrões

Esse cenário gera:

- **Perda de eficiência** (tempo gasto em tarefas repetitivas)
- **Falta de visibilidade** para a supervisão
- **Dificuldade de auditoria** (não há trilha)
- **Incapacidade de tomar decisões baseadas em dados**

---

## 2. Objetivo

Desenvolver uma **plataforma de automação e análise** que transforme o processo
manual em um **pipeline inteligente**, capaz de:

1. **Coletar** automaticamente a base de tickets
2. **Enriquecer** cada ticket com descrição e histórico de mensagens
3. **Persistir** em banco de dados para análise
4. **Filtrar** os tickets que precisam de ação
5. **Abrir** os tickets no navegador
6. **Analisar** métricas de tempo, SLA, produtividade e roteamento
7. **Alertar** sobre anomalias e SLA em risco
8. **Visualizar** em dashboard

---

## 3. Problema Resolvido

| Cenário Atual | Cenário com a Automação |
|---|---|
| Abrir cada ticket manualmente | Pipeline abre todos em lote |
| Conferir resposta caso a caso | Cruzamento automático com Tabela fato |
| Sem visão do que está pendente | `acompanhamento.xlsx` lista o que tratar |
| Sem análise de tempo de resposta | Métricas automáticas por categoria e analista |
| Sem monitoramento de SLA | Alertas automáticos de SLA em risco |
| Sem identificação de gargalos | Análise de "não retorno" por analista |
| Sem visão de roteamento | Grafo de fluxo entre áreas |
| Sem histórico | Banco de dados com 100% das movimentações |

---

## 4. Público-Alvo

### 4.1 Usuários Diretos

| Perfil | Uso | Frequência |
|---|---|---|
| **Operador de tickets** | Roda pipeline, trata os tickets abertos | Diária |
| **Supervisor** | Consome relatórios e dashboard | Semanal |
| **Analista de dados** | Consulta banco, gera análises | Conforme demanda |
| **Gestor** | Toma decisões baseadas em indicadores | Mensal |

### 4.2 Usuários Indiretos

| Perfil | Uso |
|---|---|
| **Equipe de TI** | Mantém a infraestrutura |
| **Auditoria** | Consulta trilha de decisões |
| **Outros órgãos** | Podem replicar a solução |

---

## 5. Escopo

### 5.1 Dentro do Escopo (In-Scope)

- ✅ Coleta de tickets do Help360 via Selenium
- ✅ Enriquecimento com descrição e mensagens
- ✅ Persistência em banco SQLite
- ✅ Filtragem inteligente com regras configuráveis
- ✅ Abertura automática em navegador
- ✅ Análises: tempo de resposta, SLA, produtividade, roteamento, gargalos
- ✅ Alertas automáticos
- ✅ Dashboard web
- ✅ Relatórios exportáveis (Excel, PDF)

### 5.2 Fora do Escopo (Out-of-Scope)

- ❌ **Alteração do sistema Help360** — somos consumidores, não modificadores
- ❌ **Resolução automática de tickets** — decisão permanece humana
- ❌ **Substituição do Help360** — somos uma camada de análise
- ❌ **Integração com sistemas externos** (RH, Financeiro)
- ❌ **Aplicativo mobile**
- ❌ **Autenticação SSO** (na v1; ver roadmap)

### 5.3 Roadmap Futuro (Out-of-Scope inicial)

- Classificação automática de rotas via NLP
- Previsão de volume com séries temporais
- Detecção de duplicatas
- Sumarização automática

---

## 6. Premissas

| # | Premissa |
|---|---|
| 1 | O Help360 continuará disponível e com a mesma estrutura |
| 2 | O operador atualizará a Tabela fato regularmente |
| 3 | Os analistas manterão suas áreas padronizadas |
| 4 | O ambiente Windows é o padrão da equipe |
| 5 | Haverá acesso contínuo ao Help360 via credenciais @sp.gov.br |

---

## 7. Restrições

| # | Restrição |
|---|---|
| 1 | Python 3.10+ (limitação do ambiente) |
| 2 | Windows 10/11 (limitação do parque tecnológico) |
| 3 | Sem acesso a APIs REST do Help360 (só scraping) |
| 4 | Dados sensíveis (LGPD) — exigem anonimização |
| 5 | Sem banco de dados em nuvem (dados ficam on-premise) |

---

## 8. Métricas de Sucesso

| Métrica | Baseline | Meta (6 meses) |
|---|---|---|
| Tempo médio de abertura de tickets | 2h/dia manual | 5 min (automático) |
| % SLA cumprido | Não medido | > 95% |
| Tempo médio de resolução | Não medido | Reduzir 30% |
| Pulos por ticket | Não medido | Reduzir 40% |
| Tickets esquecidos (>3d) | Não medido | Zero |
| Cobertura de análise | 0% | 100% dos tickets |

---

## 9. Riscos

| # | Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|---|
| 1 | Site do Help360 mudar HTML | Alta | Alto | Seletores robustos + fallback |
| 2 | Volume de dados crescer muito | Baixa | Médio | SQLite aguenta; migração para Postgres se necessário |
| 3 | Baixa adesão da equipe | Média | Alto | Envolver chefia; mostrar valor cedo |
| 4 | Vazamento de dados (LGPD) | Média | Alto | Anonimização + controle de acesso |
| 5 | Dependência de uma pessoa | Alta | Alto | Documentar tudo; treinar equipe |

---

## 10. Referências

- [02_Requisitos.md](02_REQUISITOS.md) — Detalhamento funcional
- [11_Roadmap.md](11_ROADMAP.md) — Plano de evolução
- [Site Help360](https://spprev.help360.com.br)
- [Lei Geral de Proteção de Dados](https://www.gov.br/cidadania/pt-br/acesso-a-informacao/lgpd)
