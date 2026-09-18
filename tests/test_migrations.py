# ============================================================
# tests/test_migrations.py
# ============================================================

import sqlite3
import pytest
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
PASTA_MIGRATIONS = RAIZ / 'dados' / 'migrations'


def aplicar_migration_em_banco(conn, caminho_sql):
    """
    Aplica uma migration num banco, tolerando erros de coluna duplicada.
    """
    with open(caminho_sql, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Separa por ; de forma robusta
    statements = []
    buffer = []
    for linha in sql.split('\n'):
        stripped = linha.strip()
        if stripped.startswith('--') or not stripped:
            continue
        buffer.append(linha)
        if stripped.endswith(';'):
            statements.append('\n'.join(buffer))
            buffer = []

    for stmt in statements:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e).lower():
                continue
            # Outros erros: relança
            raise

    conn.commit()


def test_pasta_migrations_existe():
    assert PASTA_MIGRATIONS.exists(), f"Pasta não encontrada: {PASTA_MIGRATIONS}"


def test_migrations_sao_arquivos_sql():
    arquivos = list(PASTA_MIGRATIONS.glob('*.sql'))
    assert len(arquivos) > 0, "Nenhuma migration encontrada"
    for arq in arquivos:
        assert arq.suffix == '.sql'


def test_migrations_tem_numeracao():
    arquivos = sorted(PASTA_MIGRATIONS.glob('*.sql'))
    for arq in arquivos:
        prefixo = arq.stem.split('_')[0]
        assert prefixo.isdigit(), f"Migration sem numeração: {arq.name}"


def test_migration_001_adiciona_colunas(tmp_path):
    """Aplica a migration 001 num banco temporário e verifica colunas."""
    banco = tmp_path / 'test.db'
    conn = sqlite3.connect(banco)
    conn.execute('CREATE TABLE tickets (id INTEGER PRIMARY KEY, titulo TEXT)')
    conn.commit()

    arq = PASTA_MIGRATIONS / '001_add_colunas_extras.sql'
    if not arq.exists():
        pytest.skip("Migration 001 não encontrada")

    aplicar_migration_em_banco(conn, arq)

    cols = [c[1] for c in conn.execute('PRAGMA table_info(tickets)').fetchall()]
    assert 'area' in cols
    assert 'empresa' in cols
    assert 'sistema' in cols

    conn.close()


def test_migration_002_adiciona_sprint_features(tmp_path):
    """Verifica que a migration 002 adiciona as colunas esperadas."""
    banco = tmp_path / 'test.db'
    conn = sqlite3.connect(banco)

    # Cria APENAS a tabela tickets (analistas será criada pela migration)
    conn.execute('CREATE TABLE tickets (id INTEGER PRIMARY KEY, titulo TEXT)')
    conn.commit()

    arq = PASTA_MIGRATIONS / '002_sprint_features.sql'
    if not arq.exists():
        pytest.skip("Migration 002 não encontrada")

    aplicar_migration_em_banco(conn, arq)

    # Verifica colunas em tickets
    cols = [c[1] for c in conn.execute('PRAGMA table_info(tickets)').fetchall()]
    assert 'backlog' in cols
    assert 'respondido' in cols
    assert 'diagnostico' in cols
    assert 'acao_interna' in cols
    assert 'responsavel_empresa' in cols

    # Verifica analistas (criada pela migration)
    cols_a = [c[1] for c in conn.execute('PRAGMA table_info(analistas)').fetchall()]
    assert 'empresa_tipo' in cols_a

    conn.close()