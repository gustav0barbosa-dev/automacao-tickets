-- Colunas para Backlog
ALTER TABLE tickets ADD COLUMN backlog INTEGER DEFAULT 0;

-- Colunas para Atlantic/SPPREV
ALTER TABLE tickets ADD COLUMN responsavel_empresa TEXT;

-- Colunas para "não respondidos"
ALTER TABLE tickets ADD COLUMN respondido INTEGER DEFAULT 0;

-- Colunas para Matriz de Verdade
ALTER TABLE tickets ADD COLUMN acao_interna INTEGER;
ALTER TABLE tickets ADD COLUMN pendente_usuario INTEGER;
ALTER TABLE tickets ADD COLUMN diagnostico TEXT;

-- Tabela de analistas
CREATE TABLE IF NOT EXISTS analistas (
    nome            TEXT PRIMARY KEY,
    email           TEXT,
    empresa_tipo    TEXT,
    atualizado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tickets_backlog   ON tickets(backlog);
CREATE INDEX IF NOT EXISTS idx_tickets_respondido ON tickets(respondido);
CREATE INDEX IF NOT EXISTS idx_tickets_diag      ON tickets(diagnostico);
CREATE INDEX IF NOT EXISTS idx_analistas_email   ON analistas(email);