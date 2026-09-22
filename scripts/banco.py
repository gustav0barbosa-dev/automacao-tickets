# ============================================================
# banco.py — Exporta as tabelas do SQLite para CSV
# ============================================================

import sqlite3
import pandas as pd
from pathlib import Path


# Caminho absoluto (funciona de qualquer pasta)
RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
PASTA_SAIDA = RAIZ / 'dados' / 'export_csv'


def main():
    print('=' * 60)
    print('EXPORTAR SQLITE → CSV')
    print('=' * 60)
    print(f'📁 Banco: {BANCO}')

    if not BANCO.exists():
        print(f'❌ Banco não encontrado: {BANCO}')
        return 1

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    print(f'📁 Saída: {PASTA_SAIDA}')
    print()

    conn = sqlite3.connect(BANCO)

    # Lista todas as tabelas
    tabelas = [t[0] for t in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]

    print(f'📊 {len(tabelas)} tabela(s) encontrada(s):')

    total_registros = 0

    for tabela in tabelas:
        try:
            df = pd.read_sql(f'SELECT * FROM {tabela}', conn)
            caminho = PASTA_SAIDA / f'{tabela}.csv'
            df.to_csv(caminho, index=False, encoding='utf-8')

            n = len(df)
            total_registros += n
            kb = caminho.stat().st_size / 1024
            print(f'   ✅ {tabela:<20} ({n:>6} registros, {kb:>6.1f} KB)')
        except Exception as e:
            print(f'   ❌ {tabela}: {e}')

    conn.close()

    print()
    print('=' * 60)
    print(f'✅ {total_registros} registros exportados')
    print(f'📁 Arquivos em: {PASTA_SAIDA}')
    print('=' * 60)
    print()
    print('💡 Próximos passos:')
    print('   1. Ir no Neon (console.neon.tech)')
    print('   2. Abrir o SQL Editor')
    print('   3. Criar as tabelas (ver schema SQL)')
    print('   4. Importar os CSVs')

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())