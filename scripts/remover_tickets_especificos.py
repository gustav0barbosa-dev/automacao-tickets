"""
Remove tickets específicos do banco SQLite + Postgres (opcional).

Remove:
  - tickets
  - movimentacoes (ticket_id)
  - mensagens (ticket_id)

Uso:
    python scripts/remover_tickets_especificos.py
"""
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

# Tickets da Atlantic pra remover
IDS_REMOVER = [
    111041,
    111108,
    111155,
    111193,
]


def main():
    print('=' * 60)
    print('REMOÇÃO DE TICKETS ESPECÍFICOS')
    print('=' * 60)
    print(f'Tickets a remover: {IDS_REMOVER}')
    print(f'Total: {len(IDS_REMOVER)}')
    print()

    if not BANCO.exists():
        print(f'❌ Banco não encontrado: {BANCO}')
        return False

    conn = sqlite3.connect(BANCO)
    conn.row_factory = sqlite3.Row

    placeholders = ','.join('?' * len(IDS_REMOVER))

    # ==================== VERIFICA ANTES ====================
    print('📊 ANTES DA REMOÇÃO:')
    total_antes = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
    print(f'  Total de tickets: {total_antes}')

    encontrados = conn.execute(
        f'SELECT id FROM tickets WHERE id IN ({placeholders})',
        IDS_REMOVER,
    ).fetchall()
    print(f'  Encontrados no banco: {len(encontrados)}')
    for row in encontrados:
        print(f'    #{row["id"]}')

    if not encontrados:
        print('\n⚠️ Nenhum ticket encontrado. Nada a fazer.')
        conn.close()
        return True

    # ==================== CONFIRMA ====================
    print()
    resposta = input(f'Remover {len(encontrados)} tickets? (s/N): ').strip().lower()
    if resposta != 's':
        print('Cancelado.')
        conn.close()
        return False

    # ==================== REMOVE ====================
    print('\n🗑️  Removendo tickets...')

    # 1. Remove movimentações
    cur = conn.execute(
        f'DELETE FROM movimentacoes WHERE ticket_id IN ({placeholders})',
        IDS_REMOVER,
    )
    print(f'  ✅ {cur.rowcount} movimentações removidas')

    # 2. Remove mensagens
    cur = conn.execute(
        f'DELETE FROM mensagens WHERE ticket_id IN ({placeholders})',
        IDS_REMOVER,
    )
    print(f'  ✅ {cur.rowcount} mensagens removidas')

    # 3. Remove tickets
    cur = conn.execute(
        f'DELETE FROM tickets WHERE id IN ({placeholders})',
        IDS_REMOVER,
    )
    print(f'  ✅ {cur.rowcount} tickets removidos')

    conn.commit()

    # ==================== VERIFICA DEPOIS ====================
    print()
    print('📊 DEPOIS DA REMOÇÃO:')
    total_depois = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
    print(f'  Total de tickets: {total_depois}')
    print(f'  Removidos: {total_antes - total_depois}')

    # ==================== VACUUM ====================
    print('\n🧹 Compactando banco (VACUUM)...')
    conn.execute('VACUUM')
    conn.close()

    print('\n✅ Remoção concluída!')
    return True


if __name__ == '__main__':
    import sys
    sys.exit(0 if main() else 1)