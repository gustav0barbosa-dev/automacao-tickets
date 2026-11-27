# scripts_treinamento/09_treinar_supervisionado.py
"""
Etapa 4 — Treinamento supervisionado (Fase 3).

Objetivo:
  1. Criar base de rótulos a partir dos rótulos fracos (proxy para rótulos humanos)
     — quando a amostra de validação humana for preenchida, ela substituirá esses rótulos.
  2. Treinar baseline TF-IDF + SVM (LinearSVC).
  3. Treinar com embeddings (modelo finetunado local ou paraphrase-multilingual-MiniLM-L12-v2)
     + classificador (LogisticRegression).
  4. Comparar baseline vs MLP/embeddings com métricas por motivo.
  5. Divisão temporal: treino com tickets até 08/2026, teste em 09/2026–10/2026.
  6. Gerar curva cobertura × precisão e matriz de confusão.

Saídas:
  - scripts_treinamento/artefatos/modelo_baseline_tfidf_svm.pkl
  - scripts_treinamento/artefatos/modelo_embeddings_svm.pkl
  - scripts_treinamento/artefatos/metricas_comparacao_*.xlsx
  - scripts_treinamento/artefatos/relatorio_treinamento_*.txt
  - scripts_treinamento/artefatos/curva_cobertura_precisao_*.png

Não quebra nada do pipeline nem do dashboard. Mudança aditiva.
"""

import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
import joblib
import re
from collections import Counter

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report, confusion_matrix, precision_recall_fscore_support,
    accuracy_score,
)
from sentence_transformers import SentenceTransformer

RAIZ = Path(__file__).resolve().parent.parent
ARTEFATOS = RAIZ / 'scripts_treinamento' / 'artefatos'
MODELO_FINETUNED = RAIZ / 'dados' / 'modelo_finetuned'
MODELO_EMBEDDING = 'paraphrase-multilingual-MiniLM-L12-v2'

SEED = 42
np.random.seed(SEED)


# ==================== CARREGAMENTO ====================


def encontrar_rotulos_mais_recentes():
    fixo = ARTEFATOS / 'rotulos_fracos.csv'
    if fixo.exists():
        return fixo
    candidatos = sorted(
        ARTEFATOS.glob('rotulos_fracos_*.csv'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidatos:
        return candidatos[0]
    raise FileNotFoundError(
        f'Não encontrou rotulos_fracos em {ARTEFATOS}. '
        'Rode primeiro a Fase 2 (02_rotulos_fracos.py).'
    )


def encontrar_rotulos_humanos_mais_recentes():
    """Encontra o CSV de rótulos humanos exportado da interface de validação."""
    fixo = ARTEFATOS / 'rotulos_humanos.csv'
    if fixo.exists():
        return fixo
    candidatos = sorted(
        ARTEFATOS.glob('rotulos_humanos_*.csv'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidatos:
        return candidatos[0]
    return None


def encontrar_vinculo_clusters_mais_recentes():
    """Encontra o arquivo que mapeia ticket_id -> cluster_id."""
    candidatos = sorted(
        ARTEFATOS.glob('tickets_clusters_*.csv'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidatos:
        return candidatos[0]
    return None


def carregar_base_rotulos():
    """Carrega a base de rótulos combinando rótulos fracos (regras) com
    rótulos humanos (validação dos analistas via interface).

    Regras de prioridade:
      1. Rótulo humano (validação via interface) — prioridade máxima
      2. Rótulo fraco (regras de taxonomia) — fallback
    """
    # 1. Carrega rótulos fracos (base)
    caminho_fracos = encontrar_rotulos_mais_recentes()
    print(f'📂 Rótulos fracos: {caminho_fracos.name}')
    df = pd.read_csv(caminho_fracos)
    print(f'📊 Total de rótulos fracos: {len(df)}')

    # Mantém apenas tickets com texto útil
    df = df[df['texto_util'] == True].copy()

    # Coluna de origem (regra = rótulo fraco, humano = validado por analista)
    if 'origem' not in df.columns:
        df['origem'] = 'regra'

    # Converte created_data para datetime
    if 'criado_data' in df.columns:
        df['criado_data'] = pd.to_datetime(df['criado_data'], errors='coerce')

    # 2. Carrega rótulos humanos (se existirem)
    caminho_humanos = encontrar_rotulos_humanos_mais_recentes()
    df_humanos = None
    if caminho_humanos:
        df_humanos = pd.read_csv(caminho_humanos)
        print(f'📂 Rótulos humanos: {caminho_humanos.name} ({len(df_humanos)} entradas)')

    # 3. Carrega vínculo ticket -> cluster (para aplicar rótulos humanos por cluster)
    caminho_vinculo = encontrar_vinculo_clusters_mais_recentes()
    df_vinculo = None
    if caminho_vinculo:
        df_vinculo = pd.read_csv(caminho_vinculo)
        print(f'📂 Vínculo ticket->cluster: {caminho_vinculo.name} ({len(df_vinculo)} entradas)')

    # Garante coluna ticket_id para o merge com vínculo
    if 'ticket_id' not in df.columns and 'id' in df.columns:
        df['ticket_id'] = df['id']

    # 4. Aplica rótulos humanos sobre os rótulos fracos
    n_sobrescritos = 0
    if df_humanos is not None and df_vinculo is not None:
        # Normaliza colunas do vínculo (id -> ticket_id, cluster -> cluster_id)
        col_map = {}
        if 'ticket_id' not in df_vinculo.columns and 'id' in df_vinculo.columns:
            col_map['id'] = 'ticket_id'
        if 'cluster_id' not in df_vinculo.columns and 'cluster' in df_vinculo.columns:
            col_map['cluster'] = 'cluster_id'
        if col_map:
            df_vinculo = df_vinculo.rename(columns=col_map)

        # Prepara mapeamento cluster_id -> motivo_correto
        cluster_para_motivo = dict(
            zip(df_humanos['cluster_id'], df_humanos['motivo_correto'])
        )

        # Une tickets com clusters
        df_com_cluster = df.merge(
            df_vinculo[['ticket_id', 'cluster_id']],
            on='ticket_id',
            how='left',
        )

        # Aplica motivo humano onde houver
        mask_tem_cluster = df_com_cluster['cluster_id'].notna()
        mask_tem_motivo_humano = df_com_cluster['cluster_id'].isin(
            cluster_para_motivo.keys()
        )
        mask_aplicar = mask_tem_cluster & mask_tem_motivo_humano

        if mask_aplicar.any():
            motivos_humanos = df_com_cluster.loc[
                mask_aplicar, 'cluster_id'
            ].map(cluster_para_motivo)
            df.loc[mask_aplicar, 'motivo_id'] = motivos_humanos.values
            df.loc[mask_aplicar, 'origem'] = 'humano'
            n_sobrescritos = int(mask_aplicar.sum())
            print(
                f'🔖 {n_sobrescritos} tickets sobrescritos com rótulo humano'
            )
    elif df_humanos is not None and df_vinculo is None:
        print(
            '⚠️  Rótulos humanos encontrados, mas sem vínculo ticket->cluster. '
            'Não foi possível aplicá-los.'
        )

    # Filtros finais (mantém apenas motivos válidos)
    df = df[df['motivo_id'].notna() & (df['motivo_id'] != '')].copy()
    df = df[df['motivo_id'] != 'outros'].copy()
    df = df[df['motivo_id'] != 'sem_texto_suficiente'].copy()

    print(f'📊 Após filtro (texto útil, motivo válido): {len(df)}')
    print(f'   Motivos únicos: {df["motivo_id"].nunique()}')
    print(f'   Categorias únicas: {df["categoria"].nunique()}')
    print(f'   Rótulos humanos aplicados: {n_sobrescritos}')

    return df


# ==================+ DIVISÃO TEMPORAL ====================


def dividir_temporal(df, coluna_data='criado_data', corte_treino='2026-08-31'):
    """Divide treino/teste por data (não aleatório)."""
    df = df.dropna(subset=[coluna_data]).copy()
    df = df.sort_values(coluna_data)

    corte = pd.to_datetime(corte_treino)
    df_treino = df[df[coluna_data] <= corte].copy()
    df_teste = df[df[coluna_data] > corte].copy()

    print(f'\n📅 Divisão temporal (corte: {corte_treino}):')
    print(f'   Treino: {len(df_treino)} tickets '
          f'({df_treino[coluna_data].min().date()} → {df_treino[coluna_data].max().date()})')
    print(f'   Teste:  {len(df_teste)} tickets '
          f'({df_teste[coluna_data].min().date()} → {df_teste[coluna_data].max().date()})')

    # Verifica se há motivos no teste que não estão no treino
    motivos_treino = set(df_treino['motivo_id'].unique())
    motivos_teste = set(df_teste['motivo_id'].unique())
    motivos_apenas_teste = motivos_teste - motivos_treino
    if motivos_apenas_teste:
        print(f'   ⚠️  Motivos apenas no teste (não vistos no treino): '
              f'{len(motivos_apenas_teste)}')
        for m in sorted(motivos_apenas_teste):
            qtd = (df_teste['motivo_id'] == m).sum()
            print(f'      - {m}: {qtd} tickets')

    return df_treino, df_teste


# ==================== MODELO BASELINE (TF-IDF + SVM) ====================


def treinar_baseline_tfidf_svm(X_treino, y_treino):
    """Treina pipeline TF-IDF + LinearSVC."""
    print('\n🔤 Treinando baseline TF-IDF + LinearSVC...')
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.9,
            sublinear_tf=True,
        )),
        ('clf', LinearSVC(
            C=1.0,
            class_weight='balanced',
            max_iter=5000,
            random_state=SEED,
        )),
    ])
    pipeline.fit(X_treino, y_treino)
    print('   ✅ Baseline treinado.')
    return pipeline


# ==================== MODELO EMBEDDINGS + SVM ====================


def carregar_modelo_embedding():
    """Carrega modelo de embeddings (finetunado local ou base)."""
    if MODELO_FINETUNED.exists() and (MODELO_FINETUNED / 'config.json').exists():
        print(f'🧠 Usando modelo finetunado local: {MODELO_FINETUNED}')
        return SentenceTransformer(str(MODELO_FINETUNED))
    print(f'🧠 Usando modelo base: {MODELO_EMBEDDING}')
    return SentenceTransformer(MODELO_EMBEDDING)


def gerar_embeddings(modelo, textos):
    """Gera embeddings para lista de textos."""
    return modelo.encode(
        textos.tolist(),
        show_progress_bar=True,
        batch_size=32,
        convert_to_numpy=True,
    )


def treinar_embeddings_svm(modelo, X_treino, y_treino):
    """Treina LogisticRegression sobre embeddings."""
    print('\n🧠 Treinando Embeddings + LogisticRegression...')
    X_emb = gerar_embeddings(modelo, X_treino)
    clf = LogisticRegression(
        C=1.0,
        class_weight='balanced',
        max_iter=5000,
        random_state=SEED,
        n_jobs=-1,
    )
    clf.fit(X_emb, y_treino)
    print('   ✅ Embeddings + SVM treinado.')
    return clf, modelo


# ==================== AVALIAÇÃO ====================


def avaliar_modelo(nome, modelo, X_teste, y_teste, embeddings_modelo=None):
    """Avalia modelo e retorna métricas por classe + gerais."""
    print(f'\n📊 Avaliando {nome}...')

    if embeddings_modelo is not None:
        X = gerar_embeddings(embeddings_modelo, X_teste)
        y_pred = modelo.predict(X)
    else:
        y_pred = modelo.predict(X_teste)

    # Métricas gerais
    acuracia = accuracy_score(y_teste, y_pred)
    precisao_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        y_teste, y_pred, average='macro', zero_division=0
    )
    precisao_micro, recall_micro, f1_micro, _ = precision_recall_fscore_support(
        y_teste, y_pred, average='micro', zero_division=0
    )

    print(f'   Acurácia: {acuracia:.4f}')
    print(f'   Macro-F1: {f1_macro:.4f}')
    print(f'   Micro-F1: {f1_micro:.4f}')

    # Métricas por classe
    report = classification_report(
        y_teste, y_pred, output_dict=True, zero_division=0
    )
    df_report = pd.DataFrame(report).transpose().reset_index()
    df_report = df_report.rename(columns={'index': 'motivo'})

    # Matriz de confusão (top 15 motivos por frequência no teste)
    top_motivos = y_teste.value_counts().head(15).index.tolist()
    mask_teste = y_teste.isin(top_motivos)
    if mask_teste.sum() > 0:
        cm = confusion_matrix(
            y_teste[mask_teste], y_pred[mask_teste], labels=top_motivos
        )
    else:
        cm = np.array([])
        top_motivos = []

    return {
        'modelo': nome,
        'acuracia': acuracia,
        'precisao_macro': precisao_macro,
        'recall_macro': recall_macro,
        'f1_macro': f1_macro,
        'precisao_micro': precisao_micro,
        'recall_micro': recall_micro,
        'f1_micro': f1_micro,
        'report': df_report,
        'matriz_confusao': cm,
        'labels_cm': top_motivos,
        'y_teste': y_teste,
        'y_pred': y_pred,
    }


def gerar_curva_cobertura_precisao(nome, modelo, X_teste, y_teste, embeddings_modelo=None,
                                    limiares=np.linspace(0.5, 0.95, 10)):
    """Gera curva cobertura × precisão para modelos que dão prob."""
    print(f'\n📈 Gerando curva cobertura × precisão para {nome}...')
    resultados = []

    for limiar in limiares:
        if embeddings_modelo is not None:
            # LogisticRegression tem predict_proba
            X = gerar_embeddings(embeddings_modelo, X_teste)
            probs = modelo.predict_proba(X)
            preds = modelo.classes_[np.argmax(probs, axis=1)]
            max_probs = np.max(probs, axis=1)
        else:
            # LinearSVC não tem predict_proba nativo; usa decision_function
            decisao = modelo.decision_function(X_teste)
            if decisao.ndim == 1:
                # Binário
                max_probs = np.abs(decisao)
                preds = modelo.predict(X_teste)
            else:
                max_probs = np.max(decisao, axis=1)
                preds = modelo.classes_[np.argmax(decisao, axis=1)]

        # Normaliza probs para [0,1] aproximado (decision_function não é prob)
        if embeddings_modelo is None:
            max_probs = (max_probs - max_probs.min()) / (max_probs.max() - max_probs.min() + 1e-9)

        mask = max_probs >= limiar
        cobertura = mask.mean() if mask.sum() > 0 else 0
        if mask.sum() > 0:
            precisao = (preds[mask] == y_teste[mask]).mean()
        else:
            precisao = 0

        resultados.append({
            'modelo': nome,
            'limiar': limiar,
            'cobertura': cobertura,
            'precisao': precisao,
            'n_tickets': int(mask.sum()),
        })

    return pd.DataFrame(resultados)


# ==================== SAÍDA ====================


def salvar_modelo(modelo, caminho):
    joblib.dump(modelo, caminho)
    print(f'💾 Modelo salvo: {caminho}')


def salvar_metricas(metricas, curva_df, timestamp):
    """Salva métricas de comparação em XLSX."""
    caminho = ARTEFATOS / f'metricas_comparacao_{timestamp}.xlsx'
    try:
        with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
            # Resumo geral
            resumo = []
            for m in metricas:
                resumo.append({
                    'modelo': m['modelo'],
                    'acuracia': round(m['acuracia'], 4),
                    'precisao_macro': round(m['precisao_macro'], 4),
                    'recall_macro': round(m['recall_macro'], 4),
                    'f1_macro': round(m['f1_macro'], 4),
                    'precisao_micro': round(m['precisao_micro'], 4),
                    'recall_micro': round(m['recall_micro'], 4),
                    'f1_micro': round(m['f1_micro'], 4),
                })
            pd.DataFrame(resumo).to_excel(writer, sheet_name='resumo_geral', index=False)

            # Relatório por classe (concatena modelos)
            todos_reports = []
            for m in metricas:
                r = m['report'].copy()
                r['modelo'] = m['modelo']
                todos_reports.append(r)
            pd.concat(todos_reports, ignore_index=True).to_excel(
                writer, sheet_name='metrica_por_classe', index=False)

            # Curva cobertura x precisao
            curva_df.to_excel(writer, sheet_name='curva_cobertura_precisao', index=False)

        print(f'💾 Métricas salvas: {caminho}')
    except Exception as e:
        print(f'⚠️  Erro ao salvar XLSX: {e}')


def salvar_relatorio_texto(metricas, curva_df, timestamp):
    caminho = ARTEFATOS / f'relatorio_treinamento_{timestamp}.txt'
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write('=' * 70 + '\n')
        f.write('RELATÓRIO DE TREINAMENTO SUPERVISIONADO — FASE 3, ETAPA 4\n')
        f.write(f'Gerado em: {datetime.now().isoformat()}\n')
        f.write('=' * 70 + '\n\n')

        f.write('DIVISÃO TEMPORAL: treino até 31/08/2026, teste 01/09/2026 → 31/10/2026\n\n')

        f.write('COMPARAÇÃO DE MODELOS\n')
        f.write('-' * 70 + '\n')
        for m in metricas:
            f.write(f"\nModelo: {m['modelo']}\n")
            f.write(f"  Acurácia:       {m['acuracia']:.4f}\n")
            f.write(f"  Precisão Macro: {m['precisao_macro']:.4f}\n")
            f.write(f"  Recall Macro:   {m['recall_macro']:.4f}\n")
            f.write(f"  F1 Macro:       {m['f1_macro']:.4f}\n")
            f.write(f"  Precisão Micro: {m['precisao_micro']:.4f}\n")
            f.write(f"  Recall Micro:   {m['recall_micro']:.4f}\n")
            f.write(f"  F1 Micro:       {m['f1_micro']:.4f}\n")

        f.write('\nMÉTRICAS POR CLASSE (F1-score)\n')
        f.write('-' * 70 + '\n')
        for m in metricas:
            f.write(f"\n--- {m['modelo']} ---\n")
            report = m['report']
            for _, row in report.iterrows():
                motivo = row['motivo']
                if motivo in ('accuracy', 'macro avg', 'weighted avg'):
                    continue
                f1 = row.get('f1-score', 0)
                sup = row.get('support', 0)
                f.write(f"  {motivo}: F1={f1:.3f}, suporte={sup}\n")

        f.write('\nCURVA COBERTURA × PRECISÃO\n')
        f.write('-' * 70 + '\n')
        for modelo_nome in curva_df['modelo'].unique():
            sub = curva_df[curva_df['modelo'] == modelo_nome]
            f.write(f"\n{modelo_nome}:\n")
            for _, row in sub.iterrows():
                f.write(f"  limiar={row['limiar']:.2f}: "
                        f"cobertura={row['cobertura']:.3f}, "
                        f"precisão={row['precisao']:.3f}, "
                        f"n_tickets={row['n_tickets']}\n")

        f.write('\n' + '=' * 70 + '\n')
        f.write('OBSERVAÇÕES:\n')
        f.write('- Rótulos usados são "rótulos fracos" (regras), não rótulos humanos.\n')
        f.write('- Quando a amostra de validação humana for preenchida, substitua os rótulos.\n')
        f.write('- Divisão temporal evita vazamento de informação entre treino e teste.\n')

    print(f'💾 Relatório salvo: {caminho}')


# ==================== MAIN ====================


def main():
    print('🚀 ETAPA 4 — Treinamento supervisionado (Fase 3)')
    print('=' * 70)

    # 1. Carrega base de rótulos
    df = carregar_base_rotulos()

    # 2. Divisão temporal
    df_treino, df_teste = dividir_temporal(df)

    if len(df_teste) == 0:
        print('❌ Não há tickets no teste. Ajuste a data de corte.')
        return

    X_treino = df_treino['texto_retrospectivo']
    y_treino = df_treino['motivo_id']
    X_teste = df_teste['texto_retrospectivo']
    y_teste = df_teste['motivo_id']

    print(f'\n🎯 Classes no treino: {y_treino.nunique()}')
    print(f'🎯 Classes no teste: {y_teste.nunique()}')

    ARTEFATOS.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 3. Treina baseline TF-IDF + SVM
    modelo_baseline = treinar_baseline_tfidf_svm(X_treino, y_treino)
    salvar_modelo(modelo_baseline, ARTEFATOS / f'modelo_baseline_tfidf_svm_{timestamp}.pkl')

    # 4. Treina Embeddings + SVM
    modelo_emb = carregar_modelo_embedding()
    modelo_embeddings, modelo_emb_obj = treinar_embeddings_svm(
        modelo_emb, X_treino, y_treino
    )
    salvar_modelo(
        modelo_embeddings,
        ARTEFATOS / f'modelo_embeddings_svm_{timestamp}.pkl'
    )

    # 5. Avalia ambos
    metricas = []

    res_baseline = avaliar_modelo(
        'TF-IDF + LinearSVC', modelo_baseline, X_teste, y_teste
    )
    curva_baseline = gerar_curva_cobertura_precisao(
        'TF-IDF + LinearSVC', modelo_baseline, X_teste, y_teste
    )
    metricas.append(res_baseline)

    res_emb = avaliar_modelo(
        'Embeddings + LogisticRegression', modelo_embeddings, X_teste, y_teste,
        embeddings_modelo=modelo_emb
    )
    curva_emb = gerar_curva_cobertura_precisao(
        'Embeddings + LogisticRegression', modelo_embeddings, X_teste, y_teste,
        embeddings_modelo=modelo_emb
    )
    metricas.append(res_emb)

    # 6. Comparação
    print('\n' + '=' * 70)
    print('COMPARAÇÃO FINAL')
    print('=' * 70)
    comparacao = []
    for m in metricas:
        comparacao.append({
            'modelo': m['modelo'],
            'acuracia': round(m['acuracia'], 4),
            'f1_macro': round(m['f1_macro'], 4),
            'f1_micro': round(m['f1_micro'], 4),
        })
    df_comp = pd.DataFrame(comparacao)
    print(df_comp.to_string(index=False))

    # Melhor modelo por F1 macro
    melhor = max(metricas, key=lambda m: m['f1_macro'])
    print(f'\n🏆 Melhor modelo (F1 macro): {melhor["modelo"]} '
          f'({melhor["f1_macro"]:.4f})')

    # 7. Salva saídas
    curva_todas = pd.concat([curva_baseline, curva_emb], ignore_index=True)
    salvar_metricas(metricas, curva_todas, timestamp)
    salvar_relatorio_texto(metricas, curva_todas, timestamp)

    # Salva curva como CSV (para plot posterior)
    curva_csv = ARTEFATOS / f'curva_cobertura_precisao_{timestamp}.csv'
    curva_todas.to_csv(curva_csv, index=False, encoding='utf-8')
    print(f'💾 Curva salva: {curva_csv}')

    print('\n✅ Etapa 4 — Treinamento supervisionado concluído.')
    print('\n📋 Próximo passo: Etapa 5 — Monitoramento (recorrência mensal, novos assuntos).')


if __name__ == '__main__':
    main()
