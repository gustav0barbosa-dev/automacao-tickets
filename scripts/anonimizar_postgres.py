"""
Anonimiza dados pessoais JÁ EXISTENTES no Postgres.
Versão OTIMIZADA: processa em lote (não 1 por 1).
"""
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))

from utils_anonimizacao import (
    anonimizar_texto,
    CAMPOS_POR_TABELA,
    contem_dados_pessoais,
)

# Tamanho do batch (quantos registros por vez)
BATCH_SIZE = 500
PRINT_INTERVAL = 1000


def obter_url():
    url = os.environ.get('DATABASE_URL')
    if url:
        return url.replace('&channel_binding=require', '')
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


def anonimizar_campo(engine, tabela, campo):
    """Anonimiza um campo em lote."""
    print(f'   - {campo}: lendo...', end='', flush=True)

    # Lê TUDO de uma vez
    try:
        df = pd.read_sql(
            f'SELECT id, {campo} FROM {tabela} WHERE {campo} IS NOT NULL',
            engine,
        )
    except Exception as e:
        print(f' ERRO: {e}')
        return 0

    if df.empty:
        print(' 0 registros')
        return 0

    print(f' {len(df)} lidos, filtrando...', end='', flush=True)

    # Filtra localmente (rápido — feito em Python)
    mask = df[campo].apply(contem_dados_pessoais)
    df_filtrado = df[mask].copy()

    if df_filtrado.empty:
        print(f' 0 com dados pessoais')
        return 0

    print(f' {len(df_filtrado)} com dados pessoais, anonimizando...', end='', flush=True)

    # Anonimiza localmente
    df_filtrado['novo_valor'] = df_filtrado[campo].apply(anonimizar_texto)

    # Remove os que não mudaram
    df_filtrado = df_filtrado[df_filtrado[campo] != df_filtrado['novo_valor']]

    if df_filtrado.empty:
        print(f' 0 alterações reais')
        return 0

    total = len(df_filtrado)
    print(f' {total} para atualizar, enviando em lotes...')

    # UPDATE em batch
    atualizados = 0
    for i in range(0, total, BATCH_SIZE):
        batch = df_filtrado.iloc[i:i + BATCH_SIZE]
        params = [
            {'val': row['novo_valor'], 'id': row['id']}
            for _, row in batch.iterrows()
        ]

        with engine.begin() as conn:
            conn.execute(
                text(f'UPDATE {tabela} SET {campo} = :val WHERE id = :id'),
                params,
            )
        atualizados += len(params)

        if atualizados % PRINT_INTERVAL < BATCH_SIZE:
            print(f'      ... {atualizados}/{total}')

    print(f'      ✅ {atualizados} atualizados')
    return atualizados


def anonimizar_postgres():
    url = obter_url()
    if not url:
        print('❌ URL do Postgres não encontrada.')
        return False

    print(f'✅ URL: {url[:60]}...')
    print()

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={'connect_timeout': 30},
        pool_size=1,
        max_overflow=0,
    )

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
                afetados = anonimizar_campo(engine, tabela, campo)
                total_afetados += afetados
            except Exception as e:
                print(f'   - {campo}: ERRO — {e}')

    engine.dispose()
    print()
    print('=' * 60)
    print(f'✅ Postgres: {total_afetados} registros anonimizados')
    print('=' * 60)
    return True


if __name__ == '__main__':
    sucesso = anonimizar_postgres()
    sys.exit(0 if sucesso else 1)