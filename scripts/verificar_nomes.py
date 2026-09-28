"""
Verifica se os nomes dos analistas estão intactos no SQLite.
"""
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

conn = sqlite3.connect(BANCO)
conn.row_factory = sqlite3.Row

print('=' * 60)
print('VERIFICAÇÃO DE NOMES DOS ANALISTAS')
print('=' * 60)

# 1. responsavel_atual
print('\n📋 tickets.responsavel_atual (distintos):')
for r in conn.execute('SELECT DISTINCT responsavel_atual FROM tickets WHERE responsavel_atual IS NOT NULL LIMIT 10'):
    print(f'  {r["responsavel_atual"]}')

# 2. solicitante
print('\n📋 tickets.solicitante (distintos):')
for r in conn.execute('SELECT DISTINCT solicitante FROM tickets WHERE solicitante IS NOT NULL LIMIT 10'):
    print(f'  {r["solicitante"]}')

# 3. autor das movimentações
print('\n📋 movimentacoes.autor (distintos):')
for r in conn.execute('SELECT DISTINCT autor FROM movimentacoes WHERE autor IS NOT NULL LIMIT 10'):
    print(f'  {r["autor"]}')

# 4. titulo (deve ter <NOME> se tinha beneficiário)
print('\n📋 tickets.titulo (amostra com possível <NOME>):')
for r in conn.execute("""
    SELECT titulo FROM tickets
    WHERE titulo LIKE '%<NOME>%' OR titulo LIKE '%Ação Judicial%'
    LIMIT 5
"""):
    print(f'  {r["titulo"][:100]}')

# 5. Conta quantos têm <NOME> em responsavel_atual (deve ser 0)
total_resp_quebrados = conn.execute("""
    SELECT COUNT(*) FROM tickets WHERE responsavel_atual LIKE '%<NOME>%'
""").fetchone()[0]

total_sol_quebrados = conn.execute("""
    SELECT COUNT(*) FROM tickets WHERE solicitante LIKE '%<NOME>%'
""").fetchone()[0]

total_autor_quebrados = conn.execute("""
    SELECT COUNT(*) FROM movimentacoes WHERE autor LIKE '%<NOME>%'
""").fetchone()[0]

print()
print('=' * 60)
print('RESUMO')
print('=' * 60)
print(f'tickets.responsavel_atual com <NOME>: {total_resp_quebrados}')
print(f'tickets.solicitante com <NOME>:       {total_sol_quebrados}')
print(f'movimentacoes.autor com <NOME>:       {total_autor_quebrados}')

if total_resp_quebrados == 0 and total_sol_quebrados == 0 and total_autor_quebrados == 0:
    print('\n✅ Nomes dos analistas estão INTACTOS!')
else:
    print('\n❌ Ainda tem nomes quebrados — precisa restaurar do backup')

conn.close()