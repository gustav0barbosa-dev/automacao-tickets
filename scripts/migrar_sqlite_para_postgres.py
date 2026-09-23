"""
Migra os dados do SQLite local (dados/tickets.db) para o PostgreSQL do Neon.

Uso:
    python scripts/migrar_sqlite_para_neon.py
"""
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

RAIZ = Path(__file__).resolve().parent.parent
SQLITE_PATH = RAIZ / 'dados' / 'tickets.db'


def obter_database_url():
    """Tenta ler a DATABASE_URL dos secrets do Streamlit ou da env."""
    # 1. Le o .streamlit/secrets.toml manualmente (sem tomllib, para lidar com URL sem aspas)
    secrets_path = RAIZ / '.streamlit' / 'secrets.toml'
    if secrets_path.exists():
        try:
            with open(secrets_path, 'r', encoding='utf-8') as f:
                for linha in f:
                    linha = linha.strip()
                    if linha.startswith('url') and '=' in linha:
                        # Pega o valor apos o '='
                        valor = linha.split('=', 1)[1].strip()
                        # Remove aspas se houver
                        valor = valor.strip('"').strip("'")
                        if valor.startswith('postgresql://') or valor.startswith('postgres://'):
                            return valor
        except Exception as e:
            print(f'AVISO: erro lendo secrets.toml: {e}')

    # 2. Variavel de ambiente
    url = os.environ.get('DATABASE_URL')
    if url:
        return url

    return None


def limpar_url(url):
    """Remove parâmetros problemáticos."""
    return (url
            .replace('&channel_binding=require', '')
            .replace('?channel_binding=require&', '?')
            .replace('?channel_binding=require', ''))


def listar_tabelas_sqlite(conn):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall()]


def migrar_tabela(sqlite_conn, pg_engine, tabela):
    """Lê uma tabela do SQLite e insere no PostgreSQL."""
    print(f'\n📦 Migrando tabela: {tabela}')

    df = pd.read_sql(f'SELECT * FROM {tabela}', sqlite_conn)
    print(f'   └─ {len(df)} registros lidos do SQLite')

    if df.empty:
        print(f'   └─ Tabela vazia, pulando.')
        return 0

    # Limpa a tabela no Postgres
    with pg_engine.begin() as conn:
        try:
            conn.execute(text(f'TRUNCATE TABLE {tabela} RESTART IDENTITY CASCADE'))
            print(f'   └─ Tabela {tabela} limpa no Postgres')
        except Exception as e:
            print(f'   └─ ⚠️ Não foi possível truncar (talvez não exista): {e}')

    # Insere (em chunks para não sobrecarregar)
    try:
        df.to_sql(tabela, pg_engine, if_exists='append', index=False, chunksize=1000)
        print(f'   └─ ✅ {len(df)} registros inseridos no Postgres')
        return len(df)
    except Exception as e:
        print(f'   └─ ❌ Erro ao inserir: {e}')
        return 0


def main():
    print('=' * 60)
    print('MIGRAÇÃO SQLITE → POSTGRESQL (NEON)')
    print('=' * 60)

    # 1. Verifica o SQLite
    if not SQLITE_PATH.exists():
        print(f'❌ SQLite não encontrado: {SQLITE_PATH}')
        return False
    print(f'✅ SQLite: {SQLITE_PATH}')

    # 2. Obtém a URL do Postgres
    url = obter_database_url()
    if not url:
        print('❌ DATABASE_URL não encontrada (.streamlit/secrets.toml ou env)')
        return False
    url = limpar_url(url)
    print(f'✅ Postgres: {url[:60]}...')

    # 3. Conecta no SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)

    # 4. Conecta no Postgres
    try:
        pg_engine = create_engine(url, pool_pre_ping=True)
        with pg_engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('✅ Conexão com Postgres OK')
    except Exception as e:
        print(f'❌ Erro ao conectar no Postgres: {e}')
        return False

    # 5. Lista tabelas
    tabelas = listar_tabelas_sqlite(sqlite_conn)
    print(f'\n📋 Tabelas encontradas no SQLite: {tabelas}')

    # 6. Migra cada tabela
    total = 0
    for tabela in tabelas:
        total += migrar_tabela(sqlite_conn, pg_engine, tabela)

    sqlite_conn.close()
    pg_engine.dispose()

    print()
    print('=' * 60)
    print(f'✅ MIGRAÇÃO CONCLUÍDA — {total} registros migrados')
    print('=' * 60)
    return True


if __name__ == '__main__':
    sucesso = main()
    sys.exit(0 if sucesso else 1)