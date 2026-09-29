"""
Remove tickets da Atlantic Solutions do banco SQLite.

Uso:
    python scripts/remover_tickets_atlantic.py
"""
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

# Tickets da Atlantic identificados
IDS_ATLANTIC = [
    111078, 111134, 111160, 111036, 111002, 111012, 111013, 111045,
    111021, 111039, 111049, 111051, 111052, 111053, 111054, 111068,
    111077, 111093, 111106, 111107, 111120, 111121, 111123, 111139,
    111158, 111152, 111163, 111176, 111191,
]

def main():
    print('=' * 60)
    print('REMOÇÃO DE TICKETS DA ATLANTIC SOLUTIONS')
    print('=' * 60)
    print(f'Total de IDs: {len(IDS_ATLANTIC)}')
    print()

    if not BANCO.exists():
        print(f'❌ Banco não encontrado: {BANCO}')
        return False

    conn = sqlite3.connect(BANCO)
    conn.row_factory = sqlite3.Row

    # ==================== VERIFICA ANTES ====================
    print('📊 ANTES DA REMOÇÃO:')
    cur = conn.execute('SELECT COUNT(*) FROM tickets')
    total_antes = cur.fetchone()[0]
    print(f'  Total de tickets: {total_antes}')

    placeholders = ','.join('?' * len(IDS_ATLANTIC))

    cur = conn.execute(
        f'SELECT COUNT(*) FROM tickets WHERE id IN ({placeholders})',
        IDS_ATLANTIC,
    )
    encontrados = cur.fetchone()[0]
    print(f'  Tickets da Atlantic encontrados: {encontrados}')

    if encontrados == 0:
        print('\n⚠️ Nenhum ticket da Atlantic encontrado. Nada a fazer.')
        conn.close()
        return True

    # ==================== CONFIRMA ====================
    print()
    resposta = input(f'Remover {encontrados} tickets? (s/N): ').strip().lower()
    if resposta != 's':
        print('Cancelado.')
        conn.close()
        return False

    # ==================== REMOVE ====================
    print('\n🗑️ Removendo tickets...')

    # 1. Remove mensagens
    cur = conn.execute(
        f'DELETE FROM mensagens WHERE ticket_id IN ({placeholders})',
        IDS_ATLANTIC,
    )
    print(f'  ✅ {cur.rowcount} mensagens removidas')

    # 2. Remove movimentações
    cur = conn.execute(
        f'DELETE FROM movimentacoes WHERE ticket_id IN ({placeholders})',
        IDS_ATLANTIC,
    )
    print(f'  ✅ {cur.rowcount} movimentações removidas')

    # 3. Remove tickets
    cur = conn.execute(
        f'DELETE FROM tickets WHERE id IN ({placeholders})',
        IDS_ATLANTIC,
    )
    print(f'  ✅ {cur.rowcount} tickets removidos')

    conn.commit()

    # ==================== VERIFICA DEPOIS ====================
    print()
    print('📊 DEPOIS DA REMOÇÃO:')
    cur = conn.execute('SELECT COUNT(*) FROM tickets')
    total_depois = cur.fetchone()[0]
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