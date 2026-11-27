"""
Diagnostica por que o contexto não está sendo incluído.
"""
import sqlite3
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

conn = sqlite3.connect(BANCO)

# 1. Amostra de tickets
print('=' * 70)
print('1. TICKETS (amostra)')
print('=' * 70)
df_tickets = pd.read_sql('SELECT id, titulo, descricao FROM tickets LIMIT 5', conn)
print(df_tickets.to_string())
print(f'\nTipos:')
print(df_tickets.dtypes)

# 2. Amostra de movimentações
print('\n' + '=' * 70)
print('2. MOVIMENTACOES (amostra)')
print('=' * 70)
df_movs = pd.read_sql('SELECT ticket_id, comentario FROM movimentacoes LIMIT 5', conn)
print(df_movs.to_string())
print(f'\nTipos:')
print(df_movs.dtypes)

# 3. Amostra de mensagens
print('\n' + '=' * 70)
print('3. MENSAGENS (amostra)')
print('=' * 70)
df_msgs = pd.read_sql('SELECT ticket_id, conteudo FROM mensagens LIMIT 5', conn)
print(df_msgs.to_string())
print(f'\nTipos:')
print(df_msgs.dtypes)

# 4. Teste de merge
print('\n' + '=' * 70)
print('4. TESTE DE MERGE')
print('=' * 70)

movs_agg = df_movs.groupby('ticket_id')['comentario'].apply(
    lambda x: ' '.join(x.astype(str).tolist())[:500]
).reset_index()
movs_agg.columns = ['ticket_id', 'texto_movs']

print(f'Movs agregadas: {len(movs_agg)}')
print(f'IDs movs: {movs_agg["ticket_id"].tolist()}')
print(f'Tipo: {movs_agg["ticket_id"].dtype}')

print(f'\nIDs tickets: {df_tickets["id"].tolist()}')
print(f'Tipo: {df_tickets["id"].dtype}')

# Merge
merged = df_tickets.merge(movs_agg, left_on='id', right_on='ticket_id', how='left')
print(f'\nApós merge: {len(merged)}')
print(merged[['id', 'titulo', 'texto_movs']].to_string())

# 5. Contagem
print('\n' + '=' * 70)
print('5. CONTAGEM')
print('=' * 70)
total_tickets = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
total_movs = conn.execute('SELECT COUNT(*) FROM movimentacoes').fetchone()[0]
total_msgs = conn.execute('SELECT COUNT(*) FROM mensagens').fetchone()[0]

print(f'Tickets: {total_tickets}')
print(f'Movimentações: {total_movs}')
print(f'Mensagens: {total_msgs}')

# Quantos tickets têm movimentações?
n_tickets_com_movs = conn.execute('''
    SELECT COUNT(DISTINCT ticket_id) FROM movimentacoes
''').fetchone()[0]
print(f'Tickets com movimentações: {n_tickets_com_movs}')

n_tickets_com_msgs = conn.execute('''
    SELECT COUNT(DISTINCT ticket_id) FROM mensagens
''').fetchone()[0]
print(f'Tickets com mensagens: {n_tickets_com_msgs}')

# Ticket 110506 (da analista)
print('\n' + '=' * 70)
print('6. TICKET 110506 (da analista)')
print('=' * 70)

r = conn.execute('SELECT id, titulo, descricao FROM tickets WHERE id = 110506').fetchone()
print(f'Ticket: {r}')

r = conn.execute('SELECT * FROM movimentacoes WHERE ticket_id = 110506').fetchall()
print(f'\nMovimentações ({len(r)}):')
for row in r[:3]:
    print(f'  {dict(row) if hasattr(row, "keys") else row}')

r = conn.execute('SELECT * FROM mensagens WHERE ticket_id = 110506').fetchall()
print(f'\nMensagens ({len(r)}):')
for row in r[:3]:
    print(f'  {dict(row) if hasattr(row, "keys") else row}')

conn.close()