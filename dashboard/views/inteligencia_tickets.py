# ============================================================
# dashboard/views/inteligencia_tickets.py — Inteligência de Tickets
# ============================================================
"""
Nova área de inteligência operacional de ITSM (Fase 4 — recomendação do relatório).

Cinco funcionalidades:
  1. Análise de recorrência (Entrega 1)
  2. Qualidade da abertura dos tickets (Entrega 2)
  3. Análise de problemas operacionais (Entrega 3)
  4. Recomendações inteligentes (Entrega 4)
  5. Investigação detalhada (Entrega 4)

Os dados vêm dos artefatos gerados por scripts_treinamento/11_inteligencia_tickets.py.
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
def carregar_arquivo(nome_pattern):
    """Carrega o arquivo mais recente que bate com o padrão."""
    candidatos = sorted(
        ARTEFATOS.glob(nome_pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidatos:
        return None
    try:
        df = pd.read_csv(candidatos[0], encoding='utf-8')
        if df.empty:
            return None
        return df
    except (pd.errors.EmptyDataError, Exception):
        return None


def carregar_todos():
    """Carrega todos os artefatos da Inteligência de Tickets."""
    dados = {}
    dados['ranking_assuntos'] = carregar_arquivo('inteligencia_tickets_recorrencia_ranking_*.csv')
    dados['evolucao_mensal'] = carregar_arquivo('inteligencia_tickets_recorrencia_evolucao_*.csv')
    dados['dist_sistema'] = carregar_arquivo('inteligencia_tickets_recorrencia_sistema_*.csv')
    dados['dist_area'] = carregar_arquivo('inteligencia_tickets_recorrencia_area_*.csv')
    dados['dist_categoria'] = carregar_arquivo('inteligencia_tickets_recorrencia_categoria_*.csv')
    dados['descricao_insuficiente'] = carregar_arquivo(
        'inteligencia_tickets_qualidade_descricao_*.csv'
    )
    dados['assunto_generico'] = carregar_arquivo(
        'inteligencia_tickets_qualidade_generico_*.csv'
    )
    dados['divergencia'] = carregar_arquivo(
        'inteligencia_tickets_qualidade_divergencia_*.csv'
    )
    dados['reaberturas'] = carregar_arquivo(
        'inteligencia_tickets_qualidade_reaberturas_*.csv'
    )
    dados['tickets_parados'] = carregar_arquivo(
        'inteligencia_tickets_operacional_parados_*.csv'
    )
    dados['sla_estourado'] = carregar_arquivo(
        'inteligencia_tickets_operacional_sla_*.csv'
    )
    dados['tempo_por_motivo'] = carregar_arquivo(
        'inteligencia_tickets_operacional_tempo_motivo_*.csv'
    )
    dados['recomendacoes'] = carregar_arquivo(
        'inteligencia_tickets_recomendacoes_*.csv'
    )
    return dados


# ==================== RENDERIZAÇÃO ====================


def render(df_filtrado=None):
    st.title('🎫 Inteligência de Tickets')
    st.markdown(
        'Área de inteligência operacional de ITSM. '
        'Identifica problemas operacionais, falhas no registro de chamados e '
        'oportunidades de melhoria com base nos dados dos tickets.'
    )

    dados = carregar_todos()

    if not dados or all(v is None or v.empty for v in dados.values()):
        st.warning(
            '⚠️ Nenhum dado de inteligência encontrado. '
            'Rode primeiro o script `scripts_treinamento/11_inteligencia_tickets.py`.'
        )
        return

    # Exibe data de geração dos dados (primeiro arquivo disponível)
    st.caption(
        'Dados gerados a partir dos artefatos em `scripts_treinamento/artefatos/`. '
        'Atualize rodando o script de inteligência de tickets.'
    )

    # ==================== ABAS ====================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        '1️⃣ Recorrência',
        '2️⃣ Qualidade Abertura',
        '3️⃣ Problemas Operacionais',
        '4️⃣ Recomendações',
        '5️⃣ Investigação',
    ])

    # ---------- ABA 1: RECORRÊNCIA ----------
    with tab1:
        _render_recorrencia(dados)

    # ---------- ABA 2: QUALIDADE ----------
    with tab2:
        _render_qualidade(dados)

    # ---------- ABA 3: OPERACIONAL ----------
    with tab3:
        _render_operacional(dados)

    # ---------- ABA 4: RECOMENDAÇÕES ----------
    with tab4:
        _render_recomendacoes(dados)

    # ---------- ABA 5: INVESTIGAÇÃO ----------
    with tab5:
        _render_investigacao(dados)


# ==================== COMPONENTES AUXILIARES ====================


def _render_recorrencia(dados):
    st.subheader('📊 Análise de Recorrência')
    st.caption(
        'Quais assuntos mais aparecem, qual o crescimento mensal e onde se concentram '
        'os chamados (por sistema e setor).'
    )

    ranking = dados['ranking_assuntos']
    evolucao = dados['evolucao_mensal']
    dist_sistema = dados['dist_sistema']
    dist_area = dados['dist_area']
    dist_categoria = dados['dist_categoria']

    if ranking is not None and not ranking.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.write('**Top 15 assuntos por volume**')
            st.dataframe(
                ranking.head(15),
                use_container_width=True,
                hide_index=True,
                column_config={
                    'qtd_tickets': st.column_config.NumberColumn('Tickets'),
                    'pct': st.column_config.NumberColumn('%', format='%.1f%%'),
                },
            )

        with col2:
            st.write('**Top 10 sistemas**')
            if dist_sistema is not None and not dist_sistema.empty:
                st.dataframe(
                    dist_sistema.head(10),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'qtd_tickets': st.column_config.NumberColumn('Tickets'),
                    },
                )
            else:
                st.info('Sem dados de sistema.')

    st.divider()

    # Evolução mensal
    st.write('**Evolução mensal (últimos 12 meses)**')
    if evolucao is not None and not evolucao.empty:
        st.line_chart(
            evolucao.set_index('mes_str')['qtd_tickets'],
            use_container_width=True,
        )
        st.dataframe(
            evolucao,
            use_container_width=True,
            hide_index=True,
            column_config={
                'qtd_tickets': st.column_config.NumberColumn('Tickets'),
                'crescimento_pct': st.column_config.NumberColumn('Crescimento %', format='%.1f%%'),
            },
        )
    else:
        st.info('Sem dados de evolução mensal.')

    st.divider()

    # Distribuição por área
    st.write('**Distribuição por área/setor**')
    if dist_area is not None and not dist_area.empty:
        st.bar_chart(
            dist_area.set_index('area')['qtd_tickets'],
            use_container_width=True,
        )
        st.dataframe(
            dist_area.head(10),
            use_container_width=True,
            hide_index=True,
            column_config={
                'qtd_tickets': st.column_config.NumberColumn('Tickets'),
            },
        )
    else:
        st.info('Sem dados de área.')

    st.divider()

    # Categoria declarada vs real
    st.write('**Top 15 categorias declaradas**')
    if dist_categoria is not None and not dist_categoria.empty:
        st.dataframe(
            dist_categoria.head(15),
            use_container_width=True,
            hide_index=True,
            column_config={
                'qtd_tickets': st.column_config.NumberColumn('Tickets'),
            },
        )
    else:
        st.info('Sem dados de categoria.')


def _render_qualidade(dados):
    st.subheader('🔍 Qualidade da Abertura dos Tickets')
    st.caption(
        'Identifica assuntos genéricos ou incorretos, descrições insuficientes e '
        'chamados classificados no motivo errado.'
    )

    descricao = dados['descricao_insuficiente']
    generico = dados['assunto_generico']
    divergencia = dados['divergencia']
    reaberturas = dados['reaberturas']

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Desc. insuficiente', len(descricao) if descricao is not None else 0)
    with col2:
        st.metric('Assunto genérico', len(generico) if generico is not None else 0)
    with col3:
        st.metric('Divergência cat. vs real', len(divergencia) if divergencia is not None else 0)
    with col4:
        st.metric('Reaberturas', len(reaberturas) if reaberturas is not None else 0)

    st.divider()

    # Descrição insuficiente
    st.write('**Tickets com descrição insuficiente (<20 caracteres)**')
    if descricao is not None and not descricao.empty:
        st.dataframe(
            descricao.head(20),
            use_container_width=True,
            hide_index=True,
            column_config={
                'descricao_tamanho': st.column_config.NumberColumn('Tam.'),
                'criado_data': st.column_config.DatetimeColumn('Criado em'),
            },
        )
    else:
        st.info('Nenhum ticket com descrição insuficiente encontrado.')

    st.divider()

    # Assunto genérico
    st.write('**Tickets com assunto genérico / título curto**')
    if generico is not None and not generico.empty:
        st.dataframe(
            generico.head(20),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info('Nenhum ticket com assunto genérico encontrado.')

    st.divider()

    # Divergência
    st.write('**Divergência entre categoria declarada e motivo real**')
    if divergencia is not None and not divergencia.empty:
        st.dataframe(
            divergencia.head(20),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info('Nenhuma divergência identificada.')

    st.divider()

    # Reaberturas
    st.write('**Reaberturas de tickets**')
    if reaberturas is not None and not reaberturas.empty:
        st.dataframe(
            reaberturas.head(20),
            use_container_width=True,
            hide_index=True,
            column_config={
                'data_reabertura': st.column_config.DatetimeColumn('Reabertura'),
            },
        )
    else:
        st.info('Nenhuma reabertura identificada.')


def _render_operacional(dados):
    st.subheader('⚙️ Análise de Problemas Operacionais')
    st.caption(
        'Identifica reincidências, tickets parados, demora no atendimento, '
        'violações de SLA e concentração de problemas.'
    )

    parados = dados['tickets_parados']
    sla = dados['sla_estourado']
    tempo = dados['tempo_por_motivo']

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric('Tickets parados', len(parados) if parados is not None else 0)
    with col2:
        st.metric('SLA estourado', len(sla) if sla is not None else 0)
    with col3:
        st.metric('Tempo médio resolução',
                  f"{tempo['tempo_medio_horas'].mean():.1f}h" if tempo is not None and not tempo.empty else '—')

    st.divider()

    # Tickets parados
    st.write('**Tickets parados (sem movimento há mais de 7 dias)**')
    if parados is not None and not parados.empty:
        st.dataframe(
            parados.head(20),
            use_container_width=True,
            hide_index=True,
            column_config={
                'dias_sem_movimento': st.column_config.NumberColumn('Dias parado'),
                'ultima_movimentacao': st.column_config.DatetimeColumn('Última mov.'),
            },
        )
    else:
        st.info('Nenhum ticket parado identificado.')

    st.divider()

    # SLA estourado
    st.write('**Violações de SLA**')
    if sla is not None and not sla.empty:
        st.dataframe(
            sla.head(20),
            use_container_width=True,
            hide_index=True,
            column_config={
                'atraso_horas': st.column_config.NumberColumn('Atraso (h)', format='%.1f'),
                'previsao': st.column_config.DatetimeColumn('Previsão'),
                'data_resolvido': st.column_config.DatetimeColumn('Resolvido em'),
            },
        )
    else:
        st.info('Nenhum SLA estourado identificado.')

    st.divider()

    # Tempo de resolução por motivo
    st.write('**Tempo médio de resolução por motivo (top 15)**')
    if tempo is not None and not tempo.empty:
        st.bar_chart(
            tempo.set_index('motivo')['tempo_medio_horas'],
            use_container_width=True,
        )
        st.dataframe(
            tempo.head(15),
            use_container_width=True,
            hide_index=True,
            column_config={
                'tempo_medio_horas': st.column_config.NumberColumn('Tempo médio (h)', format='%.1f'),
                'qtd_tickets': st.column_config.NumberColumn('Tickets'),
            },
        )
    else:
        st.info('Sem dados de tempo de resolução.')


def _render_recomendacoes(dados):
    st.subheader('💡 Recomendações Inteligentes')
    st.caption(
        'Sugestões geradas automaticamente com base nos padrões encontrados nos dados, '
        'cada uma com evidências e ação recomendada.'
    )

    recom = dados['recomendacoes']
    if recom is not None and not recom.empty:
        for _, row in recom.iterrows():
            prioridade = row.get('prioridade', 'Média')
            cor = {
                'Alta': '🔴',
                'Média': '🟡',
                'Baixa': '🟢',
            }.get(prioridade, '⚪')

            with st.expander(
                f"{cor} [{row.get('tipo', '')}] {row.get('problema', '')}"
            ):
                st.write(f"**Problema:** {row.get('problema', '')}")
                st.write(f"**Evidências:** {row.get('evidencias', '')}")
                st.write(f"**Ação recomendada:** {row.get('acao_recomendada', '')}")
    else:
        st.info('Nenhuma recomendação gerada ainda.')


def _render_investigacao(dados):
    st.subheader('🔎 Investigação Detalhada')
    st.caption(
        'Clique em um assunto para visualizar os tickets relacionados, entender o '
        'padrão identificado e consultar os exemplos que fundamentaram a análise.'
    )

    ranking = dados['ranking_assuntos']
    if ranking is not None and not ranking.empty:
        assunto_selecionado = st.selectbox(
            'Selecione um assunto para investigar:',
            options=ranking['assunto'].tolist(),
        )

        # Carrega tickets brutos para investigação detalhada
        import sqlite3
        conn = sqlite3.connect(RAIZ / 'dados' / 'tickets.db')
        tickets = pd.read_sql('SELECT * FROM tickets', conn)
        conn.close()

        col_motivo = 'motivo_real' if 'motivo_real' in tickets.columns else 'categoria'
        tickets_assunto = tickets[tickets[col_motivo] == assunto_selecionado]

        st.write(f'**Tickets encontrados:** {len(tickets_assunto)}')

        if not tickets_assunto.empty:
            # Mostra amostra
            st.write('**Amostra de tickets:**')
            st.dataframe(
                tickets_assunto[['id', 'titulo', 'descricao', 'status', 'criado_data', 'sistema', 'area']].head(10),
                use_container_width=True,
                hide_index=True,
                column_config={
                    'criado_data': st.column_config.DatetimeColumn('Criado em'),
                },
            )

            # Evolução desse assunto específico
            tickets_assunto_copia = tickets_assunto.copy()
            tickets_assunto_copia['criado_data'] = pd.to_datetime(
                tickets_assunto_copia['criado_data'], errors='coerce'
            )
            tickets_assunto_copia = tickets_assunto_copia[
                tickets_assunto_copia['criado_data'].notna()
            ]
            tickets_assunto_copia['mes'] = tickets_assunto_copia['criado_data'].dt.to_period('M')
            evo_assunto = tickets_assunto_copia.groupby('mes').size().reset_index()
            evo_assunto.columns = ['mes', 'qtd']
            evo_assunto['mes_str'] = evo_assunto['mes'].astype(str)

            st.write('**Evolução mensal desse assunto:**')
            st.line_chart(
                evo_assunto.set_index('mes_str')['qtd'],
                use_container_width=True,
            )
    else:
        st.info('Sem dados de assuntos para investigar.')

