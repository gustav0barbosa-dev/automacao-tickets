# scripts_treinamento/verificar_campos.py
"""
Verifica o conteúdo dos campos de texto no banco.
"""
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

conn = sqlite3.connect(BANCO)
conn.row_factory = sqlite3.Row

# ==================== TICKET 110506 ====================
ticket_id = 110506

r = conn.execute('''
    SELECT id, titulo, descricao, solucao, diagnostico, status, categoria
    FROM tickets WHERE id = ?
''', (ticket_id,)).fetchone()

print('=' * 80)
print(f'TICKET {ticket_id}')
print('=' * 80)
print(f'\nTítulo: {r["titulo"]}')
print(f'\nDescrição: {(r["descricao"] or "(vazio)")[:500]}')
print(f'\nSolução: {(r["solucao"] or "(vazio)")[:500]}')
print(f'\nDiagnóstico: {(r["diagnostico"] or "(vazio)")[:500]}')
print(f'\nStatus: {r["status"]}')
print(f'Categoria: {r["categoria"]}')

# ==================== ESTATÍSTICAS ====================
print()
print('=' * 80)
print('ESTATÍSTICAS (todos os tickets)')
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
com_diagnostico = conn.execute('''
    SELECT COUNT(*) FROM tickets
    WHERE diagnostico IS NOT NULL AND LENGTH(diagnostico) > 10
''').fetchone()[0]

print(f'\nTotal de tickets: {total}')
print(f'Com descrição:   {com_descricao} ({com_descricao/total*100:.1f}%)')
print(f'Com solução:     {com_solucao} ({com_solucao/total*100:.1f}%)')
print(f'Com diagnóstico: {com_diagnostico} ({com_diagnostico/total*100:.1f}%)')

# ==================== MOVIMENTAÇÕES ====================
print()
print('=' * 80)
print('MOVIMENTAÇÕES (ticket 110506)')
print('=' * 80)

movs = conn.execute('''
    SELECT data_movimentacao, autor, para_status, comentario
    FROM movimentacoes
    WHERE ticket_id = ?
    ORDER BY data_movimentacao
''', (ticket_id,)).fetchall()

print(f'\nTotal: {len(movs)}')
for m in movs:
    print(f'\n📅 {m["data_movimentacao"]} | {m["para_status"]}')
    print(f'   Autor: {m["autor"]}')
    print(f'   Comentário: {(m["comentario"] or "(vazio)")[:200]}')

# ==================== MENSAGENS ====================
print()
print('=' * 80)
print('MENSAGENS (ticket 110506)')
print('=' * 80)

msgs = conn.execute('''
    SELECT data_hora, autor, conteudo
    FROM mensagens
    WHERE ticket_id = ?
    ORDER BY data_hora
''', (ticket_id,)).fetchall()

print(f'\nTotal: {len(msgs)}')
for m in msgs[:5]:
    print(f'\n📅 {m["data_hora"]} | {m["autor"]}')
    print(f'   Conteúdo: {(m["conteudo"] or "(vazio)")[:200]}')

conn.close()
print()
print('✅ Fim')