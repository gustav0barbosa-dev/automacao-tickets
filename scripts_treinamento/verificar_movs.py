"""
Verifica as movimentações do ticket 110506.
"""
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

conn = sqlite3.connect(BANCO)
conn.row_factory = sqlite3.Row

ticket_id = 110506

print('=' * 80)
print(f'MOVIMENTAÇÕES DO TICKET {ticket_id}')
print('=' * 80)

for r in conn.execute('''
    SELECT data_movimentacao, autor, para_status, comentario
    FROM movimentacoes
    WHERE ticket_id = ?
    ORDER BY data_movimentacao ASC
''', (ticket_id,)):
    print(f'\n📅 {r["data_movimentacao"]}')
    print(f'   Autor: {r["autor"]}')
    print(f'   Status: {r["para_status"]}')
    if r['comentario']:
        # Mostra até 300 chars
        comentario = r['comentario'][:300]
        print(f'   Comentário: {comentario}')
    else:
        print(f'   Comentário: (vazio)')

# ==================== ESTATÍSTICAS ====================
print()
print('=' * 80)
print('ESTATÍSTICAS')
print('=' * 80)

com_comentario = conn.execute('''
    SELECT COUNT(*) FROM movimentacoes
    WHERE ticket_id = ? AND comentario IS NOT NULL AND LENGTH(comentario) > 50
''', (ticket_id,)).fetchone()[0]

sem_comentario = conn.execute('''
    SELECT COUNT(*) FROM movimentacoes
    WHERE ticket_id = ? AND (comentario IS NULL OR LENGTH(comentario) <= 50)
''', (ticket_id,)).fetchone()[0]

total = conn.execute('''
    SELECT COUNT(*) FROM movimentacoes WHERE ticket_id = ?
''', (ticket_id,)).fetchone()[0]

print(f'Total de movimentações: {total}')
print(f'Com comentário > 50 chars: {com_comentario}')
print(f'Sem comentário (ou curto): {sem_comentario}')

# ==================== BUSCA POR PALAVRAS-CHAVE ====================
print()
print('=' * 80)
print('BUSCA POR PALAVRAS-CHAVE')
print('=' * 80)

palavras = ['Solução:', 'Mensagem:', 'Comentário:', 'protocolo', 'VATC']

for palavra in palavras:
    r = conn.execute('''
        SELECT COUNT(*) FROM movimentacoes
        WHERE ticket_id = ? AND comentario LIKE ?
    ''', (ticket_id, f'%{palavra}%')).fetchone()[0]
    print(f'   "{palavra}": {r} movimentações')

conn.close()
print()
print('✅ Fim')