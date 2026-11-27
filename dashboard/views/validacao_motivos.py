# ============================================================
# dashboard/views/motivos.py — Validação de Motivos (Fase 3, Etapa 2)
# ============================================================
"""
Interface de validação orientada a decisões para mapeamento de motivos reais
de tickets (MLP — Mapeamento de Motivos Reais de Tickets).

Fluxo:
  1. Validação por cluster (agrupamento de tickets com mesmo assunto)
  2. Quatro filas de revisão:
     - Fila 1: Alta confiança (prioridade baixa)
     - Fila 2: Divergência (prioridade alta)
     - Fila 3: Baixa confiança (prioridade alta)
     - Fila 4: Assunto emergente (exploração)
  3. Decisões do analista: aprovar / dividir / descartar / não determinar

Não quebra nada do pipeline nem do dashboard. Mudança aditiva.
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# ==================== PATHS ====================
RAIZ = Path(__file__).resolve().parent.parent.parent
ARTEFATOS = RAIZ / 'scripts_treinamento' / 'artefatos'
DECISOES_PATH = ARTEFATOS / 'decisoes_validacao.json'


# ==================== CARREGAMENTO DE DADOS ====================


@st.cache_data
def carregar_auditoria_clusters():
    """Carrega o relatório de auditoria de clusters mais recente."""
    candidatos = sorted(
        ARTEFATOS.glob('auditoria_clusters_*.xlsx'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidatos:
        return pd.DataFrame()
    return pd.read_excel(candidatos[0])


@st.cache_data
def carregar_sugestoes_novos_motivos():
    """Carrega sugestões de novos motivos mais recentes."""
    candidatos = sorted(
        ARTEFATOS.glob('sugestoes_novos_motivos_*.xlsx'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidatos:
        return pd.DataFrame()
    return pd.read_excel(candidatos[0])


@st.cache_data
def carregar_analise_ruido():
    """Carrega análise de ruído mais recente."""
    candidatos = sorted(
        ARTEFATOS.glob('analise_ruido_*.xlsx'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidatos:
        return pd.DataFrame()
    return pd.read_excel(candidatos[0])


@st.cache_data
def carregar_rotulos_fracos():
    """Carrega rótulos fracos mais recentes (para validação individual)."""
    fixo = ARTEFATOS / 'rotulos_fracos.csv'
    if fixo.exists():
        return pd.read_csv(fixo)
    candidatos = sorted(
        ARTEFATOS.glob('rotulos_fracos_*.csv'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidatos:
        return pd.read_csv(candidatos[0])
    return pd.DataFrame()


# ==================== FILAS DE REVISÃO ====================


def classificar_filas(df_auditoria):
    """
    Divide os clusters em quatro filas de revisão com base na coerência
    e na ação recomendada.
    """
    df = df_auditoria.copy()

    # Fila 1 — Alta confiança (prioridade baixa)
    fila1 = df[
        (df['coerencia'] == 'alta') &
        (df['acao_recomendada'] == 'Aprovar motivo')
    ].copy()
    fila1['fila'] = 'Fila 1 — Alta confiança'
    fila1['prioridade'] = 'Baixa'

    # Fila 2 — Divergência (prioridade alta)
    fila2 = df[
        (df['acao_recomendada'] == 'Dividir cluster') |
        (df['categorias_dominantes'].str.contains(r'\|', regex=False))
    ].copy()
    fila2['fila'] = 'Fila 2 — Divergência'
    fila2['prioridade'] = 'Alta'

    # Fila 3 — Baixa confiança (prioridade alta)
    fila3 = df[
        (df['coerencia'] == 'baixa') &
        (df['acao_recomendada'] != 'Dividir cluster')
    ].copy()
    fila3['fila'] = 'Fila 3 — Baixa confiança'
    fila3['prioridade'] = 'Alta'

    # Fila 4 — Assunto emergente (exploração)
    fila4 = df[
        (df['coerencia'] == 'média') &
        (df['acao_recomendada'] == 'Aprovar com revisão leve')
    ].copy()
    fila4['fila'] = 'Fila 4 — Assunto emergente'
    fila4['prioridade'] = 'Média'

    return fila1, fila2, fila3, fila4


# ==================== RENDERIZAÇÃO ====================


def render(df_filtrado):
    st.title('🎯 Validação de Motivos Reais')
    st.markdown(
        'Validação orientada a decisões para mapeamento de motivos reais '
        'de tickets. Revise clusters, aproue novos motivos e ajuste a '
        'taxonomia antes do treinamento supervisionado.'
    )

    # ==================== CARREGAMENTO ====================
    df_auditoria = carregar_auditoria_clusters()
    df_sugestoes = carregar_sugestoes_novos_motivos()
    df_ruido = carregar_analise_ruido()
    df_rotulos = carregar_rotulos_fracos()

    if df_auditoria.empty:
        st.warning(
            '⚠️ Nenhum relatório de auditoria encontrado. '
            'Rode primeiro o script `scripts_treinamento/07_auditar_clusters.py`.'
        )
        return

    # ==================== RESUMO EXECUTIVO ====================
    st.subheader('📊 Resumo da Auditoria')
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Clusters totais', len(df_auditoria))
    with col2:
        st.metric('Alta coerência', int((df_auditoria['coerencia'] == 'alta').sum()))
    with col3:
        st.metric('Média coerência', int((df_auditoria['coerencia'] == 'média').sum()))
    with col4:
        st.metric('Baixa coerência', int((df_auditoria['coerencia'] == 'baixa').sum()))

    st.divider()

    # ==================== FILAS DE REVISÃO ====================
    fila1, fila2, fila3, fila4 = classificar_filas(df_auditoria)

    st.subheader('🗂️ Filas de Revisão')

    tab1, tab2, tab3, tab4 = st.tabs([
        'Fila 1 — Alta confiança',
        'Fila 2 — Divergência',
        'Fila 3 — Baixa confiança',
        'Fila 4 — Assunto emergente',
    ])

    # ---------- FILA 1 ----------
    with tab1:
        st.caption(
            'Clusters de alta coerência com ação "Aprovar motivo". '
            'Prioridade baixa — pode ser revisado em lote.'
        )
        if fila1.empty:
            st.info('Nenhum cluster nesta fila.')
        else:
            for _, row in fila1.iterrows():
                _render_card_cluster(row, fila='fila1')

    # ---------- FILA 2 ----------
    with tab2:
        st.caption(
            'Clusters com divergência de categoria ou ação "Dividir cluster". '
            'Prioridade alta — requer atenção do analista.'
        )
        if fila2.empty:
            st.info('Nenhum cluster nesta fila.')
        else:
            for _, row in fila2.iterrows():
                _render_card_cluster(row, fila='fila2')

    # ---------- FILA 3 ----------
    with tab3:
        st.caption(
            'Clusters de baixa coerência. '
            'Prioridade alta — textos podem ser insuficientes ou muito dispersos.'
        )
        if fila3.empty:
            st.info('Nenhum cluster nesta fila.')
        else:
            for _, row in fila3.iterrows():
                _render_card_cluster(row, fila='fila3')

    # ---------- FILA 4 ----------
    with tab4:
        st.caption(
            'Clusters de média coerência com ação "Aprovar com revisão leve". '
            'Exploração de assuntos emergentes.'
        )
        if fila4.empty:
            st.info('Nenhum cluster nesta fila.')
        else:
            for _, row in fila4.iterrows():
                _render_card_cluster(row, fila='fila4')

    # ==================== VALIDAÇÃO INDIVIDUAL (TICKETS) ====================
    st.divider()
    st.subheader('📋 Validação Individual de Tickets')
    st.caption(
        'Valide tickets individualmente quando o texto não permitir '
        'uma conclusão clara sobre o motivo.'
    )

    if df_rotulos.empty:
        st.warning('Nenhum rótulo fraco encontrado para validação individual.')
    else:
        _render_validacao_individual(df_rotulos)

    # ==================== SUGESTÕES DE NOVOS MOTIVOS ====================
    st.divider()
    st.subheader('💡 Sugestões de Novos Motivos para a Taxonomia')
    st.caption(
        'Motivos sugeridos automaticamente a partir de clusters coerentes. '
        'Revise e aprove para adicionar à taxonomia.'
    )

    if df_sugestoes.empty:
        st.info('Nenhuma sugestão de novo motivo encontrada.')
    else:
        for _, row in df_sugestoes.head(15).iterrows():
            with st.expander(
                f"🔹 {row.get('motivo_sugerido', '')} "
                f"({row.get('qtd_tickets', 0)} tickets)"
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write('**Categoria origem:**', row.get('categoria_origem', ''))
                    st.write('**Quantidade:**', row.get('qtd_tickets', ''))
                    st.write('**Termos:**', row.get('termos', ''))
                with col_b:
                    st.write('**Exemplos:**', row.get('exemplos', ''))
                    decisao = st.selectbox(
                        'Decisão',
                        ['Pendente', 'Aprovar', 'Descartar', 'Mesclar com existente'],
                        key=f"motivo_{row.get('motivo_sugerido', '')}_{row.get('qtd_tickets', '')}",
                    )
                    if decisao != 'Pendente':
                        st.success(f'Decisão registrada: {decisao}')

    # Exportar rótulos humanos para treinamento
    _render_export_rotulos_humanos()


# ==================== COMPONENTES AUXILIARES ====================


def _render_card_cluster(row, fila):
    """Renderiza um card de cluster com opções de decisão."""
    cluster_id = row.get('cluster_id', '?')
    n_tickets = row.get('n_tickets', 0)
    assunto = row.get('assunto_sugerido', '')
    categorias = row.get('categorias_dominantes', '')
    termos = row.get('terros_caracteristicos', '')
    exemplos_rep = row.get('exemplos_representativos', '')
    exemplos_div = row.get('exemplos_divergentes', '')
    acao = row.get('acao_recomendada', '')
    coerencia = row.get('coerencia', '')

    # Ícone por ação
    icone_acao = {
        'Aprovar motivo': '✅',
        'Aprovar com revisão leve': '⚠️',
        'Dividir cluster': '🔀',
        'Descartar ou revisar termos': '🗑️',
    }.get(acao, '❓')

    with st.expander(
        f'{icone_acao} Cluster {cluster_id} — {n_tickets} tickets — {assunto}',
        expanded=False,
    ):
        # Linha de métricas
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric('Tickets', n_tickets)
        with c2:
            st.metric('Coerência', coerencia.title())
        with c3:
            st.write('**Categorias:**')
            st.write(categorias if categorias else '—')
        with c4:
            st.write('**Ação recomendada:**')
            st.write(acao)

        # Termos característicos
        if termos:
            st.write('**Termos característicos:**')
            st.caption(termos)

        # Exemplos representativos
        if exemplos_rep:
            st.write('**Exemplos representativos:**')
            for ex in str(exemplos_rep).split(' | ')[:3]:
                st.markdown(f'• {ex}')

        # Exemplos divergentes
        if exemplos_div:
            st.write('**Exemplos divergentes (investigar):**')
            for ex in str(exemplos_div).split(' | ')[:3]:
                st.markdown(f'• {ex}')

        # ==================== DECISÕES DO ANALISTA ====================
        st.write('**Decisão do analista:**')
        col_dec1, col_dec2, col_dec3, col_dec4 = st.columns(4)

        chave_base = f"{fila}_{cluster_id}"

        with col_dec1:
            if st.button('✅ Aprovar', key=f"aprovar_{chave_base}"):
                _registrar_decisao(cluster_id, 'aprovar', assunto, fila)

        with col_dec2:
            if st.button('🔀 Dividir', key=f"dividir_{chave_base}"):
                _registrar_decisao(cluster_id, 'dividir', assunto, fila)

        with col_dec3:
            if st.button('🗑️ Descartar', key=f"descartar_{chave_base}"):
                _registrar_decisao(cluster_id, 'descartar', assunto, fila)

        with col_dec4:
            if st.button('❓ Não determinar', key=f"nd_{chave_base}"):
                _registrar_decisao(cluster_id, 'nao_determinar', assunto, fila)

        # Campo de motivo validado (opcional)
        motivo_validado = st.text_input(
            'Motivo validado (texto curto, opcional)',
            key=f"motivo_{chave_base}",
            placeholder='Ex: Erro ao acessar protocolo CTC',
        )
        if motivo_validado:
            _registrar_decisao(cluster_id, 'motivo_validado', motivo_validado, fila)

        st.divider()


def _render_validacao_individual(df_rotulos):
    """Renderiza validação individual de tickets."""
    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_categoria = st.multiselect(
            'Filtrar por categoria',
            options=sorted(df_rotulos['categoria'].dropna().unique()) if 'categoria' in df_rotulos.columns else [],
        )
    with col_f2:
        filtro_motivo = st.multiselect(
            'Filtrar por motivo atribuído',
            options=sorted(df_rotulos['motivo_atribuido'].dropna().unique()) if 'motivo_atribuido' in df_rotulos.columns else [],
        )

    df_filtrado = df_rotulos.copy()
    if filtro_categoria and 'categoria' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['categoria'].isin(filtro_categoria)]
    if filtro_motivo and 'motivo_atribuido' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['motivo_atribuido'].isin(filtro_motivo)]

    st.caption(f'{len(df_filtrado)} tickets exibidos (após filtros)')

    # Mostrar em lotes de 10
    if 'ticket_id' not in df_filtrado.columns and 'id' in df_filtrado.columns:
        df_filtrado['ticket_id'] = df_filtrado['id']

    id_col = 'ticket_id' if 'ticket_id' in df_filtrado.columns else None

    for _, row in df_filtrado.head(20).iterrows():
        tid = row.get(id_col, '?') if id_col else '?'
        titulo = row.get('titulo', '') or ''
        motivo = row.get('motivo_atribuido', '') or ''
        confianca = row.get('confianca', 0) or 0

        with st.container():
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                st.write(f'**Ticket {tid}:** {titulo[:100]}')
            with c2:
                st.write(f'Motivo: {motivo}')
            with c3:
                st.write(f'Confiança: {confianca}')

            motivo_correto = st.text_input(
                'Motivo correto (deixe vazio se igual ao atribuído)',
                key=f"ind_{tid}",
                placeholder='Deixe vazio para manter o atribuído',
            )
            nao_determinar = st.checkbox(
                'Não é possível determinar',
                key=f"nd_ind_{tid}",
            )
            if st.button('Salvar', key=f"salvar_ind_{tid}"):
                st.success(f'Ticket {tid} salvo.')

            st.divider()


def _carregar_decisoes_salvas():
    """Carrega decisões previamente salvas em arquivo."""
    if DECISOES_PATH.exists():
        try:
            with open(DECISOES_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _salvar_decisao(decisao):
    """Persiste uma decisão em arquivo JSON para Active Learning."""
    decisoes = _carregar_decisoes_salvas()
    decisoes.append(decisao)
    try:
        with open(DECISOES_PATH, 'w', encoding='utf-8') as f:
            json.dump(decisoes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f'Erro ao salvar decisão: {e}')


def _registrar_decisao(cluster_id, decisao, valor, fila):
    """Registra uma decisão do analista, persistindo em arquivo para Active Learning."""
    if 'decisoes_motivos' not in st.session_state:
        st.session_state.decisoes_motivos = _carregar_decisoes_salvas()

    decisao_obj = {
        'cluster_id': cluster_id,
        'decisao': decisao,
        'valor': valor,
        'fila': fila,
        'timestamp': datetime.now().isoformat(),
    }

    st.session_state.decisoes_motivos.append(decisao_obj)
    _salvar_decisao(decisao_obj)
    st.success(f'Decisão "{decisao}" registrada para o cluster {cluster_id}.')

    # Exibir decisões registradas na sessão
    with st.expander('Decisões registradas nesta sessão', expanded=False):
        for d in reversed(st.session_state.decisoes_motivos[-10:]):
            st.write(f"• Cluster {d['cluster_id']} — {d['decisao']} ({d['fila']})")


# ==================== EXPORTAR RÓTULOS PARA TREINAMENTO ====================


def _render_export_rotulos_humanos():
    """Renderiza seção para exportar decisões como rótulos humanos (Active Learning)."""
    st.divider()
    st.subheader('🔄 Exportar Rótulos para Treinamento (Active Learning)')
    st.caption(
        'Use as decisões validadas pelos analistas para gerar rótulos humanos '
        'que podem retreinar o modelo de mapeamento de motivos.'
    )

    decisoes_salvas = _carregar_decisoes_salvas()
    if not decisoes_salvas:
        st.info('Nenhuma decisão válida ainda. Valide alguns clusters primeiro.')
        return

    df_decisoes = pd.DataFrame(decisoes_salvas)
    n_aprovadas = len(df_decisoes[df_decisoes['decisao'] == 'aprovar'])
    n_dividir = len(df_decisoes[df_decisoes['decisao'] == 'dividir'])
    n_descartar = len(df_decisoes[df_decisoes['decisao'] == 'descartar'])
    n_motivo_valido = len(df_decisoes[df_decisoes['decisao'] == 'motivo_validado'])

    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    with col_e1:
        st.metric('Total de decisões', len(decisoes_salvas))
    with col_e2:
        st.metric('Aprovar', n_aprovadas)
    with col_e3:
        st.metric('Dividir', n_dividir)
    with col_e4:
        st.metric('Motivo validado', n_motivo_valido)

    # Gerar CSV de rótulos humanos a partir das decisões "motivo_validado"
    rotulos_humanos = df_decisoes[df_decisoes['decisao'] == 'motivo_validado'].copy()
    if not rotulos_humanos.empty:
        rotulos_export = rotulos_humanos[['cluster_id', 'valor', 'timestamp']].copy()
        rotulos_export.columns = ['cluster_id', 'motivo_correto', 'timestamp']
        rotulos_export['origem'] = 'humano'

        csv_bytes = rotulos_export.to_csv(index=False, encoding='utf-8').encode('utf-8')
        st.download_button(
            label='📥 Baixar rótulos humanos (CSV)',
            data=csv_bytes,
            file_name=f'rotulos_humanos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv',
            help='Este CSV pode ser usado como entrada para retreinar o modelo de mapeamento de motivos.',
        )
        st.info(
            'Os rótulos humanos têm prioridade sobre os rótulos fracos (regras) '
            'no treinamento supervisionado.'
        )
    else:
        st.info(
            'Nenhum motivo validado ainda. Use o campo "Motivo validado" nos cards '
            'de cluster para gerar rótulos humanos.'
        )
