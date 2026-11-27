"""
Busca semântica de tickets COM CONTEÚDO COMPLETO.
Usa título + descrição + solução + movimentações + mensagens.
"""
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
EMBEDDINGS_CACHE = RAIZ / 'dados' / 'embeddings_completo.npy'
IDS_CACHE = RAIZ / 'dados' / 'embeddings_ids.npy'

# Nome do modelo (pode ser trocado para './dados/modelo_finetuned' depois do treino)
NOME_MODELO = './dados/modelo_finetuned'


def limpar_placeholders(texto):
    """Remove placeholders de anonimização."""
    if not texto:
        return ''
    texto = re.sub(r'<[A-Z_]+>', '', str(texto))
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


def carregar_tickets_com_contexto():
    """Carrega tickets + descrição + solução + movs + msgs."""
    conn = sqlite3.connect(BANCO)

    df = pd.read_sql('''
        SELECT id, titulo, descricao, solucao, categoria, status
        FROM tickets
        WHERE titulo NOT LIKE '%0000000000%'
          AND descricao NOT LIKE '%<TELEFONE>%'
          AND descricao NOT LIKE '%<CPF>%'
    ''', conn)
    df['id'] = df['id'].astype('int64')

    movs = pd.read_sql('''
        SELECT ticket_id, comentario
        FROM movimentacoes
        WHERE comentario IS NOT NULL AND LENGTH(comentario) > 30
        ORDER BY ticket_id, data_movimentacao ASC
    ''', conn)
    movs['ticket_id'] = movs['ticket_id'].astype('int64')

    msgs = pd.read_sql('''
        SELECT ticket_id, conteudo
        FROM mensagens
        WHERE conteudo IS NOT NULL AND LENGTH(conteudo) > 30
        ORDER BY ticket_id, data_hora ASC
    ''', conn)
    msgs['ticket_id'] = msgs['ticket_id'].astype('int64')

    conn.close()

    movs_agg = movs.groupby('ticket_id')['comentario'].apply(
        lambda x: ' '.join(x.astype(str).tolist())[:2000]
    ).reset_index()
    movs_agg.columns = ['ticket_id', 'texto_movs']

    msgs_agg = msgs.groupby('ticket_id')['conteudo'].apply(
        lambda x: ' '.join(x.astype(str).tolist())[:2000]
    ).reset_index()
    msgs_agg.columns = ['ticket_id', 'texto_msgs']

    df = df.merge(movs_agg, left_on='id', right_on='ticket_id', how='left')
    df = df.merge(msgs_agg, left_on='id', right_on='ticket_id', how='left')
    df = df.drop(columns=['ticket_id_x', 'ticket_id_y'], errors='ignore')

    df['texto_movs'] = df['texto_movs'].fillna('')
    df['texto_msgs'] = df['texto_msgs'].fillna('')

    return df


def montar_texto(row):
    def tratar(valor, max_chars):
        if pd.isna(valor):
            return ''
        texto = limpar_placeholders(str(valor))
        return texto[:max_chars]

    titulo = tratar(row['titulo'], 200)
    descricao = tratar(row['descricao'], 800)
    solucao = tratar(row['solucao'], 400)
    movs = tratar(row['texto_movs'], 200)
    msgs = tratar(row['texto_msgs'], 200)

    return f"{titulo}. {descricao} {solucao} {movs} {msgs}".strip()


# ==================== MAIN ====================
if __name__ == '__main__':
    # Força regeneração
    if '--regen' in sys.argv:
        print('🗑️  Apagando cache...')
        EMBEDDINGS_CACHE.unlink(missing_ok=True)
        IDS_CACHE.unlink(missing_ok=True)

    if len(sys.argv) < 2:
        print('Uso: python scripts_treinamento/buscar_tickets.py "sua busca"')
        sys.exit(1)

    query = sys.argv[1]

    # Carrega modelo
    print(f'🧠 Carregando modelo: {NOME_MODELO}')
    model = SentenceTransformer(NOME_MODELO)

    # Carrega ou gera embeddings
    if EMBEDDINGS_CACHE.exists() and IDS_CACHE.exists() and '--regen' not in sys.argv:
        embeddings = np.load(EMBEDDINGS_CACHE)
        ids = np.load(IDS_CACHE)
        print(f'✅ Embeddings em cache: {len(ids)}')
    else:
        print('🧠 Gerando embeddings COM descrição + solução + movs + msgs...')
        df = carregar_tickets_com_contexto()
        textos = df.apply(montar_texto, axis=1).tolist()

        print(f'\n📝 Exemplo de texto:')
        for i in range(min(3, len(textos))):
            print(f'   [{i}] {textos[i][:200]}...')
        print()

        embeddings = model.encode(textos, show_progress_bar=True, batch_size=32)
        ids = df['id'].values

        np.save(EMBEDDINGS_CACHE, embeddings)
        np.save(IDS_CACHE, ids)
        print(f'   Shape: {embeddings.shape}')

    # Busca
    print(f'\n🔍 Buscando: "{query}"')
    query_emb = model.encode([query])[0]

    similaridades = np.dot(embeddings, query_emb) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_emb)
    )

    top_k = np.argsort(similaridades)[-30:][::-1]
    top_ids = ids[top_k]
    top_scores = similaridades[top_k]

    conn = sqlite3.connect(BANCO)
    ids_str = ','.join(str(int(i)) for i in top_ids)
    df_result = pd.read_sql(f'''
        SELECT id, titulo, categoria, status, criado_data
        FROM tickets WHERE id IN ({ids_str})
    ''', conn)
    conn.close()

    df_result = df_result.set_index('id').loc[top_ids].reset_index()
    df_result['score'] = top_scores

    print(f'\n📊 Top 30 tickets mais similares:\n')
    for _, row in df_result.iterrows():
        print(f'  [{row["score"]:.3f}] #{row["id"]} — {row["titulo"][:70]}')
        print(f'      {row["categoria"]} | {row["status"]} | {row["criado_data"]}')