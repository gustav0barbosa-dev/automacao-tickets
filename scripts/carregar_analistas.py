# ============================================================
# carregar_analistas.py
# ============================================================
"""
Lê o usuario_empresa.xlsx e popula a tabela `analistas`.
Regra:
    - email termina em @atlanticsolutions.com.br → Atlantic
    - email termina em @sp.gov.br               → SPPREV
    - outro domínio                             → Outro
"""

import sqlite3
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
ORIGEM = RAIZ / 'dados' / 'usuario_empresa.xlsx'


def classificar_empresa(email):
    if not email or pd.isna(email):
        return 'Outro'
    email = str(email).lower()
    if '@atlanticsolutions.com.br' in email:
        return 'Atlantic'
    if '@sp.gov.br' in email:
        return 'SPPREV'
    return 'Outro'


def main():
    if not ORIGEM.exists():
        print(f'❌ Arquivo não encontrado: {ORIGEM}')
        return 1

    print(f'📂 Lendo: {ORIGEM}')
    df = pd.read_excel(ORIGEM)

    print(f'   Colunas: {df.columns.tolist()}')
    print(f'   Total: {len(df)} registros')

    # Normaliza
    df['empresa_tipo'] = df['email'].apply(classificar_empresa)

    # Estatística
    print()
    print('📊 Distribuição por empresa:')
    print(df['empresa_tipo'].value_counts().to_string())

    # Salva no banco
    conn = sqlite3.connect(BANCO)
    conn.execute('DELETE FROM analistas')  # limpa antes

    registros = 0
    for _, row in df.iterrows():
        if pd.isna(row['Usuário']):
            continue
        try:
            conn.execute('''
                INSERT OR REPLACE INTO analistas (nome, email, empresa_tipo)
                VALUES (?, ?, ?)
            ''', (
                str(row['Usuário']).strip(),
                str(row['email']).strip() if pd.notna(row['email']) else None,
                row['empresa_tipo'],
            ))
            registros += 1
        except Exception as e:
            print(f'   ⚠️ Erro em {row["Usuário"]}: {e}')

    conn.commit()
    conn.close()

    print()
    print(f'✅ {registros} analistas carregados na tabela `analistas`')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())