# scripts_treinamento/verificar_campos.py
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

conn = sqlite3.connect(BANCO)
conn.row_factory = sqlite3.Row

print('=' * 80)
print('ESTATÍSTICAS APÓS ENRIQUECIMENTO')
print('=' * 80)

total = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
com_descricao = conn.execute('''
    SELECT COUNT(*) FROM tickets
    WHERE descricao IS NOT NULL AND LENGTH(descricao) > 10
''').fetchone()[0]
com_solucao = conn.execute('''
    SELECT COUNT(*) FROM tickets
    WHERE solucao IS NOT NULL AND LENGTH(solucao) > 10
''').fetchone()[0]
enriquecidos = conn.execute('''
    SELECT COUNT(*) FROM tickets WHERE enriquecido = 1
''').fetchone()[0]

# Movimentações e mensagens
total_movs = conn.execute('SELECT COUNT(*) FROM movimentacoes').fetchone()[0]
total_msgs = conn.execute('SELECT COUNT(*) FROM mensagens').fetchone()[0]

# Movimentações com comentário real (>50 chars)
movs_com_conteudo = conn.execute('''
    SELECT COUNT(*) FROM movimentacoes
    WHERE comentario IS NOT NULL AND LENGTH(comentario) > 50
''').fetchone()[0]

print(f'\n📊 TICKETS')
print(f'   Total: {total}')
print(f'   Enriquecidos: {enriquecidos} ({enriquecidos/total*100:.1f}%)')
print(f'   Com descrição: {com_descricao} ({com_descricao/total*100:.1f}%)')
print(f'   Com solução: {com_solucao} ({com_solucao/total*100:.1f}%)')

print(f'\n📊 MOVIMENTAÇÕES')
print(f'   Total: {total_movs}')
print(f'   Com conteúdo >50 chars: {movs_com_conteudo} ({movs_com_conteudo/total_movs*100:.1f}%)')

print(f'\n📊 MENSAGENS')
print(f'   Total: {total_msgs}')

# Top 10 tickets com mais conteúdo
print(f'\n📊 TOP 10 TICKETS COM MAIS CONTEÚDO')
for r in conn.execute('''
    SELECT t.id, t.titulo,
           (SELECT COUNT(*) FROM movimentacoes WHERE ticket_id = t.id) as movs,
           (SELECT COUNT(*) FROM mensagens WHERE ticket_id = t.id) as msgs
    FROM tickets t
    WHERE t.enriquecido = 1
    ORDER BY (movs + msgs) DESC
    LIMIT 10
'''):
    print(f'   #{r["id"]} — {r["titulo"][:60]}')
    print(f'      {r["movs"]} movs | {r["msgs"]} msgs')

conn.close()
print()
print('✅ Fim')