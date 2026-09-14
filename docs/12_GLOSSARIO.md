# 12 — Glossário

**Documento:** Glossário de Termos
**Versão:** 2.0
**Público-alvo:** Todos os envolvidos

---

## 1. Termos de Domínio (Help360)

| Termo | Definição |
|---|---|
| **Help360** | Sistema de gestão de chamados da SPPREV |
| **Ticket** | Chamado registrado no Help360 |
| **Analista** | Pessoa que trata os tickets |
| **Área** | Setor responsável por uma categoria de ticket |
| **Encaminhamento** | Transferência de um ticket entre áreas |
| **Reabertura** | Quando um ticket "Resolvido" volta para "Em atendimento" |
| **Solicitante** | Pessoa que abriu o ticket |
| **SLA** | Service Level Agreement — prazo acordado para resolução |
| **Previsão** | Data limite para resolução (SLA do ticket) |
| **Prioridade** | Urgência do ticket (Alta, Média, Baixa) |
| **Categoria** | Classificação do ticket (ex: Java, Folha, Financeiro) |
| **Subcategoria** | Refinamento da categoria |

---

## 2. Termos do Projeto

| Termo | Definição |
|---|---|
| **Pipeline** | Sequência automatizada de etapas |
| **Tabela fato** | Planilha manual com respostas dos tickets |
| **Acompanhamento** | Arquivo final com tickets que devem ser abertos |
| **Data Respondido** | Data da última resposta na Tabela fato |
| **Alterado Data** | Data da última movimentação no Help360 |
| **Área de mensagens** | Histórico de fluxo do ticket (scraped) |
| **Enriquecimento** | Processo de raspar descrição + mensagens |
| **Snapshot** | Estado dos dados em uma data específica |
| **Dry-run** | Execução simulada que não abre navegador |
| **Pipeline** | Conjunto de programas que processam dados em etapas |

---

## 3. Termos Técnicos — Python

| Termo | Definição |
|---|---|
| **Pandas** | Biblioteca de manipulação de dados |
| **DataFrame** | Tabela bidimensional do Pandas |
| **NaT** | Not-a-Time — valor nulo de data do Pandas |
| **NaN** | Not-a-Number — valor nulo numérico |
| **Selenium** | Biblioteca de automação de navegador |
| **WebDriver** | Componente que controla o navegador |
| **ChromeDriver** | Driver específico do Chrome |
| **openpyxl** | Biblioteca para ler/escrever Excel |
| **pytest** | Framework de testes |
| **sqlite3** | Módulo nativo do Python para SQLite |

---

## 4. Termos Técnicos — Banco de Dados

| Termo | Definição |
|---|---|
| **SQLite** | Banco de dados em arquivo único |
| **Schema** | Estrutura do banco (tabelas, colunas) |
| **Chave primária (PK)** | Identificador único de uma linha |
| **Chave estrangeira (FK)** | Referência a outra tabela |
| **Índice** | Estrutura para acelerar consultas |
| **View** | Consulta salva como tabela virtual |
| **Query** | Consulta SQL |
| **Migration** | Alteração versionada do schema |

---

## 5. Termos Técnicos — Web

| Termo | Definição |
|---|---|
| **Scraping** | Extração automatizada de dados de sites |
| **XPATH** | Linguagem de seleção de elementos HTML |
| **CSS Selector** | Alternativa ao XPATH |
| **Headless** | Navegador sem interface gráfica |
| **Selenium Grid** | Execução distribuída de testes |
| **Webhook** | Notificação HTTP enviada a um endpoint |

---

## 6. Termos de Análise

| Termo | Definição |
|---|---|
| **SLA** | Acordo de nível de serviço |
| **Backlog** | Fila de tickets não resolvidos |
| **Aging** | Idade média dos tickets abertos |
| **Throughput** | Taxa de resolução (tickets/dia) |
| **Lead Time** | Tempo total do pedido à entrega |
| **Cycle Time** | Tempo de trabalho efetivo |
| **Gargalo** | Ponto onde o fluxo é mais lento |
| **Pulo** | Encaminhamento entre áreas |
| **Reincidência** | Retorno de um problema já tratado |
| **Sazonalidade** | Variação periódica no volume |
| **YoY** | Year over Year — comparativo anual |

---

## 7. Termos de NLP

| Termo | Definição |
|---|---|
| **NLP** | Natural Language Processing |
| **TF-IDF** | Técnica de vetorização de texto |
| **Clustering** | Agrupamento de itens similares |
| **BERTimbau** | BERT pré-treinado em português |
| **NER** | Named Entity Recognition |
| **Tokenização** | Quebra de texto em unidades |
| **Similaridade de cosseno** | Medida de similaridade entre textos |
| **Fine-tuning** | Ajuste fino de modelo pré-treinado |

---

## 8. Termos de LGPD

| Termo | Definição |
|---|---|
| **LGPD** | Lei Geral de Proteção de Dados |
| **Dado pessoal** | Informação que identifica alguém |
| **Dado sensível** | Categoria especial (saúde, biometria) |
| **Anonimização** | Remover identificação de dados |
| **Pseudonimização** | Substituir identificação por código |
| **Titular** | Pessoa a quem se referem os dados |
| **Controlador** | Quem decide sobre o tratamento |
| **Operador** | Quem trata dados em nome do controlador |

---

## 9. Siglas

| Sigla | Significado |
|---|---|
| **DIO** | Diretoria de Investimentos e Operações (exemplo) |
| **SPRO** | (sigla do setor) |
| **SPPREV** | São Paulo Previdência |
| **SLA** | Service Level Agreement |
| **RF** | Requisito Funcional |
| **RNF** | Requisito Não Funcional |
| **UC** | Caso de Uso |
| **ADR** | Architecture Decision Record |
| **SRS** | Software Requirements Specification |
| **SDD** | Software Design Document |
| **E2E** | End-to-End |
| **CI/CD** | Continuous Integration / Continuous Deployment |

---

## 10. Status de Ticket

| Status | Significado |
|---|---|
| **Aberto** | Recém-criado, ainda não atribuído |
| **Em atendimento** | Atribuído a um analista |
| **Aguardando confirmação do usuário** | Resposta enviada, aguardando retorno |
| **Resolvido** | Resolvido, mas ainda pode ser reaberto |
| **Fechado** | Encerrado definitivamente |
| **Cancelado** | Não requer ação |
| **Duplicado** | Já tratado em outro ticket |

---

## 11. Perfis de Analista

| Perfil | Descrição |
|---|---|
| **Triagem** | Recebe tickets e encaminha para área correta |
| **Resolvedor** | Resolve tickets dentro da sua área |
| **Especialista** | Trata casos complexos |
| **Atendimento direto** | Atende o solicitante sem intermediários |

---

## 12. Convenções do Projeto

| Convenção | Padrão |
|---|---|
| Nomes de arquivos Python | `snake_case.py` |
| Nomes de classes | `PascalCase` |
| Nomes de funções | `snake_case` |
| Constantes | `UPPER_SNAKE_CASE` |
| Tabelas SQLite | `snake_case` plural |
| Colunas SQLite | `snake_case` singular |

---

## 13. Referências

- [01_Visao_e_Escopo.md](01_VISAO_E_ESCOPO.md)
- [02_Requisitos.md](02_REQUISITOS.md)
- [05_Regras_de_Negocio.md](05_REGRAS_DE_NEGOCIO.md)
- [Lei Geral de Proteção de Dados](https://www.gov.br/cidadania/pt-br/acesso-a-informacao/lgpd)
"""
