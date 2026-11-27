"""
Verifica o que está sendo usado nos embeddings.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
IDS_CACHE = RAIZ / 'dados' / 'embeddings_ids.npy'

# IDs dos embeddings
ids = np.load(IDS_CACHE)
print(f'📊 {len(ids)} embeddings carregados')
print(f'   Primeiros 5 IDs: {ids[:5].tolist()}')

# Tickets da analista
TICKETS_ANALISTA = {
    112328, 111703, 111418, 111156, 110852, 112265, 112134,
    111835, 111234, 111233, 111232, 111231, 111180, 110711,
    110388, 112372, 112313, 112126, 111910, 111757, 111532,
    111186, 111161, 110688, 110557, 110522, 110506,
}

# Verifica se os IDs da analista estão nos embeddings
ids_set = set(ids.tolist())
presentes = TICKETS_ANALISTA & ids_set
faltantes = TICKETS_ANALISTA - ids_set

print(f'\n📋 Tickets da analista:')
print(f'   Presentes nos embeddings: {len(presentes)}')
print(f'   Faltantes: {len(faltantes)}')

if faltantes:
    print(f'   IDs faltantes: {sorted(faltantes)}')

# Verifica se os tickets da analista estão no banco
conn = sqlite3.connect(BANCO)
print(f'\n📋 Verificando tickets da analista no banco:')
for tid in sorted(TICKETS_ANALISTA)[:5]:
    r = conn.execute('''
        SELECT id, titulo, descricao, categoria
        FROM tickets WHERE id = ?
    ''', (tid,)).fetchone()

    if r:
        print(f'\n   #{r[0]}:')
        print(f'      Título: {r[1][:80]}')
        print(f'      Descrição: {(r[2] or "")[:100]}')
        print(f'      Categoria: {r[3]}')

        # Conta movs e msgs
        n_movs = conn.execute(
            'SELECT COUNT(*) FROM movimentacoes WHERE ticket_id = ?', (tid,)
        ).fetchone()[0]
        n_msgs = conn.execute(
            'SELECT COUNT(*) FROM mensagens WHERE ticket_id = ?', (tid,)
        ).fetchone()[0]
        print(f'      Movimentações: {n_movs} | Mensagens: {n_msgs}')
    else:
        print(f'\n   #{tid}: ❌ NÃO ENCONTRADO NO BANCO')

conn.close()