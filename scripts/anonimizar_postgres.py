"""
Anonimiza dados pessoais JÁ EXISTENTES no Postgres.
Roda DENTRO do Railway (onde a DATABASE_URL aponta para a rede interna).
"""
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# Adiciona src/ ao path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))

from utils_anonimizacao import (
    anonimizar_texto,
    CAMPOS_POR_TABELA,
    contem_dados_pessoais,
)


def obter_url():
    """Lê a URL do Postgres da env var (Railway) ou do secrets (local)."""
    # 1. Env var (Railway)
    url = os.environ.get('DATABASE_URL')
    if url:
        # Limpa parâmetros problemáticos
        url = url.replace('&channel_binding=require', '')
        return url

    # 2. Secrets (local)
    secrets = RAIZ / '.streamlit' / 'secrets.toml'
    if secrets.exists():
        with open(secrets, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if linha.startswith('url') and '=' in linha:
                    valor = linha.split('=', 1)[1].strip().strip('"').strip("'")
                    if valor.startswith('postgresql://'):
                        return valor

    return None


def anonimizar_postgres():
    url = obter_url()
    if not url:
        print('❌ URL do Postgres não encontrada.')
        print('   No Railway, verifique se DATABASE_URL está definida.')
        return False

    print(f'✅ URL: {url[:60]}...')
    print()

    engine = create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout': 30})

    # Testa conexão
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('✅ Conexão OK')
    except Exception as e:
        print(f'❌ Erro ao conectar: {e}')
        return False

    total_afetados = 0

    for tabela, campos in CAMPOS_POR_TABELA.items():
        print(f'\n📦 Tabela: {tabela}')
        for campo in campos:
            try:
                df = pd.read_sql(
                    f'SELECT id, {campo} FROM {tabela} WHERE {campo} IS NOT NULL',
                    engine,
                )
            except Exception as e:
                print(f'   - {campo}: erro ao ler ({e})')
                continue

            if df.empty:
                print(f'   - {campo}: 0 registros')
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
            else:
                print(f'   - {campo}: 0 registros com dados pessoais')

    engine.dispose()
    print()
    print('=' * 60)
    print(f'✅ Postgres: {total_afetados} registros anonimizados')
    print('=' * 60)
    return True


if __name__ == '__main__':
    sucesso = anonimizar_postgres()
    sys.exit(0 if sucesso else 1)