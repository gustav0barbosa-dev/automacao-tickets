"""
Diagnóstico do banco SQLite — comparação com Help360.
"""
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

conn = sqlite3.connect(BANCO)

print('=' * 70)
print('DIAGNÓSTICO DO BANCO')
print('=' * 70)

# 1. Total
total = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
print(f'\n📊 Total no SQLite: {total}')

# 2. Por status
print('\n📊 Por status:')
for r in conn.execute('''
    SELECT COALESCE(status, '(vazio)') as st, COUNT(*) as n
    FROM tickets
    GROUP BY status
    ORDER BY n DESC
'''):
    print(f'   {r[0]:<40} {r[1]:>6}')

# 3. Por responsavel_empresa
print('\n📊 Por responsavel_empresa:')
for r in conn.execute('''
    SELECT COALESCE(responsavel_empresa, '(vazio)') as emp, COUNT(*) as n
    FROM tickets
    GROUP BY responsavel_empresa
    ORDER BY n DESC
    LIMIT 10
'''):
    print(f'   {r[0]:<30} {r[1]:>6}')

# 4. Atlantic
print('\n📊 Tickets da Atlantic:')
atlantic = conn.execute('''
    SELECT COUNT(*) FROM tickets
    WHERE responsavel_empresa LIKE '%Atlantic%'
       OR empresa LIKE '%Atlantic%'
''').fetchone()[0]
print(f'   Total: {atlantic}')

# 5. Fechados/Cancelados/Duplicados
print('\n📊 Tickets Fechados/Cancelados/Duplicados:')
fechados = conn.execute('''
    SELECT COUNT(*) FROM tickets
    WHERE status IN ('Fechado', 'Cancelado', 'Duplicado')
''').fetchone()[0]
print(f'   Total: {fechados}')

# 6. Distribuição por ano de criação
print('\n📊 Tickets por ano de criação:')
for r in conn.execute('''
    SELECT
        substr(criado_data, 1, 4) as ano,
        COUNT(*) as n
    FROM tickets
    WHERE criado_data IS NOT NULL
    GROUP BY ano
    ORDER BY ano DESC
    LIMIT 10
'''):
    print(f'   {r[0]}: {r[1]:>6}')

# 7. Categorias (top 10)
print('\n📊 Top 10 categorias:')
for r in conn.execute('''
    SELECT COALESCE(categoria, '(vazio)') as cat, COUNT(*) as n
    FROM tickets
    GROUP BY categoria
    ORDER BY n DESC
    LIMIT 10
'''):
    print(f'   {r[0]:<40} {r[1]:>6}')

conn.close()
print('\n' + '=' * 70)
print('FIM')
print('=' * 70)