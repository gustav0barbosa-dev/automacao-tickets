# ============================================================
# verificar_banco.py
# ============================================================
"""
Verifica se as colunas e tabelas novas estão no banco.
"""

import sqlite3
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'


def main():
    print('=' * 60)
    print('VERIFICAÇÃO DO BANCO')
    print('=' * 60)
    print(f'📁 Banco: {BANCO}')
    print()

    if not BANCO.exists():
        print('❌ Banco não encontrado!')
        return

    conn = sqlite3.connect(BANCO)

    # Colunas da tabela tickets
    cols = conn.execute('PRAGMA table_info(tickets)').fetchall()
    nomes = [col[1] for col in cols]

    print(f'📋 Tabela `tickets` tem {len(nomes)} colunas:')
    for nome in nomes:
        print(f'   • {nome}')

    print()
    print('🔍 Verificação das colunas novas:')
    esperadas = [
        'backlog',
        'respondido',
        'diagnostico',
        'acao_interna',
        'pendente_usuario',
        'responsavel_empresa',
        'classificacao',
        'area',
        'empresa',
        'solucao',
        'sistema',
    ]
    for col in esperadas:
        status = '✅' if col in nomes else '❌'
        print(f'   {status} {col}')

    # Tabelas existentes
    print()
    print('🔍 Tabelas existentes:')
    tabelas = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    for t in tabelas:
        print(f'   • {t[0]}')

    # Tabela analistas
    print()
    print('🔍 Verificação da tabela `analistas`:')
    t_analistas = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='analistas'"
    ).fetchone()
    if t_analistas:
        print('   ✅ Tabela `analistas` existe')
        n = conn.execute('SELECT COUNT(*) FROM analistas').fetchone()[0]
        print(f'      Registros: {n}')
    else:
        print('   ❌ Tabela `analistas` NÃO existe')

    # Views
    print()
    print('🔍 Views existentes:')
    views = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
    ).fetchall()
    for v in views:
        print(f'   • {v[0]}')

    conn.close()

    print()
    print('=' * 60)


if __name__ == '__main__':
    main()