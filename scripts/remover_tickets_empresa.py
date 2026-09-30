"""
Remove tickets de empresas específicas do banco SQLite.

Uso:
    python scripts/remover_tickets_empresa.py
"""
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

# Empresas a remover
EMPRESAS_REMOVER = ['Atlantic', 'Atlantic Solutions']


def main():
    print('=' * 60)
    print('REMOÇÃO DE TICKETS POR EMPRESA')
    print('=' * 60)
    print(f'Empresas: {EMPRESAS_REMOVER}')
    print()

    conn = sqlite3.connect(BANCO)
    conn.row_factory = sqlite3.Row

    # Conta antes
    total_antes = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
    print(f'📊 Total de tickets: {total_antes}')

    # Conta tickets das empresas
    placeholders = ','.join('?' * len(EMPRESAS_REMOVER))
    ids = conn.execute(f'''
        SELECT id FROM tickets
        WHERE empresa IN ({placeholders})
           OR responsavel_empresa IN ({placeholders})
    ''', EMPRESAS_REMOVER + EMPRESAS_REMOVER).fetchall()

    ids_list = [r['id'] for r in ids]
    print(f'🚫 Tickets das empresas {EMPRESAS_REMOVER}: {len(ids_list)}')
    print(f'   IDs: {ids_list[:10]}{"..." if len(ids_list) > 10 else ""}')
    print()

    if not ids_list:
        print('⚠️ Nenhum ticket encontrado')
        conn.close()
        return True

    # Confirma
    resposta = input(f'Remover {len(ids_list)} tickets? (s/N): ').strip().lower()
    if resposta != 's':
        print('Cancelado.')
        conn.close()
        return False

    # Remove
    print('\n🗑️  Removendo...')
    placeholders_ids = ','.join('?' * len(ids_list))

    cur = conn.execute(
        f'DELETE FROM movimentacoes WHERE ticket_id IN ({placeholders_ids})',
        ids_list,
    )
    print(f'  ✅ {cur.rowcount} movimentações removidas')

    cur = conn.execute(
        f'DELETE FROM mensagens WHERE ticket_id IN ({placeholders_ids})',
        ids_list,
    )
    print(f'  ✅ {cur.rowcount} mensagens removidas')

    cur = conn.execute(
        f'DELETE FROM tickets WHERE id IN ({placeholders_ids})',
        ids_list,
    )
    print(f'  ✅ {cur.rowcount} tickets removidos')

    conn.commit()

    # Verifica depois
    total_depois = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
    print()
    print(f'📊 DEPOIS: {total_depois} tickets')
    print(f'   Removidos: {total_antes - total_depois}')

    # VACUUM
    print('\n🧹 Compactando...')
    conn.execute('VACUUM')
    conn.close()

    print('\n✅ Concluído!')
    return True


if __name__ == '__main__':
    import sys
    sys.exit(0 if main() else 1)