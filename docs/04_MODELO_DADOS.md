# 04 — Modelo de Dados

**Documento:** Esquema do Banco de Dados
**Versão:** 2.0
**Público-alvo:** Desenvolvedores, DBAs, Analistas de Dados

---

## 1. Visão Geral

O banco de dados da Automação Help360 é implementado em **SQLite**, armazenado em
um único arquivo:
dados/tickets.db

text

### 1.1 Por que SQLite?

| Critério | Justificativa |
|---|---|
| **Zero configuração** | Não precisa instalar servidor |
| **Portabilidade** | Um arquivo, fácil de mover/fazer backup |
| **Volume adequado** | ~100 MB/ano é tranquilo |
| **Python nativo** | `import sqlite3` sem dependências |
| **Migração futura** | Se crescer, migra para PostgreSQL |

### 1.2 Convenções

| Convenção | Padrão adotado |
|---|---|
| Nomes de tabelas | `snake_case`, plural (`tickets`, `mensagens`) |
| Nomes de colunas | `snake_case`, singular (`ticket_id`, `data_hora`) |
| Chave primária | `id` (INTEGER AUTOINCREMENT) |
| Chave estrangeira | `{tabela}_id` (ex: `ticket_id`) |
| Datas | Formato ISO: `YYYY-MM-DD HH:MM:SS` |
| Booleanos | `INTEGER` (0 = falso, 1 = verdadeiro) |

---

## 2. Diagrama Entidade-Relacionamento
┌─────────────────┐
│ tickets │
│ (cadastro) │
└────────┬────────┘
│ 1:N
├──────────────┬──────────────┬──────────────┐
▼ ▼ ▼ ▼
┌──────────┐ ┌─────────────┐ ┌──────────┐ ┌────────────┐
│movimenta-│ │ mensagens │ │snapshots │ │ resposta_ │
│ coes │ │(fluxo) │ │ │ │ fato │
└──────────┘ └──────┬──────┘ └──────────┘ └────────────┘
│
│ N:1
▼
┌──────────┐ ┌──────────┐
│analistas │ │ areas │
└──────────┘ └──────────┘

text

---

## 3. Tabelas

### 3.1 `tickets`

Cadastro de cada ticket, com estado atual.

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY | ID do ticket (Help360) |
| `titulo` | TEXT | | Título do ticket |
| `descricao` | TEXT | | Descrição completa (raspada) |
| `categoria` | TEXT | | Categoria |
| `subcategoria` | TEXT | | Subcategoria |
| `status` | TEXT | | Status atual |
| `prioridade` | TEXT | | Prioridade |
| `responsavel_atual` | TEXT | | Analista atual |
| `solicitante` | TEXT | | Quem abriu |
| `criado_data` | DATETIME | | Data de criação |
| `alterado_data` | DATETIME | | Última movimentação |
| `previsao` | DATETIME | | SLA (data prevista) |
| `data_resolvido` | DATETIME | | Data da resolução |
| `data_1_resolvido` | DATETIME | | Data do 1º atendimento |
| `snapshot_data` | DATE | | Última atualização |
| `enriquecido` | INTEGER | DEFAULT 0 | Se descrição/mensagens foram raspadas |

**SQL de criação:**

```sql
CREATE TABLE IF NOT EXISTS tickets (
    id                  INTEGER PRIMARY KEY,
    titulo              TEXT,
    descricao           TEXT,
    categoria           TEXT,
    subcategoria        TEXT,
    status              TEXT,
    prioridade          TEXT,
    responsavel_atual   TEXT,
    solicitante         TEXT,
    criado_data         DATETIME,
    alterado_data       DATETIME,
    previsao            DATETIME,
    data_resolvido      DATETIME,
    data_1_resolvido    DATETIME,
    snapshot_data       DATE,
    enriquecido         INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tickets_status      ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_responsavel ON tickets(responsavel_atual);
CREATE INDEX IF NOT EXISTS idx_tickets_alterado    ON tickets(alterado_data);
CREATE INDEX IF NOT EXISTS idx_tickets_enriquecido ON tickets(enriquecido);
3.2 movimentacoes
Histórico de mudanças de status de cada ticket.

Coluna	Tipo	Restrições	Descrição
id	INTEGER	PRIMARY KEY AUTOINCREMENT	Auto-incremento
ticket_id	INTEGER	FK → tickets.id	Referência
data_movimentacao	DATETIME		Quando ocorreu
autor	TEXT		Quem fez a ação
tipo	TEXT		criado, alterado, resolvido, reaberto
de_status	TEXT		Status anterior
para_status	TEXT		Novo status
comentario	TEXT		Comentário (se houver)
SQL:

sql
CREATE TABLE IF NOT EXISTS movimentacoes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id           INTEGER NOT NULL,
    data_movimentacao   DATETIME,
    autor               TEXT,
    tipo                TEXT,
    de_status           TEXT,
    para_status         TEXT,
    comentario          TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

CREATE INDEX IF NOT EXISTS idx_mov_ticket ON movimentacoes(ticket_id);
CREATE INDEX IF NOT EXISTS idx_mov_data   ON movimentacoes(data_movimentacao);
3.3 mensagens
Coração da análise de fluxo. Contém a área de mensagens completa.

Coluna	Tipo	Restrições	Descrição
id	INTEGER	PRIMARY KEY AUTOINCREMENT	Auto-incremento
ticket_id	INTEGER	FK → tickets.id	Referência
data_hora	DATETIME		Timestamp da mensagem
autor	TEXT		Quem escreveu
tipo	TEXT		comentario, encaminhamento, sistema, resolucao
area_origem	TEXT		Área de quem escreveu
area_destino	TEXT		Área de destino (encaminhamento)
analista_destino	TEXT		Analista que recebeu
conteudo	TEXT		Texto da mensagem
primeira_acao_responsavel	INTEGER	DEFAULT 0	Se foi a 1ª ação após receber
SQL:

sql
CREATE TABLE IF NOT EXISTS mensagens (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id                   INTEGER NOT NULL,
    data_hora                   DATETIME,
    autor                       TEXT,
    tipo                        TEXT,
    area_origem                 TEXT,
    area_destino                TEXT,
    analista_destino            TEXT,
    conteudo                    TEXT,
    primeira_acao_responsavel   INTEGER DEFAULT 0,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

CREATE INDEX IF NOT EXISTS idx_msg_ticket ON mensagens(ticket_id);
CREATE INDEX IF NOT EXISTS idx_msg_autor  ON mensagens(autor);
CREATE INDEX IF NOT EXISTS idx_msg_data   ON mensagens(data_hora);
CREATE INDEX IF NOT EXISTS idx_msg_tipo   ON mensagens(tipo);
Uso nas análises:

Calcular tempo até primeira ação

Detectar tickets esquecidos

Mapear caminhos (Triagem → X → Y)

Calcular pulos por ticket

3.4 analistas
Metadados da equipe.

Coluna	Tipo	Restrições	Descrição
nome	TEXT	PRIMARY KEY	Nome completo
email	TEXT		Email
area_principal	TEXT		Área principal de atuação
perfil	TEXT		Triagem, Resolvedor, Especialista
equipe	TEXT		DIO, SPRO
meta_diaria	INTEGER		Meta de tickets/dia
meta_sla	REAL		Meta de % SLA
ativo	INTEGER	DEFAULT 1	Se ainda está na equipe
SQL:

sql
CREATE TABLE IF NOT EXISTS analistas (
    nome            TEXT PRIMARY KEY,
    email           TEXT,
    area_principal  TEXT,
    perfil          TEXT,
    equipe          TEXT,
    meta_diaria     INTEGER,
    meta_sla        REAL,
    ativo           INTEGER DEFAULT 1
);
3.5 areas
Áreas padronizadas.

Coluna	Tipo	Restrições	Descrição
nome	TEXT	PRIMARY KEY	Nome da área
tipo	TEXT		Triagem, Desenvolvimento, Financeiro, Folha
responsavel_area	TEXT		Responsável pela área
ativo	INTEGER	DEFAULT 1	Se ainda existe
SQL:

sql
CREATE TABLE IF NOT EXISTS areas (
    nome                TEXT PRIMARY KEY,
    tipo                TEXT,
    responsavel_area    TEXT,
    ativo               INTEGER DEFAULT 1
);
3.6 snapshots
Controle de execuções do pipeline.

Coluna	Tipo	Restrições	Descrição
id	INTEGER	PRIMARY KEY AUTOINCREMENT	Auto-incremento
data_execucao	DATETIME		Quando rodou
tickets_total	INTEGER		Total de tickets na base
tickets_novos	INTEGER		Tickets novos desde o último
tickets_mudaram	INTEGER		Tickets que mudaram
tickets_enriquecidos	INTEGER		Tickets raspados via Selenium
tempo_execucao_seg	INTEGER		Duração da execução
SQL:

sql
CREATE TABLE IF NOT EXISTS snapshots (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    data_execucao           DATETIME NOT NULL,
    tickets_total           INTEGER,
    tickets_novos           INTEGER,
    tickets_mudaram         INTEGER,
    tickets_enriquecidos    INTEGER,
    tempo_execucao_seg      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_snap_data ON snapshots(data_execucao);
4. Views
4.1 vw_tempo_resposta
Calcula tempo de resposta por ticket.

sql
CREATE VIEW IF NOT EXISTS vw_tempo_resposta AS
SELECT
    t.id,
    t.categoria,
    t.responsavel_atual,
    t.criado_data,
    t.data_1_resolvido,
    t.data_resolvido,
    (julianday(t.data_1_resolvido) - julianday(t.criado_data)) * 24 AS horas_1a_resposta,
    (julianday(t.data_resolvido) - julianday(t.criado_data)) * 24   AS horas_resolucao
FROM tickets t
WHERE t.data_resolvido IS NOT NULL;
4.2 vw_nao_retorno
Identifica analistas que demoram a dar retorno.

sql
CREATE VIEW IF NOT EXISTS vw_nao_retorno AS
SELECT
    m.analista_destino AS analista,
    COUNT(*) AS tickets_recebidos,
    AVG((julianday(m2.data_hora) - julianday(m.data_hora)) * 24) AS horas_ate_1a_acao,
    SUM(CASE
        WHEN (julianday(m2.data_hora) - julianday(m.data_hora)) > 48
        THEN 1 ELSE 0
    END) AS tickets_esquecidos
FROM mensagens m
LEFT JOIN mensagens m2
    ON m2.ticket_id = m.ticket_id
    AND m2.autor = m.analista_destino
    AND m2.data_hora > m.data_hora
WHERE m.tipo = 'encaminhamento'
  AND m.analista_destino IS NOT NULL
GROUP BY m.analista_destino;
4.3 vw_sla
Calcula cumprimento de SLA.

sql
CREATE VIEW IF NOT EXISTS vw_sla AS
SELECT
    t.id,
    t.categoria,
    t.prioridade,
    t.previsao,
    t.data_resolvido,
    CASE
        WHEN t.data_resolvido IS NULL THEN 'em_andamento'
        WHEN t.data_resolvido <= t.previsao THEN 'cumprido'
        ELSE 'estourado'
    END AS status_sla
FROM tickets t
WHERE t.previsao IS NOT NULL;
5. Queries de Exemplo
5.1 Tempo médio de resposta por categoria
sql
SELECT
    categoria,
    COUNT(*) AS total,
    ROUND(AVG(horas_resolucao), 2) AS horas_medias,
    ROUND(AVG(horas_1a_resposta), 2) AS horas_1a_resposta
FROM vw_tempo_resposta
GROUP BY categoria
ORDER BY horas_medias DESC;
5.2 SLA por responsável
sql
SELECT
    responsavel_atual,
    COUNT(*) AS total,
    SUM(CASE WHEN status_sla = 'cumprido' THEN 1 ELSE 0 END) AS cumpridos,
    ROUND(
        100.0 * SUM(CASE WHEN status_sla = 'cumprido' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS percentual_sla
FROM vw_sla
GROUP BY responsavel_atual
ORDER BY percentual_sla DESC;
5.3 Tickets atualmente "esquecidos" (> 2 dias sem ação)
sql
SELECT
    t.id,
    t.titulo,
    t.responsavel_atual,
    t.alterado_data,
    CAST((julianday('now') - julianday(t.alterado_data)) AS INTEGER) AS dias_parado
FROM tickets t
WHERE t.status NOT IN ('Resolvido', 'Fechado')
  AND (julianday('now') - julianday(t.alterado_data)) > 2
ORDER BY dias_parado DESC;
5.4 Roteamento: caminho mais comum
sql
SELECT
    m1.area_origem  AS origem,
    m1.area_destino AS destino,
    COUNT(*) AS quantidade
FROM mensagens m1
WHERE m1.tipo = 'encaminhamento'
GROUP BY m1.area_origem, m1.area_destino
ORDER BY quantidade DESC
LIMIT 20;
6. Crescimento Estimado
Tabela	Registros/dia	Registros/ano	Tamanho/ano
tickets	~50	~18.000	~10 MB
movimentacoes	~150	~55.000	~10 MB
mensagens	~300	~110.000	~30 MB
analistas	0 (estático)	~30	< 1 MB
areas	0 (estático)	~10	< 1 MB
snapshots	1	~250	< 1 MB
Total			~50 MB/ano
Projeção: em 5 anos, ~250 MB. SQLite suporta até 281 TB, então há
folga gigantesca.

7. Backup e Restauração
7.1 Backup
bash
# Backup simples (copiar arquivo)
copy dados\tickets.db dados\backup\tickets_20260914.db
Frequência recomendada: semanal ou após grandes cargas.

7.2 Restauração
bash
copy dados\backup\tickets_20260901.db dados\tickets.db
7.3 Backup automático (sugestão)
Criar um Programa_backup.py que roda antes de cada execução do pipeline:

python
import shutil
from datetime import datetime

data = datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy('dados/tickets.db', f'dados/backup/tickets_{data}.db')
8. Migração para PostgreSQL (futuro)
Se o volume crescer ou surgir necessidade de acesso concorrente:

Aspecto	Ação
Exportar	pgloader tickets.db postgresql://...
Schema	Compatível (mesmos tipos)
Aplicação	Trocar sqlite3 por psycopg2
Vantagem	Concorrência, índices melhores
Desvantagem	Precisa de servidor
Recomendação: só migrar se ultrapassar 500 MB ou 10 usuários simultâneos.

9. LGPD e Privacidade
Campos que podem conter dados pessoais:

tickets.solicitante

tickets.descricao

mensagens.conteudo

Medidas:

Medida	Aplicação
Anonimização em relatórios	Substituir CPF/email por <CPF> / <EMAIL>
Controle de acesso	Banco apenas local (sem rede)
Retenção	Definir política (ex: 5 anos)
Auditoria	Log de quem acessa o quê
Ver 05_Regras_de_Negocio.md.

10. Referências
03_Arquitetura.md

05_Regras_de_Negocio.md

06_Analises_e_Metricas.md

SQLite Documentation