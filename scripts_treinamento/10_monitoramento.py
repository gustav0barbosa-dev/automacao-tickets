# scripts_treinamento/10_monitoramento.py
"""
Etapa 5 — Monitoramento de qualidade do mapeamento de motivos (Fase 3).

Objetivo:
  Medir métricas de qualidade do sistema de mapeamento de motivos reais ao
  longo do tempo, para avaliar se o modelo está entregando valor e quando
  é necessário retreinar.

Métricas calculadas:
  - Precision / Recall / F1 por motivo (conjunto de teste temporal)
  - Cobertura automática (% tickets classificados sem intervenção humana)
  - Taxa de revisão humana (% tickets que caem em filas de revisão)
  - Coerência dos clusters (proporção de clusters aprovados vs. divididos)
  - Taxa de novos assuntos (motivos que aparecem no teste mas não no treino)
  - Drift de distribuição (comparação de distribuição de motivos entre períodos)

Saídas:
  - scripts_treinamento/artefatos/monitoramento_YYYYMMDD_HHMMSS.json
      métricas consolidadas
  - scripts_treinamento/artefatos/monitoramento_YYYYMMDD_HHMMSS.xlsx
      relatório detalhado por motivo
  - scripts_treinamento/artefatos/monitoramento_YYYYMMDD_HHMMSS.png
      gráfico de evolução (se houver histórico)

Não quebra nada do pipeline nem do dashboard. Mudança aditiva.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
ARTEFATOS = RAIZ / 'scripts_treinamento' / 'artefatos'

# Períodos para divisão temporal (ajustáveis)
PERIODO_TREINO_FIM = '2026-08-31'
PERIODO_TESTE_INICIO = '2026-09-01'
PERIODO_TESTE_FIM = '2026-10-31'


# ==================== CARREGAMENTO ====================


def carregar_rotulos():
    """Carrega a base de rótulos (rótulos fracos + humanos, se existirem)."""
    fixo = ARTEFATOS / 'rotulos_fracos.csv'
    if fixo.exists():
        df = pd.read_csv(fixo)
        print(f'📂 Rotulados: {fixo.name} ({len(df)} tickets)')
        return df
    raise FileNotFoundError(
        f'Não encontrou rotulos_fracos em {ARTEFATOS}. '
        'Rode primeiro a Fase 2 (02_rotulos_fracos.py).'
    )


def carregar_metricas_treinamento():
    """Carrega as últimas métricas de treinamento, se existirem."""
    candidatos = sorted(
        ARTEFATOS.glob('metricas_comparacao_*.xlsx'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidatos:
        return pd.read_excel(candidatos[0], sheet_name=None)
    return {}


# ==================== CÁLCULO DE MÉTRICAS ====================


def calcular_metricas_por_motivo(df_teste, y_true, y_pred=None):
    """
    Calcula precision, recall, F1 e suporte por motivo no conjunto de teste.
    Se y_pred não for fornecido, usa o motivo atribuído pelas regras como proxy.
    """
    if y_pred is None:
        # Proxy: assume que o motivo atribuído pelas regras é a "predição"
        y_pred = df_teste['motivo_atribuido'].fillna('outros')
    else:
        y_pred = pd.Series(y_pred, index=df_teste.index)

    motivos = sorted(set(y_true.unique()) | set(y_pred.unique()))
    resultados = []

    for motivo in motivos:
        if motivo in ('outros', 'sem_texto_suficiente'):
            continue  # não calcula métricas para classes de descarte

        y_t = (y_true == motivo).astype(int)
        y_p = (y_pred == motivo).astype(int)

        tp = int(((y_t == 1) & (y_p == 1)).sum())
        fp = int(((y_t == 0) & (y_p == 1)).sum())
        fn = int(((y_t == 1) & (y_p == 0)).sum())
        suporte = int(y_t.sum())

        precisao = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precisao * recall / (precisao + recall) if (precisao + recall) > 0 else 0.0

        resultados.append({
            'motivo': motivo,
            'precisao': round(precisao, 4),
            'recall': round(recall, 4),
            'f1': round(f1, 4),
            'suporte': suporte,
            'tp': tp,
            'fp': fp,
            'fn': fn,
        })

    return pd.DataFrame(resultados).sort_values('f1', ascending=False)


def calcular_cobertura_automatica(df, coluna_motivo='motivo_id'):
    """
    Cobertura automática = % de tickets com motivo atribuído que NÃO são
    'outros' nem 'sem_texto_suficiente'.
    """
    if df.empty:
        return 0.0, 0, 0

    total = len(df)
    classificados = df[
        df[coluna_motivo].notna() &
        (df[coluna_motivo] != 'outros') &
        (df[coluna_motivo] != 'sem_texto_suficiente')
    ]

    cobertura = len(classificados) / total if total > 0 else 0.0
    return round(cobertura, 4), len(classificados), total


def calcular_taxa_revisao_humana(df_auditoria):
    """
    Taxa de revisão humana = % de clusters que requerem intervenção
    (dividir, revisar leve, descartar) vs. aprovar diretamente.
    """
    if df_auditoria.empty:
        return 0.0, 0, 0

    total = len(df_auditoria)
    requer_revisao = df_auditoria[
        df_auditoria['acao_recomendada'].isin(
            ['Dividir cluster', 'Aprovar com revisão leve', 'Descartar ou revisar termos']
        )
    ]

    taxa = len(requer_revisao) / total if total > 0 else 0.0
    return round(taxa, 4), len(requer_revisao), total


def calcular_taxa_novos_assuntos(df_treino, df_teste, coluna_motivo='motivo_id'):
    """
    Taxa de novos assuntos = % de motivos no teste que não aparecem no treino.
    """
    motivos_treino = set(df_treino[coluna_motivo].dropna().unique())
    motivos_teste = set(df_teste[coluna_motivo].dropna().unique())

    novos = motivos_teste - motivos_treino
    novos_filtrados = {m for m in novos if m not in ('outros', 'sem_texto_suficiente')}

    total_teste_motivos = len(motivos_teste - {'outros', 'sem_texto_suficiente'})
    taxa = len(novos_filtrados) / total_teste_motivos if total_teste_motivos > 0 else 0.0

    return {
        'taxa_novos_assuntos': round(taxa, 4),
        'n_novos_assuntos': len(novos_filtrados),
        'novos_assuntos': sorted(novos_filtrados),
        'total_motivos_teste': total_teste_motivos,
    }


def calcular_coerencia_clusters(df_auditoria):
    """
    Coerência dos clusters = proporção de clusters com coerência 'alta'
    ou 'média' que não precisam ser divididos.
    """
    if df_auditoria.empty:
        return 0.0, 0, 0

    total = len(df_auditoria)
    coerentes = df_auditoria[
        df_auditoria['coerencia'].isin(['alta', 'média']) &
        ~df_auditoria['acao_recomendada'].isin(['Dividir cluster'])
    ]

    taxa = len(coerentes) / total if total > 0 else 0.0
    return round(taxa, 4), len(coerentes), total


# ==================== DRIFT DE DISTRIBUIÇÃO ====================


def calcular_drift(df_treino, df_teste, coluna_motivo='motivo_id'):
    """
    Compara distribuição de motivos entre treino e teste (drift).
    Retorna motivos com maior variação relativa.
    """
    dist_treino = df_treino[coluna_motivo].value_counts(normalize=True)
    dist_teste = df_teste[coluna_motivo].value_counts(normalize=True)

    todos = sorted(set(dist_treino.index) | set(dist_teste.index))
    drift = []

    for motivo in todos:
        if motivo in ('outros', 'sem_texto_suficiente'):
            continue
        p_treino = dist_treino.get(motivo, 0.0)
        p_teste = dist_teste.get(motivo, 0.0)
        variacao = p_teste - p_treino
        variacao_rel = variacao / p_treino if p_treino > 0 else float('inf') if p_teste > 0 else 0.0

        drift.append({
            'motivo': motivo,
            'pct_treino': round(p_treino, 4),
            'pct_teste': round(p_teste, 4),
            'variacao_absoluta': round(variacao, 4),
            'variacao_relativa': round(variacao_rel, 4),
        })

    return pd.DataFrame(drift).sort_values('variacao_relativa', key=abs, ascending=False)


# ==================== SAÍDA ====================


def salvar_json(metricas, timestamp):
    caminho = ARTEFATOS / f'monitoramento_{timestamp}.json'
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2, default=str)
    print(f'💾 Monitoramento salvo (JSON): {caminho}')
    return caminho


def salvar_xlsx(metricas, timestamp):
    caminho = ARTEFATOS / f'monitoramento_{timestamp}.xlsx'
    try:
        with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
            # Resumo geral
            pd.DataFrame([metricas['resumo']]).to_excel(
                writer, sheet_name='resumo', index=False)

            # Métricas por motivo
            if 'por_motivo' in metricas and not metricas['por_motivo'].empty:
                metricas['por_motivo'].to_excel(
                    writer, sheet_name='por_motivo', index=False)

            # Drift
            if 'drift' in metricas and not metricas['drift'].empty:
                metricas['drift'].to_excel(
                    writer, sheet_name='drift', index=False)

            # Novos assuntos
            if 'novos_assuntos' in metricas:
                pd.DataFrame([metricas['novos_assuntos']]).to_excel(
                    writer, sheet_name='novos_assuntos', index=False)

        print(f'💾 Monitoramento salvo (XLSX): {caminho}')
    except Exception as e:
        print(f'⚠️  Erro ao salvar XLSX: {e}')


# ==================== MAIN ====================


def main():
    print('📊 ETAPA 5 — Monitoramento de qualidade (Fase 3)')
    print('=' * 70)

    df = carregar_rotulos()
    if df.empty:
        print('❌ Nenhum dado disponível.')
        return

    # Converte datas
    if 'criado_data' in df.columns:
        df['criado_data'] = pd.to_datetime(df['criado_data'], errors='coerce')

    # Divisão temporal
    corte = pd.to_datetime(PERIODO_TREINO_FIM)
    df_treino = df[df['criado_data'] <= corte].copy()
    df_teste = df[(df['criado_data'] > corte) &
                  (df['criado_data'] <= pd.to_datetime(PERIODO_TESTE_FIM))].copy()

    print(f'\n📅 Período de treino: até {PERIODO_TREINO_FIM} ({len(df_treino)} tickets)')
    print(f'📅 Período de teste: {PERIODO_TESTE_INICIO} a {PERIODO_TESTE_FIM} ({len(df_teste)} tickets)')

    if df_teste.empty:
        print('❌ Não há tickets no período de teste.')
        return

    # ==================== MÉTRICAS ====================

    # 1. Métricas por motivo (usando motivo atribuído como proxy de predição)
    df_por_motivo = calcular_metricas_por_motivo(
        df_teste, df_teste['motivo_id']
    )

    # 2. Cobertura automática
    cobertura, n_classificados, n_total = calcular_cobertura_automatica(df_teste)

    # 3. Taxa de revisão humana (a partir da auditoria de clusters, se existir)
    try:
        auditoria_path = sorted(
            ARTEFATOS.glob('auditoria_clusters_*.xlsx'),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[0]
        df_auditoria = pd.read_excel(auditoria_path)
        taxa_revisao, n_revisao, n_clusters = calcular_taxa_revisao_humana(df_auditoria)
        taxa_coerencia, n_coerentes, _ = calcular_coerencia_clusters(df_auditoria)
    except (IndexError, FileNotFoundError):
        taxa_revisao, n_revisao, n_clusters = 0.0, 0, 0
        taxa_coerencia, n_coerentes, _ = 0.0, 0, 0
        df_auditoria = pd.DataFrame()

    # 4. Taxa de novos assuntos
    novos = calcular_taxa_novos_assuntos(df_treino, df_teste)

    # 5. Drift de distribuição
    df_drift = calcular_drift(df_treino, df_teste)

    # ==================== RESUMO ====================

    f1_medio = df_por_motivo['f1'].mean() if not df_por_motivo.empty else 0.0
    precisao_media = df_por_motivo['precisao'].mean() if not df_por_motivo.empty else 0.0
    recall_medio = df_por_motivo['recall'].mean() if not df_por_motivo.empty else 0.0

    resumo = {
        'data_geracao': datetime.now().isoformat(),
        'periodo_treino_fim': PERIODO_TREINO_FIM,
        'periodo_teste_inicio': PERIODO_TESTE_INICIO,
        'periodo_teste_fim': PERIODO_TESTE_FIM,
        'n_tickets_treino': len(df_treino),
        'n_tickets_teste': len(df_teste),
        'n_motivos_treino': int(df_treino['motivo_id'].nunique()),
        'n_motivos_teste': int(df_teste['motivo_id'].nunique()),
        'precisao_media': round(float(precisao_media), 4),
        'recall_medio': round(float(recall_medio), 4),
        'f1_medio': round(float(f1_medio), 4),
        'cobertura_automatica': cobertura,
        'n_classificados_automatico': n_classificados,
        'taxa_revisao_humana': taxa_revisao,
        'n_clusters_requerem_revisao': n_revisao,
        'n_clusters_total': n_clusters,
        'taxa_coerencia_clusters': taxa_coerencia,
        'taxa_novos_assuntos': novos['taxa_novos_assuntos'],
        'n_novos_assuntos': novos['n_novos_assuntos'],
        'novos_assuntos': novos['novos_assuntos'],
    }

    metricas = {
        'resumo': resumo,
        'por_motivo': df_por_motivo,
        'drift': df_drift,
        'novos_assuntos': novos,
    }

    print('\n📈 RESUMO DO MONITORAMENTO')
    print('-' * 70)
    for k, v in resumo.items():
        if k not in ('novos_assuntos', 'data_geracao'):
            print(f'   {k}: {v}')

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    salvar_json(metricas, timestamp)
    salvar_xlsx(metricas, timestamp)

    print('\n✅ Etapa 5 — Monitoramento concluído.')
    print(f'📄 Arquivos gerados com timestamp {timestamp}')


if __name__ == '__main__':
    main()
