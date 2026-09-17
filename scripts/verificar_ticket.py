import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

ticket_id = sys.argv[1] if len(sys.argv) > 1 else '111239'

conn = sqlite3.connect(BANCO)
row = conn.execute('''
    SELECT id, titulo, status, backlog, respondido, classificacao,
           responsavel_atual, area, empresa, sistema
    FROM tickets WHERE id = ?
''', (ticket_id,)).fetchone()
conn.close()

if not row:
    print(f'❌ Ticket {ticket_id} não encontrado')
    sys.exit(1)

print(f'ID              : {row[0]}')
print(f'Título          : {row[1][:60] if row[1] else None}')
print(f'Status          : {row[2]}')
print(f'Backlog         : {row[3]}  {"← ✅ É backlog!" if row[3] == 1 else ""}')
print(f'Respondido      : {row[4]}')
print(f'Classificação   : {row[5]}')
print(f'Responsável     : {row[6]}')
print(f'Área            : {row[7]}')
print(f'Empresa         : {row[8]}')
print(f'Sistema         : {row[9]}')