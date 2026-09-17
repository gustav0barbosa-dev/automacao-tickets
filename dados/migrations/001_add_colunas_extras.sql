-- ============================================================
-- 001_add_colunas_extras.sql
-- ============================================================
-- Adiciona colunas que já extraímos no enriquecimento mas não
-- estavam sendo persistidas.
--
-- Execução:
--   sqlite3 dados/tickets.db < dados/migrations/001_add_colunas_extras.sql
-- ============================================================

-- Adiciona colunas (ignora erro se já existirem)
ALTER TABLE tickets ADD COLUMN classificacao TEXT;
ALTER TABLE tickets ADD COLUMN area TEXT;
ALTER TABLE tickets ADD COLUMN empresa TEXT;
ALTER TABLE tickets ADD COLUMN solucao TEXT;
ALTER TABLE tickets ADD COLUMN sistema TEXT;
ALTER TABLE tickets ADD COLUMN responsavel_empresa TEXT;
ALTER TABLE tickets ADD COLUMN respondido INTEGER DEFAULT 0;
ALTER TABLE tickets ADD COLUMN diagnostico TEXT;
ALTER TABLE tickets ADD COLUMN acao_interna INTEGER;
ALTER TABLE tickets ADD COLUMN pendente_usuario INTEGER;
ALTER TABLE tickets ADD COLUMN backlog INTEGER DEFAULT 0;

-- Cria índices para filtros futuros
CREATE INDEX IF NOT EXISTS idx_tickets_classificacao ON tickets(classificacao);
CREATE INDEX IF NOT EXISTS idx_tickets_area          ON tickets(area);
CREATE INDEX IF NOT EXISTS idx_tickets_empresa       ON tickets(empresa);