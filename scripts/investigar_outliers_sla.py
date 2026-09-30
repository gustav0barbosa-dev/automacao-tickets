"""
Investiga os tickets com horas de resolução absurdas (outliers).
"""
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

conn = sqlite3.connect(BANCO)
conn.row_factory = sqlite3.Row

print('=' * 80)
print('INVESTIGAÇÃO DE OUTLIERS — SLA')
print('=' * 80)

# ==================== TOP 10 PIORES ====================
print('\n📊 Top 10 tickets com MAIS horas de resolução:')
print()

for r in conn.execute('''
    SELECT id, prioridade, criado_data, data_resolvido, horas_resolucao
    FROM tickets
    WHERE horas_resolucao IS NOT NULL
    ORDER BY horas_resolucao DESC
    LIMIT 10
'''):
    horas = r['horas_resolucao']
    anos = horas / (365 * 24)
    print(f'  #{r["id"]} ({r["prioridade"]}): {horas:,.0f}h ({anos:.1f} anos)')
    print(f'      criado    = {r["criado_data"]}')
    print(f'      resolvido = {r["data_resolvido"]}')
    print()

# ==================== DISTRIBUIÇÃO ====================
print('=' * 80)
print('DISTRIBUIÇÃO DAS HORAS DE RESOLUÇÃO')
print('=' * 80)
print()

# Faixas de horas
faixas = [
    ('0-24h (1 dia)', 0, 24),
    ('24-48h (1-2 dias)', 24, 48),
    ('48-120h (2-5 dias)', 48, 120),
    ('120-240h (5-10 dias)', 120, 240),
    ('240-720h (10-30 dias)', 240, 720),
    ('720-2160h (30-90 dias)', 720, 2160),
    ('2160-8760h (90-365 dias)', 2160, 8760),
    ('>8760h (>1 ano) ⚠️', 8760, 99999999),
]

for label, min_h, max_h in faixas:
    r = conn.execute('''
        SELECT COUNT(*) as n FROM tickets
        WHERE horas_resolucao >= ? AND horas_resolucao < ?
    ''', (min_h, max_h)).fetchone()
    n = r['n']
    if n > 0:
        print(f'  {label:<30} {n:>5} tickets')

# ==================== ESTATÍSTICAS ====================
print()
print('=' * 80)
print('ESTATÍSTICAS')
print('=' * 80)
print()

r = conn.execute('''
    SELECT
        COUNT(*) as total,
        AVG(horas_resolucao) as media,
        MIN(horas_resolucao) as minimo,
        MAX(horas_resolucao) as maximo
    FROM tickets
    WHERE horas_resolucao IS NOT NULL
''').fetchone()

print(f'  Total analisado   : {r["total"]}')
print(f'  Média             : {r["media"]:,.1f}h')
print(f'  Mínimo            : {r["minimo"]:.1f}h')
print(f'  Máximo            : {r["maximo"]:,.1f}h')

# Percentis
print()
print('  Percentis:')
for pct in [50, 75, 90, 95, 99]:
    r = conn.execute('''
        SELECT horas_resolucao
        FROM tickets
        WHERE horas_resolucao IS NOT NULL
        ORDER BY horas_resolucao
        LIMIT 1 OFFSET (
            SELECT CAST(COUNT(*) * ? / 100 AS INTEGER)
            FROM tickets WHERE horas_resolucao IS NOT NULL
        )
    ''', (pct,)).fetchone()
    if r:
        print(f'    P{pct:<3}: {r["horas_resolucao"]:,.1f}h')

# ==================== TICKETS SUSPEITOS ====================
print()
print('=' * 80)
print('TICKETS SUSPEITOS (>1 ano em horas úteis)')
print('=' * 80)
print()

r = conn.execute('''
    SELECT COUNT(*) as n FROM tickets
    WHERE horas_resolucao > 8760
''').fetchone()
print(f'  Total de tickets > 1 ano: {r["n"]}')

if r['n'] > 0:
    print()
    print('  Top 5 mais suspeitos:')
    for row in conn.execute('''
        SELECT id, criado_data, data_resolvido, horas_resolucao
        FROM tickets
        WHERE horas_resolucao > 8760
        ORDER BY horas_resolucao DESC
        LIMIT 5
    '''):
        print(f'    #{row["id"]}: {row["horas_resolucao"]:,.0f}h')
        print(f'        criado={row["criado_data"]} → resolvido={row["data_resolvido"]}')

conn.close()
print()
print('✅ Investigação concluída!')