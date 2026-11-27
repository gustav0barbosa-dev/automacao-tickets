# scripts_treinamento/06_descobrir_grupos.py
"""
Fase 2 (complemento) — Descoberta de grupos emergentes via clustering não supervisionado.

Objetivo: descobrir novos motivos nos tickets que as regras não conseguiram classificar
("outros / não classificado") e no subgrupo ambíguo "Retorno para determinado fluxo"
(dentro da categoria "Retorno de Tarefa", 17 tickets no DOCX).

Etapas:
  1. Carrega rotulos_fracos.csv (Fase 2 revisada).
  2. Filtra tickets com motivo_id == 'outros' (clustering emergente geral).
  3. Filtra tickets da categoria 'Retorno de Tarefa' com motivo_id == 'retorno_para_determinado_fluxo'
     (descoberta direcionada no subgrupo ambíguo).
  4. Gera embeddings locais (modelo finetunado em dados/modelo_finetuned/ ou
     paraphrase-multilingual-MiniLM-L12-v2 como fallback).
  5. Reduz dimensão com UMAP e clusteriza com HDBSCAN.
  6. Para cada cluster: extrai termos característicos via c-TF-IDF, mostra tamanho,
     categorias dominantes e 5 títulos de exemplo (já anonimizados).
  7. Salva relatório em scripts_treinamento/artefatos/grupos_emergentes_YYYYMMDD_HHMMSS.xlsx|csv.

Não quebra nada do pipeline nem do dashboard. Mudança aditiva.
"""

import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import hdbscan
import umap
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_distances

RAIZ = Path(__file__).resolve().parent.parent
ARTEFATOS = RAIZ / 'scripts_treinamento' / 'artefatos'
MODELO_FINETUNED = RAIZ / 'dados' / 'modelo_finetuned'

MODELO_EMBEDDING = 'paraphrase-multilingual-MiniLM-L12-v2'


# ==================== CARREGAMENTO ====================


def encontrar_rotulos_mais_recentes():
    candidatos = sorted(
        ARTEFATOS.glob('rotulos_fracos_*.csv'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    # Fallback para o nome fixo
    fixo = ARTEFATOS / 'rotulos_fracos.csv'
    if fixo.exists():
        return fixo
    if candidatos:
        return candidatos[0]
    raise FileNotFoundError(
        f'Não encontrou rotulos_fracos em {ARTEFATOS}. '
        'Rode primeiro a Fase 2 (02_rotulos_fracos.py).'
    )


def carregar_modelo_embedding():
    """Tenta usar o modelo finetunado local; senão, baixa o base."""
    if MODELO_FINETUNED.exists() and (MODELO_FINETUNED / 'config.json').exists():
        print(f'🧠 Usando modelo finetunado local: {MODELO_FINETUNED}')
        return SentenceTransformer(str(MODELO_FINETUNED))
    print(f'🧠 Baixando/usando modelo base: {MODELO_EMBEDDING}')
    return SentenceTransformer(MODELO_EMBEDDING)


# ==================== CLUSTERING ====================


def clusterizar_textos(textos, modelo, min_cluster_size=15, min_samples=5):
    """
    Gera embeddings, reduz com UMAP e clusteriza com HDBSCAN.
    Retorna (df_com_clusters, embeddings, umap_emb).
    """
    print(f'   Gerando embeddings para {len(textos)} textos...')
    embeddings = modelo.encode(
        textos.tolist(),
        show_progress_bar=True,
        batch_size=32,
        convert_to_numpy=True,
    )
    print(f'   Shape dos embeddings: {embeddings.shape}')

    print('   Reduzindo dimensão (UMAP)...')
    n_neighbors = min(15, len(textos) - 1) if len(textos) > 2 else 2
    umap_emb = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=5,
        min_dist=0.0,
        metric='cosine',
        random_state=42,
    ).fit_transform(embeddings)

    print('   Clusterizando (HDBSCAN)...')
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='euclidean',
        cluster_selection_method='eom',
    )
    clusters = clusterer.fit_predict(umap_emb)

    n_clusters = len(set(clusters)) - (1 if -1 in clusters else 0)
    n_ruido = int((clusters == -1).sum())
    print(f'   {n_clusters} clusters encontrados')
    print(f'   {n_ruido} tickets como ruído')

    return clusters, embeddings, umap_emb


# ==================== C-TF-IDF PARA TERMOS CARACTERÍSTICOS ====================


def extrair_termos_cluster(textos_cluster, top_n=8):
    """
    Extrai os top_n termos mais característicos de um cluster usando c-TF-IDF
    (TF-IDF dentro do cluster, normalizado pelo tamanho do cluster).
    """
    if len(textos_cluster) == 0:
        return []
    vectorizer = TfidfVectorizer(
        max_features=200,
        ngram_range=(1, 2),
        stop_words=None,  # PT-BR sem stopwords prontas; mantemos termos de negócio
        min_df=1,
    )
    try:
        tfidf = vectorizer.fit_transform(textos_cluster.tolist())
        feature_names = vectorizer.get_feature_names_out()
        # Soma TF-IDF por termo (c-TF-IDF simplificado)
        scores = np.asarray(tfidf.sum(axis=0)).ravel()
        top_idx = scores.argsort()[::-1][:top_n]
        return [(feature_names[i], round(float(scores[i]), 3)) for i in top_idx if scores[i] > 0]
    except Exception:
        return []


# ==================== RELATÓRIO ====================


def gerar_relatorio_cluster(df_subset, coluna_texto, modelo, prefixo, min_cluster_size=15):
    """
    Executa clustering em um subconjunto e gera um DataFrame de relatório
    com um linha por cluster.
    """
    textos = df_subset[coluna_texto].fillna('')
    clusters, embeddings, umap_emb = clusterizar_textos(
        textos, modelo, min_cluster_size=min_cluster_size
    )

    df_result = df_subset.copy()
    df_result['cluster'] = clusters

    relatorio = []
    for cluster_id in sorted(df_result['cluster'].unique()):
        sub = df_result[df_result['cluster'] == cluster_id]
        n = len(sub)

        if cluster_id == -1:
            relatorio.append({
                'cluster_id': -1,
                'tipo': 'ruido',
                'n_tickets': n,
                'terros_caracteristicos': '',
                'categorias_dominantes': '',
                'exemplos_titulos': '',
                'motivo_sugerido': 'Ruído / sem padrão claro',
            })
            continue

        # Termos característicos (c-TF-IDF sobre títulos + descrição)
        textos_cluster = sub[coluna_texto].fillna('')
        termos = extrair_termos_cluster(textos_cluster, top_n=8)
        termos_str = ' | '.join(f'{t} ({s})' for t, s in termos)

        # Categorias dominantes
        cats = sub['categoria'].value_counts().head(3)
        cats_str = ' | '.join(f'{c} ({q})' for c, q in cats.items())

        # Exemplos de títulos (já anonimizados)
        exemplos = sub['titulo'].head(5).tolist()
        exemplos_str = ' | '.join(str(e)[:80] for e in exemplos)

        # Motivo sugerido: os 3 primeiros termos
        motivo_sugerido = ' + '.join(t for t, _ in termos[:3]) if termos else '(sem termo)'

        relatorio.append({
            'cluster_id': cluster_id,
            'tipo': 'cluster',
            'n_tickets': n,
            'terros_caracteristicos': termos_str,
            'categorias_dominantes': cats_str,
            'exemplos_titulos': exemplos_str,
            'motivo_sugerido': motivo_sugerido,
        })

    df_rel = pd.DataFrame(relatorio).sort_values('n_tickets', ascending=False)
    return df_rel, df_result


# ==================== MAIN ====================


def main():
    rotulos_path = encontrar_rotulos_mais_recentes()
    print(f'📂 Rotulados: {rotulos_path.name}')
    df = pd.read_csv(rotulos_path)
    print(f'📊 Total de tickets: {len(df)}')

    modelo = carregar_modelo_embedding()

    # Garante coluna texto
    coluna_texto = 'texto_retrospectivo' if 'texto_retrospectivo' in df.columns else 'descricao'
    if coluna_texto not in df.columns:
        coluna_texto = 'titulo'

    ARTEFATOS.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    resultados = []

    # ============================================================
    # 1. CLUSTERING EMERGENTE GERAL nos tickets "outros"
    # ============================================================
    print('\n' + '=' * 70)
    print('1. CLUSTERING EMERGENTE — tickets rotulados como "outros"')
    print('=' * 70)
    df_outros = df[df['motivo_id'] == 'outros'].copy()
    print(f'   Tickets em "outros": {len(df_outros)}')

    if len(df_outros) >= 30:
        rel_outros, df_outros_cluster = gerar_relatorio_cluster(
            df_outros, coluna_texto, modelo, prefixo='outros', min_cluster_size=20
        )
        print(f'\n📦 Clusters emergentes em "outros": {len(rel_outros[rel_outros["tipo"]=="cluster"])}')
        for _, row in rel_outros.head(20).iterrows():
            if row['tipo'] == 'cluster':
                print(f"\n   🔹 Cluster {row['cluster_id']} — {row['n_tickets']} tickets")
                print(f"      Termos: {row['terros_caracteristicos'][:150]}")
                print(f"      Categorias: {row['categorias_dominantes'][:100]}")
                print(f"      Exemplos: {row['exemplos_titulos'][:150]}")
                print(f"      Motivo sugerido: {row['motivo_sugerido']}")
        resultados.append(rel_outros.assign(origem='outros'))
    else:
        print('   Poucos tickets para clustering. Pulando.')
        rel_outros = pd.DataFrame()

    # ============================================================
    # 2. DESCOBERTA DIRECIONADA — "Retorno para determinado fluxo"
    #    dentro da categoria "Retorno de Tarefa"
    # ============================================================
    print('\n' + '=' * 70)
    print('2. DESCOBERTA DIRECIONADA — "Retorno para determinado fluxo"')
    print('   (categoria: Retorno de Tarefa, subgrupo ambíguo do DOCX)')
    print('=' * 70)
    df_retorno = df[
        (df['categoria'] == 'Retorno de Tarefa') &
        (df['motivo_id'] == 'retorno_para_determinado_fluxo')
    ].copy()
    print(f'   Tickets encontrados: {len(df_retorno)}')

    if len(df_retorno) >= 10:
        rel_retorno, df_retorno_cluster = gerar_relatorio_cluster(
            df_retorno, coluna_texto, modelo, prefixo='retorno_fluxo', min_cluster_size=5
        )
        print(f'\n📦 Clusters em "Retorno para determinado fluxo": {len(rel_retorno[rel_retorno["tipo"]=="cluster"])}')
        for _, row in rel_retorno.head(15).iterrows():
            if row['tipo'] == 'cluster':
                print(f"\n   🔹 Cluster {row['cluster_id']} — {row['n_tickets']} tickets")
                print(f"      Termos: {row['terros_caracteristicos'][:150]}")
                print(f"      Categorias: {row['categorias_dominantes'][:100]}")
                print(f"      Exemplos: {row['exemplos_titulos'][:150]}")
                print(f"      Motivo sugerido: {row['motivo_sugerido']}")
        resultados.append(rel_retorno.assign(origem='retorno_para_determinado_fluxo'))
    else:
        print('   Poucos tickets para clustering direcionado. Pulando.')
        rel_retorno = pd.DataFrame()

    # ============================================================
    # Salvar relatório consolidado
    # ============================================================
    if resultados:
        df_consolidado = pd.concat(resultados, ignore_index=True)
        caminho_xlsx = ARTEFATOS / f'grupos_emergentes_{timestamp}.xlsx'
        try:
            df_consolidado.to_excel(caminho_xlsx, index=False, engine='openpyxl')
            print(f'\n💾 Relatório de grupos emergentes salvo: {caminho_xlsx}')
        except Exception as e:
            caminho_csv = caminho_xlsx.with_suffix('.csv')
            df_consolidado.to_csv(caminho_csv, index=False, encoding='utf-8')
            print(f'⚠️  Não foi possível salvar XLSX ({e}). Salvando CSV: {caminho_csv}')
            caminho_xlsx = caminho_csv

        # Salvar também os tickets com cluster atribuído (para uso na Fase 6/7)
        dfs_ids = []
        if len(df_outros) >= 30 and not df_outros_cluster.empty:
            dfs_ids.append(df_outros_cluster[['id', 'cluster']])
        if len(df_retorno) >= 10 and not df_retorno_cluster.empty:
            dfs_ids.append(df_retorno_cluster[['id', 'cluster']])
        if dfs_ids:
            df_cluster_ids = pd.concat(dfs_ids, ignore_index=True)
            caminho_ids = ARTEFATOS / f'tickets_clusters_{timestamp}.csv'
            df_cluster_ids.to_csv(caminho_ids, index=False, encoding='utf-8')
            print(f'💾 IDs + clusters salvos: {caminho_ids} ({len(df_cluster_ids)} tickets)')
        else:
            print('⚠️  Não há clusters com tickets suficientes para salvar vínculo ticket→cluster.')

        print('\n📝 PRÓXIMO PASSO: revisar os motivos sugeridos e adicionar os aprovados')
        print('   à config/taxonomia_motivos.yaml antes da Fase 3.')
        print('\n✅ Descoberta de grupos emergentes concluída.')
    else:
        print('\n⚠️  Não foi possível gerar clusters.')


if __name__ == '__main__':
    main()
