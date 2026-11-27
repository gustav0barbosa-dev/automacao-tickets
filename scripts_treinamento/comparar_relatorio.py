"""
Compara os tickets do relatório da analista com os clusters.
"""
import sqlite3
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
CLUSTERS = RAIZ / 'dados' / 'tickets_clusters.csv'

# ==================== TICKETS DA ANALISTA ====================
TICKETS_ANALISTA = [
    112328, 111703, 111418, 111156, 110852, 112265, 112134,
    111835, 111234, 111233, 111232, 111231, 111180, 110711,
    110388, 112372, 112313, 112126, 111910, 111757, 111532,
    111186, 111161, 110688, 110557, 110522, 110506,
]

# ==================== CARREGA CLUSTERS ====================
df_clusters = pd.read_csv(CLUSTERS)

# ==================== CRUZA ====================
print('=' * 70)
print('COMPARAÇÃO: RELATÓRIO DA ANALISTA vs CLUSTERS')
print('=' * 70)
print()

# Filtra tickets da analista
df_analista = df_clusters[df_clusters['id'].isin(TICKETS_ANALISTA)]
print(f'📋 Tickets da analista: {len(df_analista)} de {len(TICKETS_ANALISTA)}')

# Distribuição por cluster
dist = df_analista['cluster'].value_counts().sort_index()
print(f'\n📊 Distribuição por cluster:')
for cluster_id, n in dist.items():
    if cluster_id == -1:
        print(f'   Cluster -1 (ruído): {n} tickets')
    else:
        print(f'   Cluster {cluster_id}: {n} tickets')

# ==================== DETALHES POR CLUSTER ====================
print()
print('=' * 70)
print('DETALHES DOS CLUSTERS DOS TICKETS DA ANALISTA')
print('=' * 70)

# Carrega títulos
conn = sqlite3.connect(BANCO)
for cluster_id in sorted(dist.index):
    if cluster_id == -1:
        continue

    ids_cluster = df_analista[df_analista['cluster'] == cluster_id]['id'].tolist()
    ids_str = ','.join(str(i) for i in ids_cluster)

    df_titulos = pd.read_sql(f'''
        SELECT id, titulo, categoria, status
        FROM tickets
        WHERE id IN ({ids_str})
    ''', conn)

    print(f'\n📦 Cluster {cluster_id} ({len(ids_cluster)} tickets):')
    for _, row in df_titulos.iterrows():
        print(f'   #{row["id"]} — {row["titulo"][:70]}')
        print(f'      {row["categoria"]} | {row["status"]}')

conn.close()

# ==================== CLUSTERS QUE MAIS APARECEM ====================
print()
print('=' * 70)
print('CLUSTERS MAIS FREQUENTES NOS TICKETS DA ANALISTA')
print('=' * 70)

# Top 5 clusters
top_clusters = dist.head(10)
for cluster_id, n in top_clusters.items():
    if cluster_id == -1:
        continue
    pct = n / len(df_analista) * 100
    print(f'   Cluster {cluster_id}: {n} tickets ({pct:.0f}%)')

# ==================== TICKETS SEM CLUSTER ====================
print()
print('=' * 70)
print('TICKETS DA ANALISTA QUE NÃO ESTÃO EM NENHUM CLUSTER (ruído)')
print('=' * 70)

ruido = df_analista[df_analista['cluster'] == -1]['id'].tolist()
if ruido:
    conn = sqlite3.connect(BANCO)
    ids_str = ','.join(str(i) for i in ruido)
    df_ruido = pd.read_sql(f'''
        SELECT id, titulo FROM tickets WHERE id IN ({ids_str})
    ''', conn)
    conn.close()

    for _, row in df_ruido.iterrows():
        print(f'   #{row["id"]} — {row["titulo"][:80]}')
else:
    print('   ✅ Nenhum ticket em ruído')