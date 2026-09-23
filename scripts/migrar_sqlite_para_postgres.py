"""
Migra os dados do SQLite local para o PostgreSQL (Railway).
Dropa as tabelas do Postgres e recria com o schema do SQLite.
"""
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

RAIZ = Path(__file__).resolve().parent.parent
SQLITE_PATH = RAIZ / 'dados' / 'tickets.db'

# Tabelas que NAO devem ser migradas (internas do SQLite)
TABELAS_IGNORADAS = ['sqlite_sequence']


def obter_database_url():
    """Le a DATABASE_URL dos secrets (local) ou env (Railway)."""
    # 1. Secrets local
    secrets_path = RAIZ / '.streamlit' / 'secrets.toml'
    if secrets_path.exists():
        try:
            with open(secrets_path, 'r', encoding='utf-8') as f:
                for linha in f:
                    linha = linha.strip()
                    if linha.startswith('url') and '=' in linha:
                        valor = linha.split('=', 1)[1].strip()
                        valor = valor.strip('"').strip("'")
                        if valor.startswith('postgresql://') or valor.startswith('postgres://'):
                            return valor
        except Exception as e:
            print(f'AVISO: erro lendo secrets.toml: {e}')

    # 2. Variavel de ambiente (Railway)
    url = os.environ.get('DATABASE_URL')
    if url:
        return url

    return None


def limpar_url(url):
    return (url
            .replace('&channel_binding=require', '')
            .replace('?channel_binding=require&', '?')
            .replace('?channel_binding=require', ''))


def listar_tabelas_sqlite(conn):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall() if r[0] not in TABELAS_IGNORADAS]


def drop_tabelas_postgres(pg_engine, tabelas):
    """Dropa as tabelas do Postgres (com CASCADE) para recriar do zero."""
    with pg_engine.begin() as conn:
        for tabela in tabelas:
            try:
                conn.execute(text(f'DROP TABLE IF EXISTS {tabela} CASCADE'))
                print(f'   - Tabela {tabela} dropada')
            except Exception as e:
                print(f'   - AVISO: erro dropando {tabela}: {e}')


def migrar_tabela(sqlite_conn, pg_engine, tabela):
    """Le uma tabela do SQLite e insere no PostgreSQL."""
    print(f'\n[MIGRANDO] Tabela: {tabela}')

    df = pd.read_sql(f'SELECT * FROM {tabela}', sqlite_conn)
    print(f'   - {len(df)} registros lidos do SQLite')

    if df.empty:
        print(f'   - Tabela vazia, pulando.')
        return 0

    # Insere em chunks (to_sql cria a tabela se nao existir)
    try:
        df.to_sql(tabela, pg_engine, if_exists='append', index=False, chunksize=500)
        print(f'   - OK: {len(df)} registros inseridos no Postgres')
        return len(df)
    except Exception as e:
        print(f'   - ERRO ao inserir: {e}')
        return 0


def main():
    print('=' * 60)
    print('MIGRACAO SQLITE -> POSTGRESQL')
    print('=' * 60)

    if not SQLITE_PATH.exists():
        print(f'ERRO: SQLite nao encontrado: {SQLITE_PATH}')
        return False
    print(f'OK SQLite: {SQLITE_PATH}')

    url = obter_database_url()
    if not url:
        print('ERRO: DATABASE_URL nao encontrada')
        return False
    url = limpar_url(url)
    print(f'OK Postgres: {url[:60]}...')

    sqlite_conn = sqlite3.connect(SQLITE_PATH)

    # Conecta no Postgres
    try:
        pg_engine = create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout': 15})
        with pg_engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('OK Conexao com Postgres')
    except Exception as e:
        print(f'ERRO ao conectar no Postgres: {e}')
        sqlite_conn.close()
        return False

    # Lista tabelas
    tabelas = listar_tabelas_sqlite(sqlite_conn)
    print(f'\nTabelas encontradas no SQLite: {tabelas}')

    # DROPA as tabelas do Postgres (para recriar com o schema correto)
    print('\n[FASE 1] Dropando tabelas antigas do Postgres...')
    drop_tabelas_postgres(pg_engine, tabelas)

    # MIGRA
    print('\n[FASE 2] Inserindo dados...')
    total = 0
    for tabela in tabelas:
        total += migrar_tabela(sqlite_conn, pg_engine, tabela)

    sqlite_conn.close()
    pg_engine.dispose()

    print()
    print('=' * 60)
    print(f'CONCLUIDO - {total} registros migrados')
    print('=' * 60)
    return True


if __name__ == '__main__':
    sucesso = main()
    sys.exit(0 if sucesso else 1)