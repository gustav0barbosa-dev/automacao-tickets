# ============================================================
# marcar_respondidos.py
# ============================================================
"""
Marca em `tickets.respondido` quais tickets já foram respondidos
(conforme registrado na tabela fato).

Um ticket é "respondido" se:
    - Tem `Data Respondido` preenchida (não NaT)
    - OU tem qualquer movimentação posterior ao Alterado Data
"""

import sqlite3
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
RESPONDIDOS = Path.home() / 'Downloads' / 'tickets_com_respondido.xlsx'


def main():
    if not RESPONDIDOS.exists():
        print(f'❌ Arquivo não encontrado: {RESPONDIDOS}')
        print('   Rode o Programa0 primeiro.')
        return 1

    print(f'📂 Lendo: {RESPONDIDOS}')
    df_resp = pd.read_excel(RESPONDIDOS)
    df_resp['ID'] = df_resp['ID'].astype(str).str.strip()

    # Só os que têm data preenchida
    ids_respondidos = set(
        df_resp[df_resp['Data Respondido'].notna()]['ID']
    )

    print(f'   {len(ids_respondidos)} tickets com resposta registrada')

    # Reset total + marca
    conn = sqlite3.connect(BANCO)
    conn.execute('UPDATE tickets SET respondido = 0')
    conn.execute('UPDATE tickets SET respondido = 1 WHERE CAST(id AS TEXT) IN ({})'.format(
        ','.join('?' * len(ids_respondidos))
    ), list(ids_respondidos))
    conn.commit()

    total = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
    respondidos = conn.execute('SELECT COUNT(*) FROM tickets WHERE respondido = 1').fetchone()[0]
    conn.close()

    print()
    print(f'✅ {respondidos}/{total} marcados como respondidos')
    print(f'   {total - respondidos} pendentes')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())