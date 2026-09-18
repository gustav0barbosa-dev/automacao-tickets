# ============================================================
# marcar_empresa_responsavel.py
# ============================================================
"""
Preenche tickets.responsavel_empresa com base na tabela analistas.
"""

import sqlite3
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'


def main():
    conn = sqlite3.connect(BANCO)

    # Pega mapa nome → empresa_tipo
    mapa = dict(conn.execute(
        'SELECT nome, empresa_tipo FROM analistas'
    ).fetchall())

    print(f'📊 {len(mapa)} analistas carregados')

    # Busca todos os tickets
    tickets = conn.execute('''
        SELECT id, responsavel_atual
        FROM tickets
        WHERE responsavel_atual IS NOT NULL
          AND responsavel_atual != ''
    ''').fetchall()

    print(f'📋 {len(tickets)} tickets com responsável')

    # Atualiza
    atualizados = 0
    sem_match = 0

    for tid, resp in tickets:
        # Tenta match exato
        empresa = mapa.get(resp)

        # Se não achou, tenta match normalizado (strip, lower)
        if empresa is None:
            resp_norm = str(resp).strip()
            for nome, tipo in mapa.items():
                if nome.strip().lower() == resp_norm.lower():
                    empresa = tipo
                    break

        if empresa:
            conn.execute(
                'UPDATE tickets SET responsavel_empresa = ? WHERE id = ?',
                (empresa, tid)
            )
            atualizados += 1
        else:
            sem_match += 1

    conn.commit()

    print()
    print(f'✅ {atualizados} tickets com empresa identificada')
    print(f'⚠️  {sem_match} tickets sem correspondência')

    # Resumo final
    print()
    print('📊 Distribuição por tipo de empresa:')
    for row in conn.execute('''
        SELECT responsavel_empresa, COUNT(*)
        FROM tickets
        GROUP BY responsavel_empresa
        ORDER BY COUNT(*) DESC
    '''):
        print(f'   {row[0] or "(não identificado)":<20} {row[1]}')

    # Marca quem ficou sem empresa como "Externo"
    conn.execute('''
        UPDATE tickets
        SET responsavel_empresa = 'Externo'
        WHERE responsavel_empresa IS NULL
          AND responsavel_atual IS NOT NULL
          AND responsavel_atual != ''
    ''')
    conn.commit()

    print()
    print('📊 Distribuição FINAL:')
    for row in conn.execute('''
        SELECT responsavel_empresa, COUNT(*)
        FROM tickets
        GROUP BY responsavel_empresa
        ORDER BY COUNT(*) DESC
    '''):
        nome = row[0] or '(vazio)'
        print(f'   {nome:<20} {row[1]:>6}')

    conn.close()


if __name__ == '__main__':
    main()