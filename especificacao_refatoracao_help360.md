# Especificação de Refatoração e Reorganização do Help360

**Projeto:** Help360 / Automação de Tickets — SPPREV  
**Documento:** Especificação de refatoração do dashboard e consolidação funcional  
**Versão:** 1.0  
**Data:** 06/11/2026  


---

## 1. Objetivo do documento

Este documento define o que deve ser reorganizado, preservado, reutilizado, consolidado ou removido no projeto Help360, com foco na limpeza da estrutura e na reorganização do dashboard em quatro áreas funcionais:

1. **SLA + Reincidência (Reabertura)**
2. **Produtividade + Roteamento**
3. **Tendências / BI**
4. **Inteligência de Tickets**

A proposta não é reescrever o sistema. É realizar uma refatoração incremental, preservando o pipeline de coleta, enriquecimento, persistência, autenticação, regras de negócio e componentes que já entregam valor.

## 2. Resumo executivo

O projeto já possui uma base funcional relevante: coleta e persistência de tickets, histórico de movimentações, mensagens, cadastro de analistas, páginas de SLA, produtividade, roteamento, reincidência e tendências, além de componentes visuais compartilhados.

O principal problema observado é a fragmentação da navegação e a distribuição de responsabilidades. Algumas páginas apresentam análises relacionadas em lugares diferentes, enquanto parte da lógica de consulta, transformação e cálculo está implementada dentro das próprias views. Há também duplicação de funções de acesso a dados.

A solução recomendada é consolidar o dashboard em quatro áreas, criar uma camada de serviços de análise entre o acesso a dados e as views, padronizar filtros e métricas e preservar os componentes de visualização já existentes.

**Não apagar o pipeline de automação nem as tabelas de histórico.** A limpeza deve se concentrar em páginas redundantes, código duplicado, módulos obsoletos e artefatos que não pertencem ao código-fonte.

## 3. Diagnóstico do estado atual

### 3.1 Estrutura atual identificada

O ZIP contém, entre outros, os seguintes módulos:

| Área | Arquivos identificados | Situação observada |
|---|---|---|
| Entrada do dashboard | `dashboard.py`, `dashboard/app.py` | Existem dois pontos de entrada; confirmar qual é o oficial e eliminar ambiguidade |
| Configuração | `dashboard/config.py` | Mantém menu, cores, limites e constantes |
| Acesso a dados | `dashboard/data.py` | Centraliza engine e carregamento, mas contém funções duplicadas |
| Filtros | `dashboard/filters.py` | Aplica filtros globais, principalmente sobre data de criação |
| Componentes | `dashboard/components.py`, `lucide.py`, `theme.py` | Reutilizáveis; preservar e padronizar |
| Grafos | `dashboard/components_grafo.py` | Implementa visualizações de fluxo e árvore de ticket; preservar |
| Views atuais | `dashboard/views/*.py` | Dez páginas principais, com sobreposição funcional |
| Regras de domínio | `src/utils_sla.py`, regras em `docs/05_REGRAS_DE_NEGOCIO.md` | Devem continuar como referência para os cálculos |
| Banco | `dados/schema.sql`, `dados/migrations/*.sql` | Contém tickets, movimentações, mensagens, analistas, áreas e snapshots |
| Testes | `tests/` | Há testes de pipeline, banco e utilitários; ampliar para regras e dashboard |

### 3.2 Problemas técnicos identificados

1. **Duplicação em `dashboard/data.py`:** `carregar_movimentacoes()` e `carregar_mensagens()` aparecem definidas mais de uma vez. Deve existir uma única implementação de cada função.
2. **Lógica de negócio dentro das views:** cálculos de tempo, agrupamentos, classificações e indicadores são feitos em páginas. Isso dificulta testes e reutilização.
3. **Filtros globais inadequados para todas as análises:** o filtro de período atual usa `criado_data`. Produtividade e roteamento precisam também filtrar por data de movimentação, período de atribuição e período de permanência.
4. **Navegação fragmentada:** páginas de SLA e reincidência, assim como produtividade e roteamento, estão separadas apesar de formarem jornadas de análise relacionadas.
5. **Produtividade incompleta em relação ao objetivo futuro:** a view atual trabalha com volume por responsável e tempo médio de resolução. A nova área precisa medir tempo de espera, tempo sob responsabilidade e permanência por etapa.
6. **Tendências ainda não é um módulo de BI gerencial:** já existem gráficos temporais, mas faltam comparativos padronizados, tabelas analíticas, indicadores explicáveis e preparação para reuniões.
7. **Ponto de entrada duplicado:** confirmar a função de `dashboard.py` na raiz e padronizar a execução por `dashboard/app.py` (ou pelo arquivo escolhido como oficial).
8. **Acoplamento ao SQLite em componentes de grafo:** `components_grafo.py` define caminho local do banco, embora `data.py` suporte PostgreSQL. As consultas devem usar a engine compartilhada.
9. **Configuração da página Streamlit:** `st.set_page_config()` deve ser executado antes de qualquer outra chamada Streamlit. No `dashboard/app.py` analisado, a tela de login é chamada antes dessa configuração; corrigir a ordem.
10. **Filtros aplicados indiscriminadamente:** o filtro global de criação pode excluir tickets cujo evento relevante ocorreu no período selecionado. Cada área deve declarar qual data dirige sua análise.
11. **Documentação desatualizada em relação ao código:** alguns documentos ainda descrevem fases como roadmap ou funcionalidades futuras, embora existam módulos implementados. Atualizar após a refatoração.
12. **Ausência de testes específicos para as quatro jornadas:** criar testes de domínio e integração para os cálculos que sustentam os indicadores.

### 3.3 Divergência sobre o MLP da Fase 3

O relatório de implementação da Fase 3 descreve arquivos como `dashboard/views/validacao_motivos.py`, `dashboard/views/monitoramento.py` e scripts `07` a `10` de auditoria, taxonomia, treinamento e monitoramento.

**Esses arquivos não foram encontrados no ZIP analisado.** O arquivo contém apenas scripts de treinamento anteriores e uma amostra de validação. Portanto:

- confirmar se o ZIP é uma versão anterior à implementação da Fase 3;
- não excluir os arquivos do MLP da versão atual do repositório;
- integrar a Inteligência de Tickets usando a versão efetivamente existente e versionada;
- antes de remover ou reorganizar pastas de treinamento, comparar o repositório atual com os artefatos do relatório.

Essa divergência deve ser resolvida antes de uma limpeza destrutiva.

## 4. Arquitetura funcional desejada

### 4.1 Menu principal proposto

| Grupo no dashboard | Página | Responsabilidade |
|---|---|---|
| OPERAÇÃO | SLA + Reincidência | Cumprimento de SLA, risco e reaberturas |
| OPERAÇÃO | Produtividade + Roteamento | Tempos por responsável, espera, histórico e fluxo |
| GESTÃO | Tendências / BI | Comparativos, indicadores gerenciais e relatórios |
| INTELIGÊNCIA | Inteligência de Tickets | Temas, problemas operacionais e recomendações |

A página inicial pode ser uma visão resumida do BI ou uma tela inicial leve com atalhos e indicadores. Não é necessário manter uma página independente de Visão Geral se ela duplicar informações do BI.

### 4.2 Estrutura de navegação

- **OPERAÇÃO**
  - SLA + Reincidência
  - Produtividade + Roteamento
- **GESTÃO**
  - Tendências / BI
- **INTELIGÊNCIA**
  - Inteligência de Tickets

A página Relatórios deixa de ser uma área isolada se sua função for apenas exportar dados. Exportação deve estar disponível dentro das áreas relevantes, respeitando filtros e permissões.

## 5. Especificação funcional das quatro áreas

## 5.1 SLA + Reincidência (Reabertura)

### Objetivo

Unificar o acompanhamento de prazos de SLA com a identificação de tickets que retornaram a estados de trabalho após terem sido resolvidos ou fechados.

### Funcionalidades

- Indicadores de SLA cumprido, estourado, em andamento e em risco.
- Cumprimento de SLA por período, categoria, prioridade e área.
- Lista de tickets próximos do vencimento ou já fora do prazo.
- Taxa de reabertura no período.
- Quantidade de reaberturas por ticket.
- Identificação das transições de `Resolvido` ou `Fechado` para `Em atendimento`, `Aguardando confirmação do usuário` ou outro estado definido como reabertura.
- Linha do tempo de status do ticket.
- Filtros por período, categoria, prioridade, responsável, área, status e ID do ticket.
- Detalhamento do ticket que originou cada indicador.

### Regras de negócio

1. O SLA deve respeitar a data de previsão (`previsao`) registrada pelo Help360, salvo quando uma regra oficial de cálculo substituta for aprovada.
2. Conforme a regra documentada atualmente, o SLA é:
   - Cumprido: `data_resolvido <= previsao`;
   - Estourado: `data_resolvido > previsao`;
   - Em andamento: `data_resolvido IS NULL`;
   - Em risco: previsão próxima do vencimento e ticket ainda não resolvido.
3. A documentação existente informa que o cálculo atual utiliza dias corridos. A conversão para dias úteis, incluindo feriados nacionais e estaduais, aparece como regra desejada, mas não deve ser considerada implementada sem validação do código e dos dados.
4. A reincidência de reabertura deve ser calculada pelo histórico de movimentações, não apenas pela diferença entre `data_resolvido` e `data_1_resolvido`.
5. Uma reabertura ocorre quando há transição de um estado terminal definido para um estado ativo definido. A lista de estados deve ser normalizada e configurável.
6. Não contar a criação inicial do ticket como reabertura.
7. Contar eventos de reabertura e tickets reabertos como métricas distintas:
   - **Tickets reabertos:** quantidade de IDs que tiveram ao menos uma reabertura;
   - **Eventos de reabertura:** quantidade total de transições de retorno;
   - **Taxa de reabertura:** tickets reabertos / tickets elegíveis encerrados no período, com denominador explicitado.
8. Um ticket pode ser reaberto mais de uma vez. A linha do tempo deve preservar todos os eventos.
9. O período de análise deve indicar qual data está sendo usada: criação, resolução ou evento de reabertura.
10. Status como Cancelado, Duplicado e outros estados administrativos não devem ser tratados como reabertura sem regra explícita.

### Indicadores recomendados

| Indicador | Definição |
|---|---|
| % SLA cumprido | Tickets resolvidos no prazo / tickets resolvidos com previsão válida |
| Tickets em risco | Tickets abertos próximos do vencimento |
| Tickets com SLA estourado | Tickets resolvidos após a previsão ou abertos após vencimento, apresentados separadamente |
| Taxa de reabertura | Tickets reabertos / tickets encerrados elegíveis |
| Total de eventos de reabertura | Número de transições de retorno |
| Média de reaberturas por ticket reaberto | Eventos / tickets reabertos |
| Motivos com maior reabertura | Agrupamento por categoria/motivo real, quando disponível |

**Atenção:** não misturar tickets em aberto e resolvidos no mesmo denominador de cumprimento. Exibir quantidade de registros sem previsão válida e dados incompletos.

## 5.2 Produtividade + Roteamento

### Objetivo

Oferecer uma visão operacional do ciclo de vida do ticket: quanto tempo aguarda, quanto tempo permanece com cada responsável ou área, quantas transferências ocorrem e qual caminho percorre até a resolução.

### Pesquisa e filtros

A área deve ter uma pesquisa detalhada, com os seguintes filtros:

- Nome do analista/responsável;
- Área de origem ou destino;
- Período;
- Assunto/título;
- ID do ticket;
- Status;
- Categoria ou motivo;
- Tipo de evento (atribuição, encaminhamento, mensagem, mudança de status).

A pesquisa por ID deve permitir abrir a linha do tempo completa do ticket.

### Funcionalidades de produtividade

- Tempo total desde a abertura.
- Tempo até a primeira ação.
- Tempo em cada responsável.
- Tempo em cada área.
- Tempo em estado de espera.
- Tempo em atendimento ativo, quando houver evidência de atividade.
- Quantidade de tickets recebidos, transferidos e resolvidos.
- Distribuição de carga por responsável e área.
- Identificação de tickets com longos intervalos sem movimentação.
- Tabela detalhada com ticket, responsável, área, início, fim, duração e evento que encerrou a etapa.

### Funcionalidades de roteamento

- Grafo geral de encaminhamentos entre áreas ou responsáveis.
- Direção das transferências (origem → destino).
- Peso da aresta representando quantidade de tickets ou transferências.
- Caminhos mais comuns.
- Quantidade de transferências por ticket.
- Identificação de retornos para uma área anterior.
- Árvore/linha do tempo de um ticket individual.
- Destaque de etapas com maior tempo de espera.
- Comparação entre caminhos que resolvem rapidamente e caminhos com maior duração.

### Regras de negócio

1. A duração de uma etapa deve ser calculada entre dois eventos cronológicos válidos e consecutivos que representem mudança de responsável, área ou estado.
2. Não inferir que o responsável atual esteve com o ticket durante todo o período histórico. Usar os eventos de atribuição/encaminhamento.
3. Se não houver evento de atribuição confiável, marcar a duração como desconhecida; não preencher com zero.
4. O tempo de espera entre movimentações não deve ser automaticamente chamado de tempo de trabalho do analista.
5. Distinguir:
   - tempo total do ticket;
   - tempo sob responsabilidade de uma pessoa;
   - tempo sob responsabilidade de uma área;
   - tempo em estado de espera;
   - intervalo sem movimentação registrada.
6. O cálculo deve respeitar a ordenação por data e hora. Eventos com data inválida ou duplicidade precisam ser sinalizados.
7. Se duas movimentações tiverem o mesmo timestamp, aplicar critério estável de ordenação e marcar a ambiguidade quando ela alterar a interpretação.
8. Volume de tickets não equivale isoladamente a produtividade. Exibir complexidade, tempo, situação e contexto; não transformar ranking em avaliação individual automática.
9. A classificação de empresa (SPPREV, Atlantic, Externo, Outro) e as regras de responsabilidade existentes devem ser preservadas.
10. Os filtros de período devem informar se filtram tickets criados no período ou eventos ocorridos no período.

### Indicadores recomendados

| Indicador | Definição |
|---|---|
| Tempo até primeira ação | Primeira ação válida - recebimento/atribuição |
| Tempo médio/mediano por responsável | Soma/mediana da permanência em cada responsável |
| Tempo médio/mediano por área | Permanência entre entrada e saída da área |
| Tickets sem movimentação | Tickets com último evento anterior ao limite definido |
| Transferências por ticket | Quantidade de eventos de encaminhamento |
| Taxa de retorno de rota | Tickets que voltam a uma área já visitada / tickets roteados |
| Caminho mais frequente | Sequência de áreas mais observada |
| Gargalos por etapa | Etapas com maior mediana de espera |

Sempre apresentar média e mediana quando houver assimetria ou valores extremos. Definir limites de outlier de forma documentada, sem apagar os registros da consulta detalhada.

## 5.3 Tendências / BI

### Objetivo

Transformar a página Tendências em um painel de Business Intelligence para análise comparativa, acompanhamento de desempenho e apresentação em reuniões de gestão.

### Funcionalidades

- Comparação mês a mês.
- Comparação entre períodos selecionados.
- Comparação com o mesmo mês do ano anterior, quando houver histórico.
- Tabelas analíticas com totais, variações absolutas e percentuais.
- Gráficos de linha para evolução temporal.
- Gráficos de barras para comparação de categorias, áreas e motivos.
- Gráficos empilhados para composição de status ou categorias.
- Tabelas de ranking e detalhamento.
- Indicadores de volume, SLA, reabertura, tempo de resolução, espera e roteamento.
- Exportação dos dados filtrados para Excel e relatório para reunião.
- Identificação de variações relevantes, com explicação do cálculo.
- Filtros persistentes por período, área, categoria, prioridade, status e responsável.

### Regras de negócio

1. Comparações devem usar períodos equivalentes. Mês parcial não deve ser comparado silenciosamente com mês completo.
2. Todo gráfico deve informar período, unidade, denominador e data de referência.
3. Variação percentual deve tratar corretamente o período anterior igual a zero; nesse caso, exibir “sem base de comparação”, não infinito.
4. Indicadores calculados com amostras diferentes devem ser identificados. Exemplo: SLA só pode considerar tickets com previsão válida.
5. Para volume criado, usar `criado_data`; para volume resolvido, usar `data_resolvido`; para reabertura, usar a data do evento de reabertura.
6. A série temporal deve preservar meses sem ocorrência, exibindo zero quando a ausência de registros for real e não falha de coleta.
7. A página deve permitir abrir os tickets que compõem um indicador, sempre que a permissão e a disponibilidade dos dados permitirem.
8. Exportações devem respeitar os mesmos filtros exibidos na tela e aplicar anonimização quando necessário.

### Indicadores de gestão sugeridos

- Tickets criados e resolvidos por mês;
- saldo de backlog no fim de cada mês, se houver snapshots confiáveis;
- cumprimento de SLA;
- taxa de reabertura;
- tempo de resolução;
- tempo de primeira ação;
- tickets sem movimentação;
- volume por área, categoria e motivo real;
- assuntos com crescimento acima da linha de base;
- quantidade de tickets por rota e transferências.

### Padrão visual para reuniões

- KPIs resumidos no topo;
- comparação principal em gráficos centrais;
- tabela de variação logo abaixo;
- filtros visíveis e período de referência destacado;
- legendas e unidades explícitas;
- botão de exportação;
- evitar excesso de gráficos decorativos ou métricas sem decisão associada.

## 5.4 Inteligência de Tickets

### Objetivo

Identificar padrões nos assuntos e descrições, descobrir problemas operacionais recorrentes e propor melhorias para processos, sistemas, formulários e futuras atualizações.

### Funcionalidades

- Classificação do motivo real do ticket, independente do assunto informado na abertura.
- Ranking de assuntos/motivos mais recorrentes.
- Detecção de novos temas e clusters emergentes.
- Evolução mensal dos motivos.
- Identificação de assunto possivelmente incorreto ou genérico.
- Identificação de descrição insuficiente, incompleta ou sem contexto.
- Detecção de possíveis duplicidades e reincidências temáticas.
- Cruzamento dos motivos com SLA, reabertura, tempo parado e roteamento.
- Recomendações de melhoria com evidências.
- Detalhamento dos tickets usados para sustentar cada insight.
- Fila de revisão humana para classificações incertas ou novos temas.
- Histórico das recomendações, decisões e resultados.

### Reutilização do MLP existente

A implementação descrita no relatório da Fase 3 deve ser reutilizada quando os arquivos correspondentes forem confirmados na versão atual:

- taxonomia de motivos;
- regras de rotulagem fraca;
- clusters emergentes e auditoria;
- interface de validação humana;
- classificador supervisionado;
- monitoramento de qualidade;
- exportação e aplicação de rótulos humanos no Active Learning.

Não treinar outro modelo apenas para montar o dashboard. Primeiro integrar o classificador atual e validar sua saída, sua versão e suas métricas.

### Regras de negócio

1. Toda classificação deve armazenar motivo previsto, versão do modelo, confiança ou margem de decisão e data da inferência.
2. A confiança do modelo não deve ser apresentada como probabilidade calibrada se não houver calibração comprovada.
3. Tickets abaixo do limiar de confiança devem ser enviados para revisão humana ou classificados como “não determinado”.
4. A taxonomia oficial deve ter versão e histórico de alteração.
5. A classificação humana deve ter prioridade sobre rótulos automáticos no conjunto de treinamento.
6. Um cluster descoberto não se torna automaticamente um motivo oficial. Deve passar por auditoria e aprovação.
7. A análise de assunto incorreto deve comparar assunto/categoria de abertura com motivo real validado, não apenas com a previsão do modelo.
8. A qualidade da descrição deve ser avaliada por critérios explícitos: contexto, sintoma, sistema/funcionalidade, mensagem de erro, ação realizada e resultado esperado. Não penalizar descrições curtas quando forem suficientes.
9. Recomendações devem apresentar:
   - problema observado;
   - evidências e quantidade de tickets;
   - período analisado;
   - impacto operacional associado;
   - ação sugerida;
   - nível de confiança;
   - necessidade de validação humana.
10. Correlação não é causalidade. O sistema pode apontar associação entre motivo e atraso, mas não afirmar que o motivo causou o atraso sem evidência adicional.
11. Não classificar um ticket como “travamento de sistema” apenas porque ficou parado. Diferenciar falha técnica reportada, ausência de movimentação e demora operacional.
12. Recomendações não devem executar alterações em sistemas ou processos automaticamente. A decisão é do responsável humano.

### Exemplos de recomendações

| Padrão detectado | Evidência necessária | Recomendação possível |
|---|---|---|
| Muitos tickets sobre a mesma funcionalidade | Motivo validado e série temporal | Investigar a funcionalidade e avaliar correção |
| Assunto genérico com motivo específico | Comparação assunto original × motivo validado | Melhorar opções do formulário |
| Descrições frequentemente incompletas | Auditoria textual com critérios explícitos | Incluir campos orientadores no formulário |
| Motivo associado a muitas reaberturas | Histórico de status e motivo validado | Revisar critério de resolução e validação com usuário |
| Motivo com alto tempo de espera | Eventos de atribuição e movimentação | Investigar fila, capacidade e fluxo |
| Novo assunto emergente | Cluster coerente e validação humana | Avaliar inclusão na taxonomia |

## 6. Funcionalidades e componentes a reutilizar

| Componente atual | Decisão | Ação |
|---|---|---|
| `dashboard/data.py` | Reutilizar e refatorar | Manter engine e loaders; remover duplicações; padronizar consultas |
| `dashboard/components.py` | Reutilizar | Preservar KPIs, tabelas, cards, alertas e exportação; padronizar estilos |
| `dashboard/theme.py` | Reutilizar | Manter tema global e consolidar tokens visuais |
| `dashboard/lucide.py` | Reutilizar | Manter ícones |
| `dashboard/components_grafo.py` | Reutilizar e refatorar | Manter grafos; remover conexão direta SQLite e usar engine compartilhada |
| `dashboard/auth.py` | Reutilizar | Preservar autenticação; revisar proteção e configuração |
| `dashboard/filters.py` | Refatorar | Transformar em filtros comuns configuráveis por página; não aplicar data de criação a todas as análises |
| `dashboard/views/sla.py` | Reutilizar | Migrar para a página SLA + Reincidência |
| `dashboard/views/reincidencia.py` | Reutilizar | Preservar detector de reabertura; revisar transições e denominadores |
| `dashboard/views/produtividade.py` | Reutilizar parcialmente | Preservar agregações úteis; substituir ranking simplista por tempos e contexto |
| `dashboard/views/roteamento.py` | Reutilizar | Integrar à área Produtividade + Roteamento |
| `dashboard/views/tendencias.py` | Reutilizar parcialmente | Preservar consultas e gráficos válidos; reconstruir experiência BI |
| `dashboard/views/relatorios.py` | Reutilizar componentes | Incorporar exportações às áreas; remover página isolada se não houver função própria |
| `src/utils_sla.py` | Preservar | Centralizar cálculo e testar regras de calendário |
| `scripts/consultas_roteamento.py` | Avaliar reutilização | Consolidar consultas de fluxo em serviços/repositórios |
| `dados/schema.sql` e migrations | Preservar | Evoluir por migrations; não alterar banco manualmente |

## 7. Páginas a consolidar, arquivar ou retirar do menu

| Página atual | Destino proposto | Observação |
|---|---|---|
| SLA | SLA + Reincidência | Consolidar com Reincidência |
| Reincidência | SLA + Reincidência | Preservar detecção por histórico |
| Produtividade | Produtividade + Roteamento | Expandir para tempos por responsável/área |
| Roteamento | Produtividade + Roteamento | Preservar grafos e histórico |
| Tendências | Tendências / BI | Reformular para reuniões gerenciais |
| Visão Geral | Absorver no BI ou tela inicial | Remover se duplicar KPIs |
| Tempo de Resposta | Absorver em Produtividade + Roteamento | Manter cálculos úteis |
| Backlog | Absorver em SLA e Produtividade | Manter conceito e indicadores de aging/espera |
| Diagnóstico | Retirar como página independente | Preservar regras úteis no domínio se ainda alimentarem alertas |
| Relatórios | Incorporar exportação às áreas | Manter geradores úteis; retirar menu isolado se redundante |
| Validação de Motivos / Monitoramento | Integrar à Inteligência ou manter como ferramentas administrativas | Depende da confirmação dos arquivos da Fase 3 |

**Regra para remoção:** primeiro migrar a funcionalidade, criar teste de equivalência, validar com usuários e só depois excluir o módulo antigo. Não apagar código por nome de página sem verificar dependências.

## 8. Arquitetura técnica recomendada

Separar o dashboard em quatro responsabilidades:

1. **Apresentação (views):** componentes Streamlit, filtros de tela, gráficos e tabelas. Não deve conter SQL nem regras de cálculo complexas.
2. **Serviços de domínio/analytics:** cálculos de SLA, reabertura, permanência, roteamento, comparativos e inteligência.
3. **Repositórios/acesso a dados:** consultas SQL parametrizadas, leitura de tickets, movimentações, mensagens, analistas, áreas e dados do MLP.
4. **Banco e pipeline:** coleta, enriquecimento, persistência, migrations e histórico.

### Estrutura de pastas sugerida

```text
dashboard/
  app.py
  config.py
  auth.py
  theme.py
  filters/
    common.py
    sla.py
    produtividade.py
    bi.py
    inteligencia.py
  components/
    kpis.py
    tables.py
    charts.py
    graphs.py
    exports.py
  data/
    connection.py
    tickets_repository.py
    movements_repository.py
    messages_repository.py
    analytics_repository.py
    ml_repository.py
  services/
    sla_service.py
    reopening_service.py
    productivity_service.py
    routing_service.py
    trends_service.py
    ticket_intelligence_service.py
  views/
    sla_reincidencia.py
    produtividade_roteamento.py
    tendencias_bi.py
    inteligencia_tickets.py
```

A estrutura é uma proposta de destino, não uma exigência de renomear tudo em um único commit. A migração pode ser incremental. Evitar criar uma camada genérica sem necessidade; cada módulo deve ter responsabilidade clara.

## 9. Requisitos do sistema

### 9.1 Requisitos funcionais (RF)

| ID | Requisito |
|---|---|
| RF-01 | O dashboard deve apresentar somente as quatro áreas funcionais definidas, além de navegação administrativa estritamente necessária. |
| RF-02 | A área SLA deve calcular e detalhar cumprimento, atraso, risco e ausência de previsão válida. |
| RF-03 | A área SLA deve identificar reaberturas usando o histórico de transições de status. |
| RF-04 | O sistema deve diferenciar tickets reabertos de quantidade de eventos de reabertura. |
| RF-05 | A área Produtividade deve permitir pesquisa por analista, área, período, assunto e ID do ticket. |
| RF-06 | O sistema deve calcular tempo até primeira ação, permanência por responsável/área e intervalos sem movimentação, quando os eventos permitirem. |
| RF-07 | O sistema deve apresentar grafo de roteamento e linha do tempo de ticket individual. |
| RF-08 | A área BI deve comparar períodos equivalentes e apresentar gráficos, tabelas e variações. |
| RF-09 | O BI deve permitir detalhar e exportar os dados que compõem os indicadores. |
| RF-10 | A Inteligência deve classificar motivos, detectar temas recorrentes e acompanhar temas emergentes. |
| RF-11 | A Inteligência deve sinalizar possíveis problemas na qualidade do assunto e da descrição, com critérios explicáveis. |
| RF-12 | A Inteligência deve cruzar temas com SLA, reabertura, espera e roteamento quando houver dados suficientes. |
| RF-13 | Recomendações devem conter evidências, período, impacto observado e necessidade de validação. |
| RF-14 | O sistema deve preservar decisões humanas, versões de taxonomia e versões de modelo. |
| RF-15 | Filtros e exportações devem manter consistência entre o que aparece na tela e os dados exportados. |

### 9.2 Requisitos não funcionais (RNF)

| ID | Requisito |
|---|---|
| RNF-01 | As consultas devem funcionar no banco configurado (SQLite local e PostgreSQL/Neon/Railway, conforme ambiente). |
| RNF-02 | Consultas devem ser parametrizadas; não concatenar entrada de usuário em SQL. |
| RNF-03 | A aplicação deve manter autenticação e acesso restrito. |
| RNF-04 | Dados pessoais devem ser minimizados e anonimizados em exportações e telas compartilhadas. |
| RNF-05 | O dashboard deve usar cache com invalidação previsível após atualização do pipeline. |
| RNF-06 | Indicadores devem ser reproduzíveis, documentados e testáveis. |
| RNF-07 | As páginas devem apresentar estados vazios, erros de dados e ausência de histórico sem falhar. |
| RNF-08 | A interface deve manter padrão visual, responsividade e legibilidade em apresentações. |
| RNF-09 | Alterações de banco devem ocorrer por migrations versionadas. |
| RNF-10 | Logs não devem expor senhas, tokens, CPF ou conteúdo pessoal desnecessário. |

## 10. Modelo de dados e necessidades de informação

### 10.1 Tabelas existentes a preservar

O `schema.sql` do ZIP contém:

- `tickets`: estado atual e dados principais;
- `movimentacoes`: histórico de status;
- `mensagens`: mensagens, encaminhamentos e áreas;
- `analistas`: metadados da equipe;
- `areas`: áreas padronizadas;
- `snapshots`: controle de execuções do pipeline.

Essas tabelas são essenciais para as quatro áreas. Não remover histórico de movimentações ou mensagens durante a limpeza.

### 10.2 Campos importantes por área

| Área | Dados necessários |
|---|---|
| SLA + Reincidência | ID, criado_data, previsao, data_resolvido, prioridade, categoria, status, histórico de transições |
| Produtividade + Roteamento | ID, autor, responsável, área origem/destino, data/hora do evento, tipo de evento, status anterior/novo |
| Tendências / BI | Datas de criação/resolução/evento, categoria, prioridade, status, área, responsável, motivo |
| Inteligência | Título/assunto original, descrição, mensagens anonimizadas, categoria, motivo real, rótulo validado, confiança, versão do modelo |

### 10.3 Evoluções de dados a avaliar

Antes de criar novas tabelas, verificar se os dados já existem no banco atual. Se não existirem, avaliar migrations para:

- resultados de classificação por ticket e versão de modelo;
- decisões de validação humana;
- versões da taxonomia;
- recomendações geradas e status de revisão;
- eventos normalizados de atribuição/área, caso as mensagens atuais não representem esse histórico de forma confiável.

Não duplicar dados que já possam ser derivados de `movimentacoes` e `mensagens`. Definir a fonte de verdade para cada evento.

## 11. Regras transversais e cuidados de interpretação

1. **Tempo sem movimentação não é automaticamente tempo de trabalho de um analista.**
2. **Volume não é produtividade isoladamente.** Considerar complexidade, área, situação e tempo.
3. **Assunto previsto pelo modelo não é rótulo confirmado.** Diferenciar classificação automática e validação humana.
4. **Correlação não é causalidade.** Recomendações devem ser apresentadas como hipóteses fundamentadas.
5. **Amostras incompletas não devem gerar indicadores definitivos.** Mostrar cobertura e limitações.
6. **Outliers não devem desaparecer sem explicação.** A visualização pode limitar escalas, mas o detalhe deve continuar acessível.
7. **Status e nomes de áreas devem ser normalizados** sem destruir o valor original capturado.
8. **Datas precisam de timezone e semântica definida.** Registrar qual evento está sendo usado em cada cálculo.
9. **LGPD:** aplicar minimização, controle de acesso e anonimização de nomes, CPF, e-mails, telefones e texto livre em saídas compartilhadas.
10. **Não usar indicadores para avaliação punitiva individual.** A finalidade é identificar gargalos, sobrecarga e oportunidades de melhoria.

## 12. Limpeza do repositório

### 12.1 Remover ou corrigir após validação

- Implementações duplicadas de funções em `dashboard/data.py`.
- Páginas antigas depois que suas funcionalidades estiverem migradas e testadas.
- Código morto, imports não utilizados e estilos repetidos.
- Ponto de entrada duplicado ou não documentado.
- Consultas SQL duplicadas espalhadas por views.
- Caminhos absolutos ou conexões locais embutidas em componentes que deveriam usar a engine comum.

### 12.2 Não remover sem análise

- `src/`: pipeline de coleta, filtragem, persistência, enriquecimento e utilitários.
- `dados/migrations/`: histórico de evolução do banco.
- `dados/schema.sql`: estrutura de referência.
- `scripts/`: automação operacional e manutenção, após classificar scripts ativos e pontuais.
- `tests/`: base de regressão.
- `config/`: configurações e regras operacionais.
- `scripts_treinamento/`: confirmar versão atual e integração com MLP antes de limpar.
- `docs/`: atualizar e consolidar, não apagar indiscriminadamente.

### 12.3 Dados e artefatos que exigem cuidado

O ZIP contém `dados/tickets.db.gz`, planilhas de validação, HTML de clusters e metadados locais em `supabase/.temp/`. Antes de manter esses itens versionados:

- verificar se contêm dados pessoais ou conteúdo de tickets;
- remover bancos reais e relatórios sensíveis do Git;
- manter apenas dados sintéticos/anônimos para testes;
- incluir artefatos gerados no `.gitignore`, salvo quando houver justificativa de versionamento;
- não commitar segredos, credenciais, tokens ou configurações locais;
- preservar cópias seguras antes de qualquer remoção.

## 13. Plano de refatoração recomendado

### Etapa 0 — Segurança e baseline

1. Criar branch de refatoração.
2. Fazer backup do banco e dos artefatos necessários.
3. Registrar versão do ZIP/repositório e confirmar se inclui a Fase 3 do MLP.
4. Executar testes existentes e salvar resultados.
5. Identificar arquivos com dados pessoais e revisar `.gitignore`.

**Critério de aceite:** existe ponto de retorno e baseline documentado.

### Etapa 1 — Limpeza estrutural sem mudança funcional

1. Corrigir a ordem de `st.set_page_config()`.
2. Remover duplicações de loaders.
3. Padronizar acesso ao banco pela engine compartilhada.
4. Corrigir consultas de `components_grafo.py` para não depender diretamente de SQLite.
5. Definir um único ponto de entrada.
6. Organizar constantes, imports e configurações.

**Critério de aceite:** dashboard continua funcionando e testes atuais passam.

### Etapa 2 — Consolidar SLA + Reincidência

1. Migrar as duas views para uma nova view.
2. Extrair cálculo de SLA e detecção de reabertura para serviços.
3. Definir transições válidas e denominadores.
4. Criar linha do tempo e filtros específicos.
5. Testar casos de múltiplas reaberturas, cancelamento, duplicidade e dados ausentes.

**Critério de aceite:** resultados conferem com amostra manual validada.

### Etapa 3 — Consolidar Produtividade + Roteamento

1. Migrar funcionalidades atuais de produtividade e roteamento.
2. Criar pesquisa por nome, área, período, assunto e ID.
3. Construir cálculo de permanência por responsável e área.
4. Preservar grafos e histórico individual.
5. Diferenciar espera, atividade registrada e ausência de movimentação.
6. Criar testes para eventos fora de ordem, duplicados e lacunas.

**Critério de aceite:** para tickets amostrados, linha do tempo e durações conferem com o histórico de origem.

### Etapa 4 — Evoluir Tendências para BI

1. Definir catálogo de indicadores e denominadores.
2. Construir comparativos mês a mês e períodos equivalentes.
3. Criar tabelas com variação absoluta e percentual.
4. Padronizar gráficos e filtros.
5. Incorporar exportações.
6. Validar os números com relatório de referência.

**Critério de aceite:** relatório exportado reproduz os dados filtrados da tela e os comparativos são temporalmente equivalentes.

### Etapa 5 — Integrar Inteligência de Tickets

1. Confirmar e integrar os arquivos reais da Fase 3.
2. Exibir motivos classificados e respectivos níveis de confiança.
3. Integrar taxonomia e clusters aprovados.
4. Construir análise de assunto e descrição.
5. Cruzar motivos com reabertura, SLA, espera e roteamento.
6. Gerar recomendações explicáveis e revisáveis.
7. Preservar fila de validação humana e Active Learning.

**Critério de aceite:** cada recomendação pode ser rastreada até os tickets e métricas que a sustentam.

### Etapa 6 — Remoção final e documentação

1. Retirar do menu as páginas substituídas.
2. Remover arquivos antigos somente após confirmar ausência de dependências.
3. Atualizar documentação, README, arquitetura, regras e roadmap.
4. Atualizar testes e instruções de execução.
5. Validar com usuários e responsáveis pelos indicadores.

**Critério de aceite:** menu contém as quatro áreas; não há regressão funcional; documentação reflete o código real.

## 14. Plano mínimo de testes

### SLA + Reincidência

- Ticket resolvido antes da previsão.
- Ticket resolvido depois da previsão.
- Ticket aberto com previsão vencida.
- Ticket sem previsão.
- Ticket resolvido e reaberto uma vez.
- Ticket reaberto várias vezes.
- Ticket fechado sem reabertura.
- Ticket cancelado ou duplicado.
- Histórico sem movimentações.

### Produtividade + Roteamento

- Ticket com uma atribuição.
- Ticket com várias transferências.
- Ticket que retorna para área anterior.
- Ticket sem evento de atribuição.
- Eventos com timestamps iguais.
- Eventos fora de ordem.
- Lacuna longa sem movimentação.
- Responsável ou área não identificados.

### Tendências / BI

- Mês completo versus mês completo.
- Mês parcial versus mês parcial.
- Período anterior sem registros.
- Categoria sem ocorrências.
- Dados com datas inválidas.
- Exportação com os mesmos filtros da tela.

### Inteligência de Tickets

- Motivo com alta confiança.
- Motivo com baixa confiança.
- Ticket sem texto suficiente.
- Assunto original divergente do motivo validado.
- Cluster novo sem aprovação.
- Recomendação sem evidência suficiente (não deve ser publicada como conclusão).
- Dados pessoais no texto (devem ser anonimizados nas saídas).

## 15. Critérios gerais de aceite

A refatoração será considerada concluída quando:

- o menu apresentar as quatro áreas funcionais definidas;
- as funcionalidades importantes das páginas antigas estiverem preservadas nas novas áreas;
- não houver duplicação de funções de acesso a dados;
- as views não concentrarem regras complexas de negócio;
- filtros usarem a data correta para cada análise;
- grafos e histórico individual continuarem funcionando;
- indicadores tiverem fórmula, denominador, período e fonte documentados;
- recomendações de inteligência apresentarem evidências e incertezas;
- dados sensíveis não forem expostos em relatórios ou arquivos versionados;
- testes de regressão e de domínio passarem;
- documentação e código estiverem alinhados.

## 16. Decisões que precisam ser confirmadas antes da implementação

1. O ZIP enviado é anterior à Fase 3 do MLP? Onde está a versão atual dos arquivos `validacao_motivos.py`, `monitoramento.py` e scripts `07` a `10`?
2. O cálculo oficial do SLA deve continuar usando a previsão do Help360 em dias corridos ou deve passar a usar os prazos por criticidade em dias úteis? A documentação atual descreve ambos como situações diferentes.
3. Quais status exatos representam encerramento e quais representam reabertura? A lista precisa ser validada com o histórico real do Help360.
4. O histórico de mensagens contém eventos confiáveis de atribuição e mudança de área, ou será necessário enriquecer a coleta?
5. A produtividade deve ser analisada por pessoa, por área ou pelas duas dimensões? A recomendação é apresentar ambas, sem ranking punitivo.
6. Quem poderá acessar a Inteligência de Tickets e visualizar textos originais? Recomenda-se limitar texto livre e disponibilizar visões anonimizadas para reuniões.

---

## 17. Recomendação final

Executar a refatoração em etapas, começando pela limpeza estrutural e consolidação de SLA + Reincidência. Em seguida, consolidar Produtividade + Roteamento, reformular Tendências como BI e, por último, integrar a Inteligência de Tickets com o MLP da Fase 3.

A principal regra de engenharia é **não apagar funcionalidades antes de migrá-las, testá-las e validar seus resultados**. O objetivo é reduzir a complexidade do dashboard sem perder histórico, regras de negócio ou capacidade analítica já construída.
