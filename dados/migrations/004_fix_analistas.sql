-- ============================================================
-- 004_fix_analistas.sql
-- ============================================================
-- Adiciona a coluna empresa_tipo se não existir
-- ============================================================

ALTER TABLE analistas ADD COLUMN empresa_tipo TEXT;

CREATE INDEX IF NOT EXISTS idx_analistas_empresa ON analistas(empresa_tipo);