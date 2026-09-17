import sqlite3
from pathlib import Path
from collections import Counter

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

conn = sqlite3.connect(BANCO)

print('=' * 60)
print('TOP 20 RESPONSÁVEIS SEM EMPRESA IDENTIFICADA')
print('=' * 60)

rows = conn.execute('''
    SELECT responsavel_atual, COUNT(*) as qtd
    FROM tickets
    WHERE responsavel_empresa IS NULL
      AND responsavel_atual IS NOT NULL
      AND responsavel_atual != ''
    GROUP BY responsavel_atual
    ORDER BY qtd DESC
    LIMIT 20
''').fetchall()

for resp, qtd in rows:
    print(f'  {qtd:>5}  {resp}')

print()
print('=' * 60)
print('TIPOS DE RESPONSÁVEL SEM EMPRESA')
print('=' * 60)

rows2 = conn.execute('''
    SELECT responsavel_atual
    FROM tickets
    WHERE responsavel_empresa IS NULL
      AND responsavel_atual IS NOT NULL
      AND responsavel_atual != ''
    GROUP BY responsavel_atual
''').fetchall()

nomes = [r[0] for r in rows2]
print(f'Total de nomes únicos sem empresa: {len(nomes)}')

# Verifica se algum está na tabela analistas
analistas = set(conn.execute('SELECT nome FROM analistas').fetchall())
analistas = {a[0] for a in analistas}

com_match = [n for n in nomes if n in analistas]
print(f'Desses, {len(com_match)} estão na tabela analistas (match direto)')

# Amostra dos primeiros
print()
print('Amostra (10 primeiros):')
for n in nomes[:10]:
    print(f'  • {n}')

conn.close()