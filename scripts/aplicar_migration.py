# ============================================================
# aplicar_migration.py
# ============================================================
"""
Aplica migrations SQL no banco de dados.
Idempotente: pode rodar várias vezes sem erro.
"""

import os
import sqlite3
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
MIGRATIONS = RAIZ / 'dados' / 'migrations'


def aplicar_arquivo(conn, caminho_sql):
    """Executa um arquivo .sql no banco, ignorando erros de coluna duplicada."""
    print(f'\n📄 Aplicando: {caminho_sql.name}')

    with open(caminho_sql, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Divide por ponto-e-vírgula para aplicar statement a statement
    statements = [s.strip() for s in sql.split(';') if s.strip()]

    for i, stmt in enumerate(statements, 1):
        # Ignora comentários
        if stmt.startswith('--'):
            continue

        try:
            conn.execute(stmt)
            print(f'   ✅ {stmt[:70]}...')
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print(f'   ⏭️  Coluna já existe (pulando)')
            else:
                print(f'   ❌ Erro: {e}')
                raise

    conn.commit()


def main():
    if not BANCO.exists():
        print(f'❌ Banco não encontrado: {BANCO}')
        return 1

    if not MIGRATIONS.exists():
        print(f'⚠️  Pasta de migrations não encontrada: {MIGRATIONS}')
        print('   Criando...')
        MIGRATIONS.mkdir(parents=True)
        return 1

    arquivos = sorted(MIGRATIONS.glob('*.sql'))

    if not arquivos:
        print(f'⚠️  Nenhum arquivo .sql encontrado em {MIGRATIONS}')
        return 1

    print('=' * 60)
    print('APLICANDO MIGRATIONS')
    print('=' * 60)
    print(f'📁 Banco: {BANCO}')
    print(f'📁 Migrations: {MIGRATIONS}')
    print(f'📋 {len(arquivos)} arquivo(s) encontrado(s)')

    conn = sqlite3.connect(BANCO)

    try:
        for arquivo in arquivos:
            aplicar_arquivo(conn, arquivo)

        # Verifica resultado
        print('\n' + '=' * 60)
        print('VERIFICAÇÃO')
        print('=' * 60)

        cols = conn.execute('PRAGMA table_info(tickets)').fetchall()
        print('\nColunas da tabela `tickets`:')
        for col in cols:
            print(f'   • {col[1]:<20} {col[2]}')

    finally:
        conn.close()

    print('\n✅ Migrations aplicadas com sucesso!')
    return 0


if __name__ == '__main__':
    sys.exit(main())