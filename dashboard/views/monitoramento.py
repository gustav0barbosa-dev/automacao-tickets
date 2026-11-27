# ============================================================
# dashboard/views/monitoramento.py — Monitoramento de qualidade (Fase 3, Etapa 5)
# ============================================================
"""
View de monitoramento do sistema de mapeamento de motivos reais de tickets.

Exibe métricas de qualidade calculadas pelo script
scripts_treinamento/10_monitoramento.py:
  - Precisão / Recall / F1 por motivo
  - Cobertura automática (% tickets classificados sem intervenção humana)
  - Taxa de revisão humana
  - Coerência dos clusters
  - Taxa de novos assuntos
  - Drift de distribuição entre períodos

Não quebra nada do pipeline nem do dashboard. Mudança aditiva.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# ==================== PATHS ====================
RAIZ = Path(__file__).resolve().parent.parent.parent
ARTEFATOS = RAIZ / 'scripts_treinamento' / 'artefatos'


# ==================== CARREGAMENTO ====================


@st.cache_data
def carregar_monitoramento():
    """Carrega o relatório de monitoramento mais recente."""
    candidatos = sorted(
        ARTEFATOS.glob('monitoramento_*.xlsx'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidatos:
        return None, None
    caminho = candidatos[0]
    try:
        xlsx = pd.ExcelFile(caminho)
        resumo = pd.read_excel(xlsx, sheet_name='resumo')
        por_motivo = pd.read_excel(xlsx, sheet_name='por_motivo')
        drift = pd.read_excel(xlsx, sheet_name='drift')
        novos = pd.read_excel(xlsx, sheet_name='novos_assuntos')
        return {
            'arquivo': caminho.name,
            'resumo': resumo,
            'por_motivo': por_motivo,
            'drift': drift,
            'novos_assuntos': novos,
        }, caminho
    except Exception as e:
        st.error(f'Erro ao ler relatório de monitoramento: {e}')
        return None, None


# ==================== RENDERIZAÇÃO ====================


def render(df_filtrado=None):
    st.title('📊 Monitoramento de Qualidade')
    st.markdown(
        'Acompanhamento de métricas do sistema de mapeamento de motivos reais '
        '(Fase 3, Etapa 5). Os dados são gerados pelo script '
        '`scripts_treinamento/10_monitoramento.py`.'
    )

    dados, caminho = carregar_monitoramento()

    if dados is None:
        st.warning(
            '⚠️ Nenhum relatório de monitoramento encontrado. '
            'Rode primeiro o script `scripts_treinamento/10_monitoramento.py`.'
        )
        return

    st.caption(f'📄 Fonte: `{dados["arquivo"]}`')

    # ==================== RESUMO GERAL ====================
    st.subheader('📈 Resumo Executivo')

    resumo = dados['resumo']
    linha = resumo.iloc[0] if len(resumo) > 0 else {}

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Tickets no teste', linha.get('n_tickets_teste', 0))
        st.metric('Motivos no teste', linha.get('n_motivos_teste', 0))
    with col2:
        st.metric('F1 médio', f"{linha.get('f1_medio', 0):.3f}")
        st.metric('Precisão média', f"{linha.get('precisao_media', 0):.3f}")
    with col3:
        st.metric('Recall médio', f"{linha.get('recall_medio', 0):.3f}")
        st.metric('Cobertura automática', f"{linha.get('cobertura_automatica', 0):.1%}")
    with col4:
        st.metric('Taxa de revisão humana', f"{linha.get('taxa_revisao_humana', 0):.1%}")
        st.metric('Coerência dos clusters', f"{linha.get('taxa_coerencia_clusters', 0):.1%}")

    st.divider()

    # ==================== MÉTRICAS POR MOTIVO ====================
    st.subheader('🎯 Precisão / Recall / F1 por Motivo')

    por_motivo = dados['por_motivo']
    if por_motivo.empty:
        st.info('Sem dados de métricas por motivo disponíveis.')
    else:
        # Top 15 por F1
        top = por_motivo.sort_values('f1', ascending=False).head(15)

        col_a, col_b = st.columns(2)

        with col_a:
            st.write('**Top 15 motivos por F1-score**')
            st.dataframe(
                top[['motivo', 'precisao', 'recall', 'f1', 'suporte']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'precisao': st.column_config.NumberColumn('Precisão', format='%.3f'),
                    'recall': st.column_config.NumberColumn('Recall', format='%.3f'),
                    'f1': st.column_config.NumberColumn('F1', format='%.3f'),
                    'suporte': st.column_config.NumberColumn('Suporte'),
                },
            )

        with col_b:
            st.write('**Motivos com menor F1-score (precisam de atenção)**')
            bottom = por_motivo.sort_values('f1', ascending=True).head(10)
            st.dataframe(
                bottom[['motivo', 'precisao', 'recall', 'f1', 'suporte']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'precisao': st.column_config.NumberColumn('Precisão', format='%.3f'),
                    'recall': st.column_config.NumberColumn('Recall', format='%.3f'),
                    'f1': st.column_config.NumberColumn('F1', format='%.3f'),
                    'suporte': st.column_config.NumberColumn('Suporte'),
                },
            )

    st.divider()

    # ==================== DRIFT DE DISTRIBUIÇÃO ====================
    st.subheader('🔄 Drift de Distribuição (Treino vs. Teste)')
    st.caption(
        'Motivos com maior variação relativa entre o período de treino e o de teste. '
        'Valores positivos = aumento no teste; negativos = redução.'
    )

    drift = dados['drift']
    if drift.empty:
        st.info('Sem dados de drift disponíveis.')
    else:
        top_drift = drift.head(10)
        st.dataframe(
            top_drift,
            use_container_width=True,
            hide_index=True,
            column_config={
                'pct_treino': st.column_config.NumberColumn('% Treino', format='%.3f'),
                'pct_teste': st.column_config.NumberColumn('% Teste', format='%.3f'),
                'variacao_absoluta': st.column_config.NumberColumn('Var. Absoluta', format='%.3f'),
                'variacao_relativa': st.column_config.NumberColumn('Var. Relativa', format='%.3f'),
            },
        )

    st.divider()

    # ==================== NOVOS ASSUNTOS ====================
    st.subheader('🆕 Novos Assuntos Descobertos')
    st.caption(
        'Motivos que aparecem no período de teste mas não foram vistos no treino. '
        'Indicam necessidade de revisão da taxonomia.'
    )

    novos = dados['novos_assuntos']
    if novos.empty:
        st.info('Sem dados de novos assuntos disponíveis.')
    else:
        linha_novos = novos.iloc[0] if len(novos) > 0 else {}

        col_x, col_y, col_z = st.columns(3)
        with col_x:
            st.metric('Taxa de novos assuntos', f"{linha_novos.get('taxa_novos_assuntos', 0):.1%}")
        with col_y:
            st.metric('Qtd. novos assuntos', linha_novos.get('n_novos_assuntos', 0))
        with col_z:
            st.metric('Total motivos no teste', linha_novos.get('total_motivos_teste', 0))

        lista_novos = linha_novos.get('novos_assuntos', [])
        if isinstance(lista_novos, str) and lista_novos:
            try:
                import ast
                lista_novos = ast.literal_eval(lista_novos)
            except Exception:
                lista_novos = [lista_novos]

        if lista_novos:
            st.write('**Motivos novos:**')
            for item in lista_novos:
                st.markdown(f'• {item}')
        else:
            st.info('Nenhum novo assunto detectado.')

    st.divider()

    # ==================== INDICADORES DE QUALIDADE ====================
    st.subheader('⚖️ Indicadores de Qualidade')

    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    with col_q1:
        st.metric(
            'Cobertura automática',
            f"{linha.get('cobertura_automatica', 0):.1%}",
            help='% de tickets classificados automaticamente sem intervenção humana',
        )
    with col_q2:
        st.metric(
            'Taxa de revisão humana',
            f"{linha.get('taxa_revisao_humana', 0):.1%}",
            help='% de clusters que requerem intervenção do analista',
        )
    with col_q3:
        st.metric(
            'Coerência dos clusters',
            f"{linha.get('taxa_coerencia_clusters', 0):.1%}",
            help='% de clusters coerentes (alta/média coerência sem divisão)',
        )
    with col_q4:
        st.metric(
            'Novos assuntos',
            f"{linha_novos.get('taxa_novos_assuntos', 0):.1%}",
            help='% de motivos no teste não vistos no treino',
        )

    st.divider()

    # ==================== AÇÕES RECOMENDADAS ====================
    st.subheader('🚨 Ações Recomendadas')

    acoes = []

    f1_medio = linha.get('f1_medio', 0)
    if f1_medio < 0.6:
        acoes.append(
            '⚠️ F1 médio abaixo de 0,60. Considere revisar rótulos ou '
            'treinar com mais dados.'
        )
    else:
        acoes.append('✅ F1 médio acima de 0,60. Modelo em nível aceitável.')

    cobertura = linha.get('cobertura_automatica', 0)
    if cobertura < 0.6:
        acoes.append(
            '⚠️ Cobertura automática abaixo de 60%. Muitos tickets estão '
            'sem classificação automática.'
        )
    else:
        acoes.append('✅ Cobertura automática acima de 60%.')

    taxa_revisao = linha.get('taxa_revisao_humana', 0)
    if taxa_revisao > 0.5:
        acoes.append(
            '⚠️ Mais de 50% dos clusters requerem revisão humana. '
            'Considere aprimorar as regras de classificação.'
        )
    else:
        acoes.append('✅ Taxa de revisão humana controlada.')

    novos_assuntos = linha_novos.get('taxa_novos_assuntos', 0)
    if novos_assuntos > 0.2:
        acoes.append(
            '⚠️ Mais de 20% de novos assuntos no teste. '
            'A taxonomia pode estar desatualizada.'
        )
    else:
        acoes.append('✅ Taxa de novos assuntos controlada.')

    for acao in acoes:
        st.markdown(acao)

    st.divider()
    st.caption(
        'Para atualizar estas métricas, rode: '
        '`python scripts_treinamento/10_monitoramento.py`'
    )
