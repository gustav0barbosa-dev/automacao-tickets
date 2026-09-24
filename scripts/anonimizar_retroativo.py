"""
Anonimiza dados pessoais JÁ EXISTENTES no SQLite e no Postgres.
Uso: python scripts/anonimizar_retroativo.py
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))

from utils_anonimizacao import anonimizar_texto, CAMPOS_POR_TABELA, contem_dados_pessoais

BANCO_SQLITE = RAIZ / 'dados' / 'tickets.db'


def anonimizar_sqlite():
    """Anonimiza o banco SQLite local."""
    print('=' * 60)
    print('ANONIMIZANDO SQLITE')
    print('=' * 60)

    conn = sqlite3.connect(BANCO_SQLITE)
    conn.row_factory = sqlite3.Row

    total_afetados = 0

    for tabela, campos in CAMPOS_POR_TABELA.items():
        print(f'\n📦 Tabela: {tabela}')
        for campo in campos:
            try:
                # Lê todos os valores do campo
                cur = conn.execute(f'SELECT id, {campo} FROM {tabela} WHERE {campo} IS NOT NULL')
                linhas = cur.fetchall()
            except sqlite3.OperationalError:
                # Coluna não existe
                continue

            afetados = 0
            for row in linhas:
                original = row[campo]
                if not contem_dados_pessoais(original):
                    continue

                anonimizado = anonimizar_texto(original)
                if anonimizado != original:
                    conn.execute(
                        f'UPDATE {tabela} SET {campo} = ? WHERE id = ?',
                        (anonimizado, row['id']),
                    )
                    afetados += 1

            if afetados > 0:
                print(f'   - {campo}: {afetados} registros anonimizados')
                total_afetados += afetados

    conn.commit()
    conn.close()

    print(f'\n✅ SQLite: {total_afetados} registros anonimizados')
    return total_afetados


def anonimizar_postgres():
    """Anonimiza o banco Postgres (Neon/Railway)."""
    print('\n' + '=' * 60)
    print('ANONIMIZANDO POSTGRES')
    print('=' * 60)

    # Lê a URL do secrets
    from urllib.parse import urlparse
    secrets_path = RAIZ / '.streamlit' / 'secrets.toml'
    if not secrets_path.exists():
        print('⚠️ secrets.toml não encontrado. Pulando Postgres.')
        return 0

    url = None
    with open(secrets_path, 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if linha.startswith('url') and '=' in linha:
                valor = linha.split('=', 1)[1].strip().strip('"').strip("'")
                if valor.startswith('postgresql://'):
                    url = valor
                    break

    if not url:
        print('⚠️ URL do Postgres não encontrada. Pulando.')
        return 0

    from sqlalchemy import create_engine, text
    engine = create_engine(url, pool_pre_ping=True)

    total_afetados = 0

    for tabela, campos in CAMPOS_POR_TABELA.items():
        print(f'\n📦 Tabela: {tabela}')
        for campo in campos:
            try:
                df = pd.read_sql(f'SELECT id, {campo} FROM {tabela} WHERE {campo} IS NOT NULL', engine)
            except Exception:
                continue

            afetados = 0
            for _, row in df.iterrows():
                original = row[campo]
                if not contem_dados_pessoais(original):
                    continue

                anonimizado = anonimizar_texto(original)
                if anonimizado != original:
                    with engine.begin() as conn:
                        conn.execute(
                            text(f'UPDATE {tabela} SET {campo} = :val WHERE id = :id'),
                            {'val': anonimizado, 'id': row['id']},
                        )
                    afetados += 1

            if afetados > 0:
                print(f'   - {campo}: {afetados} registros anonimizados')
                total_afetados += afetados

    engine.dispose()
    print(f'\n✅ Postgres: {total_afetados} registros anonimizados')
    return total_afetados


def main():
    print('=' * 60)
    print('ANONIMIZAÇÃO RETROATIVA (LGPD)')
    print('=' * 60)
    print()
    print('⚠️  ATENÇÃO: Esta operação MODIFICA o banco permanentemente.')
    print('   Faça backup antes de continuar!')
    print()
    confirmar = input('Continuar? (s/N): ').strip().lower()
    if confirmar != 's':
        print('Cancelado.')
        return

    # Backup
    import shutil
    from datetime import datetime
    backup = BANCO_SQLITE.with_suffix(f'.db.backup-{datetime.now():%Y%m%d-%H%M%S}')
    shutil.copy2(BANCO_SQLITE, backup)
    print(f'📁 Backup: {backup}')
    print()

    # Anonimiza
    total_sqlite = anonimizar_sqlite()
    total_postgres = anonimizar_postgres()

    print()
    print('=' * 60)
    print(f'✅ CONCLUÍDO')
    print(f'   SQLite   : {total_sqlite} registros')
    print(f'   Postgres : {total_postgres} registros')
    print('=' * 60)


if __name__ == '__main__':
    main()