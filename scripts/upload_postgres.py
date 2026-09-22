# ============================================================
# upload_postgres.py
# ============================================================
"""
Sobe os CSVs (exportados do SQLite) para o PostgreSQL do Neon.

Uso:
    set DATABASE_URL=postgresql://...
    python scripts/upload_postgres.py
"""

import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


RAIZ = Path(__file__).resolve().parent.parent
PASTA_CSV = RAIZ / 'dados' / 'export_csv'


def main():
    # 1. Lê a URL do PostgreSQL
    url = os.environ.get('DATABASE_URL')
    if not url:
        print('❌ Variável DATABASE_URL não configurada.')
        print()
        print('   No PowerShell:')
        print('   $env:DATABASE_URL = "postgresql://..."')
        print()
        print('   Ou passe como argumento:')
        print('   python scripts/upload_postgres.py "postgresql://..."')
        if len(sys.argv) > 1:
            url = sys.argv[1]
        else:
            return 1

    print('=' * 60)
    print('UPLOAD SQLITE → POSTGRESQL')
    print('=' * 60)
    print(f'📁 CSVs: {PASTA_CSV}')
    print(f'🔗 URL: {url[:50]}...')
    print()

    if not PASTA_CSV.exists():
        print(f'❌ Pasta não encontrada: {PASTA_CSV}')
        print('   Rode primeiro: python scripts/banco.py')
        return 1

    # 2. Cria engine
    print('🔌 Conectando ao PostgreSQL...')
    engine = create_engine(url)

    # 3. Ordem de importação (respeita FKs)
    ordem = ['areas', 'analistas', 'tickets', 'movimentacoes', 'mensagens', 'snapshots']

    total = 0

    for tabela in ordem:
        caminho = PASTA_CSV / f'{tabela}.csv'
        if not caminho.exists():
            print(f'⏭️  {tabela}.csv não encontrado. Pulando.')
            continue

        print(f'\n📤 Enviando {tabela}...')
        df = pd.read_csv(caminho)
        n = len(df)
        print(f'   {n} registros')

        if n == 0:
            print(f'   ⏭️  Vazio. Pulando.')
            continue

        try:
            # Trata colunas de data
            for col in df.columns:
                if 'data' in col.lower() or 'previsao' in col.lower():
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            # Substitui NaN por None (PostgreSQL aceita NULL)
            df = df.where(pd.notna(df), None)

            # Envia
            df.to_sql(tabela, engine, if_exists='append', index=False, method='multi', chunksize=500)
            print(f'   ✅ {n} registros enviados')
            total += n
        except Exception as e:
            print(f'   ❌ Erro: {e}')

    print()
    print('=' * 60)
    print(f'✅ {total} registros enviados')
    print('=' * 60)


if __name__ == '__main__':
    sys.exit(main())