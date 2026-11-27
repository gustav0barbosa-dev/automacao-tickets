"""
Avalia várias queries contra os tickets da analista.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
EMBEDDINGS_CACHE = RAIZ / 'dados' / 'embeddings_completo.npy'
IDS_CACHE = RAIZ / 'dados' / 'embeddings_ids.npy'

# ==================== GABARITO ====================
TICKETS_ANALISTA_TODOS = {
    112328, 111703, 111418, 111156, 110852, 112265, 112134,
    111835, 111234, 111233, 111232, 111231, 111180, 110711,
    110388, 112372, 112313, 112126, 111910, 111757, 111532,
    111186, 111161, 110688, 110557, 110522, 110506,
}

# ==================== QUERIES ====================
QUERIES = [
    "erro ao abrir composição de rubricas",
    "contagem de tempo zerada",
    "cálculo da média não para no mês",
    "protocolo cancelado ao formalizar tarefa",
    "erro interno do servidor",
    "valor do benefício não cadastrado",
    "protocolo VTC associado não encontrado",
    "requerimento com data errada",
    "fluxo seguiu caminho errado",
    "tarefa reaberta após formalização",
]

# ==================== CARREGA EMBEDDINGS ====================
print('📂 Carregando embeddings...')
embeddings = np.load(EMBEDDINGS_CACHE)
ids = np.load(IDS_CACHE)
print(f'   {len(ids)} embeddings')

# ==================== FILTRA O GABARITO ====================
# Só considera tickets que ESTÃO nos embeddings
ids_disponiveis = set(ids.tolist())
tickets_analista = TICKETS_ANALISTA_TODOS & ids_disponiveis
tickets_faltantes = TICKETS_ANALISTA_TODOS - ids_disponiveis

print(f'\n📋 Tickets da analista:')
print(f'   Total: {len(TICKETS_ANALISTA_TODOS)}')
print(f'   Com embeddings: {len(tickets_analista)}')
print(f'   SEM embeddings: {len(tickets_faltantes)}')

if tickets_faltantes:
    print(f'   IDs sem embeddings: {sorted(tickets_faltantes)}')

# ==================== CARREGA MODELO ====================
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# ==================== AVALIA ====================
print()
print('=' * 70)
print('AVALIAÇÃO DE QUERIES')
print('=' * 70)

# Guarda o resultado de cada query
resultados = []

for query in QUERIES:
    # Gera embedding da query
    query_emb = model.encode([query])[0]

    # Similaridade
    similaridades = np.dot(embeddings, query_emb) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_emb)
    )

    # Top 100
    top_100 = set(ids[np.argsort(similaridades)[-100:]].tolist())

    # Acertos
    acertos = len(tickets_analista & top_100)
    recall = acertos / len(tickets_analista) * 100 if tickets_analista else 0

    resultados.append({
        'query': query,
        'acertos': acertos,
        'recall': recall,
        'total': len(tickets_analista),
    })

    print(f'\n📝 "{query}"')
    print(f'   Acertos: {acertos}/{len(tickets_analista)} ({recall:.0f}%)')

    # Lista os que faltaram
    faltaram = tickets_analista - top_100
    if faltaram:
        print(f'   Faltaram ({len(faltaram)}): {sorted(faltaram)[:5]}...')

# ==================== RANKING ====================
print()
print('=' * 70)
print('RANKING DAS QUERIES (por recall)')
print('=' * 70)

df_result = pd.DataFrame(resultados).sort_values('recall', ascending=False)

for i, row in df_result.iterrows():
    print(f'   {row["recall"]:5.1f}%  ({row["acertos"]:2d}/{row["total"]:2d})  "{row["query"]}"')

# ==================== MELHOR QUERY ====================
melhor = df_result.iloc[0]
print(f'\n🏆 Melhor query: "{melhor["query"]}" ({melhor["recall"]:.0f}%)')