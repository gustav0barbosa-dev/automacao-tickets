# scripts/descobrir_temas.py (v2 — com movimentações e mensagens)
"""
Descobre temas nos tickets usando clustering.

DIFERENCIAL: concatena título + descrição + movimentações + mensagens
para capturar o contexto REAL do ticket.
"""
import sqlite3
from pathlib import Path

import hdbscan
import pandas as pd
import umap
from sentence_transformers import SentenceTransformer

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
SAIDA_CSV = RAIZ / 'relatorios' / 'clusters.csv'
SAIDA_IDS = RAIZ / 'dados' / 'tickets_clusters.csv'
SAIDA_HTML = RAIZ / 'relatorios' / 'clusters.html'

# ==================== 1. CARREGA TICKETS + CONTEXTO ====================
print('📂 Carregando tickets e contexto...')
conn = sqlite3.connect(BANCO)

# Tickets do último ano
df = pd.read_sql('''
    SELECT id, titulo, descricao, categoria, status, prioridade
    FROM tickets
    WHERE criado_data >= date('now', '-1 year')
''', conn)

# Movimentações (agrega por ticket)
movs = pd.read_sql('''
    SELECT ticket_id, comentario, autor, para_status
    FROM movimentacoes
    WHERE ticket_id IN (
        SELECT id FROM tickets WHERE criado_data >= date('now', '-1 year')
    )
    AND comentario IS NOT NULL
    ORDER BY ticket_id, data_movimentacao ASC
''', conn)

# Mensagens (agrega por ticket)
msgs = pd.read_sql('''
    SELECT ticket_id, conteudo, autor
    FROM mensagens
    WHERE ticket_id IN (
        SELECT id FROM tickets WHERE criado_data >= date('now', '-1 year')
    )
    AND conteudo IS NOT NULL
    ORDER BY ticket_id, data_hora ASC
''', conn)

conn.close()

print(f'   {len(df)} tickets')
print(f'   {len(movs)} movimentações')
print(f'   {len(msgs)} mensagens')

# ==================== 2. AGREGA CONTEXTO POR TICKET ====================
print('\n🔗 Agregando contexto por ticket...')

def agregar_texto(group):
    """Junta os textos de um ticket em uma string."""
    return ' '.join(group['comentario'].astype(str).tolist())

def agregar_mensagens(group):
    """Junta os textos de mensagens de um ticket."""
    return ' '.join(group['conteudo'].astype(str).tolist())

movs_por_ticket = movs.groupby('ticket_id').apply(agregar_texto).reset_index()
movs_por_ticket.columns = ['ticket_id', 'texto_movs']

msgs_por_ticket = msgs.groupby('ticket_id').apply(agregar_mensagens).reset_index()
msgs_por_ticket.columns = ['ticket_id', 'texto_msgs']

# Merge com tickets
df = df.merge(movs_por_ticket, left_on='id', right_on='ticket_id', how='left')
df = df.merge(msgs_por_ticket, left_on='id', right_on='ticket_id', how='left')
df = df.drop(columns=['ticket_id_x', 'ticket_id_y'], errors='ignore')

# Preenche NaN com vazio
df['texto_movs'] = df['texto_movs'].fillna('')
df['texto_msgs'] = df['texto_msgs'].fillna('')

# ==================== 3. MONTA TEXTO ENRIQUECIDO ====================
print('\n📝 Montando texto enriquecido...')

def montar_texto(row):
    """
    Monta o texto que vai pro embedding.

    Estratégia:
      - Título (repetido 2x, peso maior)
      - Descrição (300 chars)
      - Movimentações (500 chars, do final)
      - Mensagens (500 chars, do final)
    """
    titulo = str(row['titulo'] or '')[:200]
    descricao = str(row['descricao'] or '')[:300]
    movs = str(row['texto_movs'] or '')[-500:]  # últimas 500 chars
    msgs = str(row['texto_msgs'] or '')[-500:]  # últimas 500 chars

    return f"{titulo}. {titulo}. {descricao} {movs} {msgs}".strip()

df['texto_completo'] = df.apply(montar_texto, axis=1)

# Verifica tamanho médio
tamanho_medio = df['texto_completo'].str.len().mean()
print(f'   Tamanho médio: {tamanho_medio:.0f} chars')

# ==================== 4. GERA EMBEDDINGS ====================
print('\n🧠 Gerando embeddings...')
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

textos = df['texto_completo'].tolist()
embeddings = model.encode(textos, show_progress_bar=True, batch_size=32)
print(f'   Shape: {embeddings.shape}')

# ==================== 5. REDUZ DIMENSÃO ====================
print('\n📉 Reduzindo dimensão (UMAP)...')
umap_emb = umap.UMAP(
    n_neighbors=15,
    n_components=5,
    min_dist=0.0,
    metric='cosine',
    random_state=42,
).fit_transform(embeddings)

# ==================== 6. CLUSTERING ====================
print('\n🔍 Agrupando (HDBSCAN)...')
clusterer = hdbscan.HDBSCAN(
    min_cluster_size=20,
    min_samples=5,
    metric='euclidean',
    cluster_selection_method='eom',
)
clusters = clusterer.fit_predict(umap_emb)
df['cluster'] = clusters

n_clusters = len(set(clusters)) - (1 if -1 in clusters else 0)
n_ruido = (clusters == -1).sum()
print(f'   {n_clusters} clusters encontrados')
print(f'   {n_ruido} tickets como ruído')

# ==================== 7. GERA RELATÓRIO ====================
print(f'\n📄 Gerando relatório: {SAIDA_CSV}')
SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)

relatorio = []
for cluster_id in sorted(df['cluster'].unique()):
    if cluster_id == -1:
        continue

    sub = df[df['cluster'] == cluster_id]
    n = len(sub)

    # Amostra de títulos
    amostra = sub['titulo'].head(15).tolist()

    # Categoria mais comum
    cat_mode = sub['categoria'].mode()
    cat_comum = cat_mode.iloc[0] if not cat_mode.empty else '(vazio)'

    # Status mais comum
    status_mode = sub['status'].mode()
    status_comum = status_mode.iloc[0] if not status_mode.empty else '(vazio)'

    relatorio.append({
        'cluster_id': cluster_id,
        'n_tickets': n,
        'categoria_mais_comum': cat_comum,
        'status_mais_comum': status_comum,
        'amostra_titulos': ' | '.join(amostra),
    })

df_rel = pd.DataFrame(relatorio).sort_values('n_tickets', ascending=False)
df_rel.to_csv(SAIDA_CSV, index=False)

# ==================== 8. SALVA IDS + CLUSTERS ====================
print(f'💾 Salvando IDs + clusters: {SAIDA_IDS}')
df[['id', 'cluster']].to_csv(SAIDA_IDS, index=False)

# ==================== 9. RESUMO ====================
print('\n' + '=' * 70)
print('RESUMO DOS CLUSTERS')
print('=' * 70)
for _, row in df_rel.head(30).iterrows():  # top 30
    print(f'\n📦 Cluster {row["cluster_id"]} — {row["n_tickets"]} tickets')
    print(f'   Categoria: {row["categoria_mais_comum"]} | Status: {row["status_mais_comum"]}')
    print(f'   Amostra: {row["amostra_titulos"][:250]}...')

if len(df_rel) > 30:
    print(f'\n... e mais {len(df_rel) - 30} clusters (ver CSV)')

# ==================== 10. VISUALIZAÇÃO ====================
print('\n📊 Gerando visualização...')
import plotly.express as px

umap_2d = umap.UMAP(n_components=2, random_state=42).fit_transform(embeddings)
df['x'] = umap_2d[:, 0]
df['y'] = umap_2d[:, 1]
df['cluster_str'] = df['cluster'].astype(str)

fig = px.scatter(
    df,
    x='x', y='y',
    color='cluster_str',
    hover_data=['id', 'titulo', 'categoria'],
    title='Clusters de tickets (título + descrição + movimentações + mensagens)',
    height=800,
)
fig.write_html(SAIDA_HTML)
print(f'   Salvo em: {SAIDA_HTML}')