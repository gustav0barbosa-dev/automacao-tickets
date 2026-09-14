-- ============================================================
-- schema.sql - Esquema do banco de dados SQLite
-- ============================================================
-- Automação Help360 - SPPREV
-- Versão: 1.0
--
-- Executar via: sqlite3 dados/tickets.db < dados/schema.sql
-- Ou programaticamente: programas leem este arquivo e executam.
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ============================================================
-- TABELAS
-- ============================================================

-- ------------------------------------------------------------
-- tickets: Cadastro + estado atual de cada ticket
-- ------------------------------------------------------------
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
    enriquecido         INTEGER DEFAULT 0,
    criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tickets_status      ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_responsavel ON tickets(responsavel_atual);
CREATE INDEX IF NOT EXISTS idx_tickets_alterado    ON tickets(alterado_data);
CREATE INDEX IF NOT EXISTS idx_tickets_categoria   ON tickets(categoria);
CREATE INDEX IF NOT EXISTS idx_tickets_enriquecido ON tickets(enriquecido);
CREATE INDEX IF NOT EXISTS idx_tickets_criado      ON tickets(criado_data);

-- ------------------------------------------------------------
-- movimentacoes: Histórico de mudanças de status
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS movimentacoes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id           INTEGER NOT NULL,
    data_movimentacao   DATETIME,
    autor               TEXT,
    tipo                TEXT,
    de_status           TEXT,
    para_status         TEXT,
    comentario          TEXT,
    criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mov_ticket ON movimentacoes(ticket_id);
CREATE INDEX IF NOT EXISTS idx_mov_data   ON movimentacoes(data_movimentacao);

-- ------------------------------------------------------------
-- mensagens: Área de mensagens (fluxo) - Fase 2
-- ------------------------------------------------------------
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
    criado_em                   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_msg_ticket ON mensagens(ticket_id);
CREATE INDEX IF NOT EXISTS idx_msg_autor  ON mensagens(autor);
CREATE INDEX IF NOT EXISTS idx_msg_data   ON mensagens(data_hora);
CREATE INDEX IF NOT EXISTS idx_msg_tipo   ON mensagens(tipo);

-- ------------------------------------------------------------
-- analistas: Metadados da equipe - Fase 2
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analistas (
    nome            TEXT PRIMARY KEY,
    email           TEXT,
    area_principal  TEXT,
    perfil          TEXT,
    equipe          TEXT,
    meta_diaria     INTEGER,
    meta_sla        REAL,
    ativo           INTEGER DEFAULT 1,
    atualizado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- areas: Áreas padronizadas - Fase 2
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS areas (
    nome                TEXT PRIMARY KEY,
    tipo                TEXT,
    responsavel_area    TEXT,
    ativo               INTEGER DEFAULT 1,
    atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- snapshots: Controle de execuções do pipeline
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS snapshots (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    data_execucao           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tickets_total           INTEGER,
    tickets_novos           INTEGER,
    tickets_atualizados     INTEGER,
    tickets_mudaram         INTEGER,
    tickets_enriquecidos    INTEGER,
    tempo_execucao_seg      REAL,
    origem                  TEXT,
    observacao              TEXT
);

CREATE INDEX IF NOT EXISTS idx_snap_data ON snapshots(data_execucao);

-- ============================================================
-- VIEWS
-- ============================================================

-- ------------------------------------------------------------
-- vw_tempo_resposta: Tempo de resposta por ticket
-- ------------------------------------------------------------
DROP VIEW IF EXISTS vw_tempo_resposta;
CREATE VIEW vw_tempo_resposta AS
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

-- ------------------------------------------------------------
-- vw_sla: Cumprimento de SLA
-- ------------------------------------------------------------
DROP VIEW IF EXISTS vw_sla;
CREATE VIEW vw_sla AS
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

-- ------------------------------------------------------------
-- vw_nao_retorno: Analistas que demoram a dar retorno (Fase 2)
-- ------------------------------------------------------------
DROP VIEW IF EXISTS vw_nao_retorno;
CREATE VIEW vw_nao_retorno AS
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

-- ============================================================
-- FIM DO SCHEMA
-- ============================================================