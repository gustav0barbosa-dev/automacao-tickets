### 1.1 Convenções

| Convenção | Padrão |
|---|---|
| Nomes de tabelas | `snake_case`, plural |
| Chaves primárias | `id` (INTEGER) |
| Chaves estrangeiras | `{tabela}_id` |
| Datas | ISO: `YYYY-MM-DD HH:MM:SS` |
| Booleanos | `INTEGER` (0/1); `NULL` = não processado |

### 1.2 Migrations

O schema evolui via arquivos SQL em `dados/migrations/`:

| # | Migration | O que faz |
|---|---|---|
| 001 | `add_colunas_extras.sql` | Adiciona `classificacao`, `area`, `empresa`, `solucao`, `sistema` |
| 002 | `sprint_features.sql` | Adiciona `backlog`, `respondido`, `diagnostico`, `acao_interna`, `pendente_usuario`, `responsavel_empresa` + tabela `analistas` |
| 003 | `add_classificacao.sql` | Reforça `classificacao` |
| 004 | `fix_analistas.sql` | Corrige `analistas.empresa_tipo` |

Aplicar com:

```bash
python scripts/aplicar_migration.py
2. Diagrama Entidade-Relacionamento
text
┌─────────────────┐
│    tickets      │
│  (28 colunas)   │
└────────┬────────┘
         │ 1:N
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
   ┌──────────┐  ┌─────────────┐ ┌──────────┐
   │movimenta-│  │ mensagens   │ │snapshots │
   │  coes    │  │(fluxo)      │ │          │
   └──────────┘  └─────────────┘ └──────────┘

┌─────────────────┐         ┌──────────┐
│   analistas     │         │  areas   │
│  (cadastro de   │         │(cadastro)│
│   pessoas)      │         │          │
└─────────────────┘         └──────────┘

         ▲
         │ usado por
         │
    ┌────┴────┐
    │  Joins  │
    │ lógicos │
    │(por nome)│
    └─────────┘
3. Tabela tickets (28 colunas)
3.1 Colunas Originais
Coluna	Tipo	Descrição
id	INTEGER PK	ID do ticket (Help360)
titulo	TEXT	Título
descricao	TEXT	Descrição (raspada)
categoria	TEXT	Categoria
subcategoria	TEXT	Subcategoria
status	TEXT	Status atual
prioridade	TEXT	Prioridade
responsavel_atual	TEXT	Analista atual
solicitante	TEXT	Quem abriu
criado_data	DATETIME	Data de criação
alterado_data	DATETIME	Última movimentação
previsao	DATETIME	SLA (data prevista)
data_resolvido	DATETIME	Data da resolução
data_1_resolvido	DATETIME	Data do 1º atendimento
snapshot_data	DATE	Última atualização do snapshot
enriquecido	INTEGER	0=pendente, 1=enriquecido, 3=falhou
criado_em	DATETIME	Timestamp de criação do registro
atualizado_em	DATETIME	Timestamp de última atualização
3.2 Colunas Adicionadas (Sprint 1)
Coluna	Tipo	Descrição	Migration
classificacao	TEXT	Incidente, Dúvida, Solicitação	001
area	TEXT	Área responsável (ex: DIPM-SMM)	001
empresa	TEXT	Empresa (ex: DBPE, DTR)	001
solucao	TEXT	Texto da solução dada	001
sistema	TEXT	Sistema afetado (ex: SIGEPREV)	001
3.3 Colunas de Filtros (Sprint 2)
Coluna	Tipo	Descrição	Migration
responsavel_empresa	TEXT	SPPREV, Atlantic, Externo, Outro	002
respondido	INTEGER	1 se está na Tabela Fato com data	002
backlog	INTEGER	1 se ticket virou backlog	002
3.4 Colunas de Diagnóstico (Sprint 2)
Coluna	Tipo	Descrição	Migration
acao_interna	INTEGER	1 se resp == alt; 0 se diferente; NULL se sem movimentação	002
pendente_usuario	INTEGER	1 se status == 'Aguardando confirmação'	002
diagnostico	TEXT	CEN-01..CEN-12, OUTRO, SEM_DADOS	002
4. Tabela analistas (10 colunas)
Cadastro de pessoas com classificação de empresa.

Coluna	Tipo	Descrição
nome	TEXT PK	Nome completo
email	TEXT	Email
area_principal	TEXT	Área principal
perfil	TEXT	Triagem, Resolvedor, Especialista
equipe	TEXT	DIO, SPRO
meta_diaria	INTEGER	Meta de tickets/dia
meta_sla	REAL	Meta de % SLA
ativo	INTEGER	1=ativo, 0=inativo
atualizado_em	DATETIME	Timestamp
empresa_tipo	TEXT	SPPREV, Atlantic, Externo, Outro
Popular com: python scripts/carregar_analistas.py (lê dados/usuario_empresa.xlsx).

Regra de classificação:

python
if '@atlanticsolutions.com.br' in email: return 'Atlantic'
if '@sp.gov.br' in email:                return 'SPPREV'
return 'Outro'
5. Tabela movimentacoes
Histórico de mudanças de status de cada ticket.

Coluna	Tipo	Descrição
id	INTEGER PK	Auto-incremento
ticket_id	INTEGER FK	Referência a tickets.id
data_movimentacao	DATETIME	Quando ocorreu
autor	TEXT	Quem fez a ação
tipo	TEXT	criado, alterado, resolvido, reaberto, historico
de_status	TEXT	Status anterior
para_status	TEXT	Novo status
comentario	TEXT	Comentário
Populado por: Programa5 (baixa o Excel do Help360).

6. Tabela mensagens
Área de mensagens do ticket.

Coluna	Tipo	Descrição
id	INTEGER PK	Auto-incremento
ticket_id	INTEGER FK	Referência
data_hora	DATETIME	Timestamp
autor	TEXT	Quem escreveu
tipo	TEXT	comentario, encaminhamento, sistema
area_origem	TEXT	Área de origem
area_destino	TEXT	Área de destino
analista_destino	TEXT	Analista que recebeu
conteudo	TEXT	Texto
primeira_acao_responsavel	INTEGER	1 se foi a 1ª ação
7. Tabela snapshots
Controle de execuções do pipeline.

Coluna	Tipo	Descrição
id	INTEGER PK	Auto-incremento
data_execucao	DATETIME	Quando rodou
tickets_total	INTEGER	Total na base
tickets_novos	INTEGER	Novos
tickets_atualizados	INTEGER	Atualizados
tickets_mudaram	INTEGER	Que mudaram
tickets_enriquecidos	INTEGER	Enriquecidos via Selenium
tempo_execucao_seg	REAL	Duração
8. Tabela areas
Cadastro de áreas padronizadas.

Coluna	Tipo	Descrição
nome	TEXT PK	Nome
tipo	TEXT	Triagem, Desenvolvimento, etc.
responsavel_area	TEXT	Responsável
ativo	INTEGER	1/0
9. Views
9.1 vw_tempo_resposta
Tempo entre criação e resolução.

sql
SELECT id, categoria, responsavel_atual,
       criado_data, data_1_resolvido, data_resolvido,
       (julianday(data_1_resolvido) - julianday(criado_data)) * 24 AS horas_1a_resposta,
       (julianday(data_resolvido) - julianday(criado_data)) * 24 AS horas_resolucao
FROM tickets WHERE data_resolvido IS NOT NULL;
9.2 vw_sla
Cumprimento de SLA.

sql
SELECT id, categoria, prioridade, previsao, data_resolvido,
       CASE
           WHEN data_resolvido IS NULL THEN 'em_andamento'
           WHEN data_resolvido <= previsao THEN 'cumprido'
           ELSE 'estourado'
       END AS status_sla
FROM tickets WHERE previsao IS NOT NULL;
9.3 vw_nao_retorno
Analistas que demoram a agir.

sql
SELECT analista_destino, COUNT(*) AS tickets_recebidos,
       AVG((julianday(m2.data_hora) - julianday(m.data_hora)) * 24) AS horas_ate_1a_acao
FROM mensagens m
LEFT JOIN mensagens m2 ON m2.ticket_id = m.ticket_id AND m2.autor = m.analista_destino
WHERE m.tipo = 'encaminhamento'
GROUP BY m.analista_destino;
10. Queries Práticas
10.1 Tickets travados SPPREV (> 3 dias, sem ação)
sql
SELECT id, titulo, responsavel_atual, dias_aberto
FROM (
    SELECT id, titulo, responsavel_atual,
           CAST(julianday('now') - julianday(criado_data) AS INTEGER) AS dias_aberto
    FROM tickets
    WHERE status IN ('Em atendimento', 'Aguardando confirmação do usuário')
      AND responsavel_empresa = 'SPPREV'
      AND acao_interna = 1
      AND backlog = 0
      AND (julianday('now') - julianday(criado_data)) > 3
)
ORDER BY dias_aberto DESC;
10.2 Distribuição dos cenários
sql
SELECT diagnostico, COUNT(*) AS qtd
FROM tickets
GROUP BY diagnostico
ORDER BY diagnostico;
10.3 Tickets por tipo de empresa
sql
SELECT responsavel_empresa, COUNT(*) AS qtd
FROM tickets
WHERE responsavel_empresa IS NOT NULL
GROUP BY responsavel_empresa
ORDER BY qtd DESC;
11. Crescimento Estimado
Tabela	Registros/ano	Tamanho/ano
tickets	+50/dia (novos)	~10 MB
movimentacoes	+150/dia	~10 MB
mensagens	+300/dia	~30 MB
analistas	estático (~410)	< 1 MB
snapshots	1/dia	< 1 MB
Total		~50 MB/ano
SQLite suporta até 281 TB — folga gigantesca.

12. Backup e Restauração
Backup semanal
bash
copy dados\tickets.db dados\backup\tickets_YYYYMMDD.db
Restauração
bash
copy dados\backup\tickets_20260901.db dados\tickets.db
Backup automático (sugestão)
Criar scripts/backup.py que roda antes de cada execução do pipeline.

13. Migração Futura para PostgreSQL
Se ultrapassar 500 MB ou 10 usuários simultâneos:

Aspecto	Ação
Exportar	pgloader tickets.db postgresql://...
Tipos	Compatíveis (INTEGER, TEXT, DATETIME)
App	Trocar sqlite3 por psycopg2
Vantagem	Concorrência, índices melhores
Recomendação: só migrar se necessário.

14. LGPD e Privacidade
Campos sensíveis:

tickets.solicitante

tickets.descricao

mensagens.conteudo

Medidas:

Medida	Aplicação
Anonimização	Regex substitui CPF/email/telefone
Controle de acesso	Banco local, sem rede
Retenção	Sugestão: 5 anos
Auditoria	Log de acesso
15. Referências
03_Arquitetura.md

05_Regras_de_Negocio.md

06_Analises_e_Metricas.md

SQLite Documentation