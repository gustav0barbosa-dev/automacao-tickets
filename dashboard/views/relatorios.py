# ============================================================
# dashboard/views/relatorios.py — Relatórios customizados
# ============================================================

import io
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from components import (
    global_header, chart_card, empty_state, kpi,
)
from lucide import lucide


# ==================== IMPORTS ====================
# Adiciona scripts/ ao sys.path pra importar relatorio_resolvidos
RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ / 'scripts'))


def render(df):
    # ==================== HEADER ====================
    global_header(
        'Relatórios',
        'Exportação de relatórios customizados.',
        usuario=st.session_state.get('usuario'),
    )

    # ==================== RELATÓRIO: RESOLVIDOS ====================
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'margin:24px 0 6px 0;">'
        f'<span style="color:#c9a666;">{lucide("download", 20)}</span>'
        f'<span style="font-family:Fraunces,serif;font-size:22px;font-weight:600;">'
        f'Relatório de Resolvidos</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="font-size:13px;color:#9299a6;margin-bottom:20px;">'
        'Lista de tickets que <b>fecharam no período filtrado</b>, '
        'com data do 1º e último resolvido, quem alterou e previsão.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ==================== BOTÃO GERAR ====================
    if not st.session_state.get('gerar_relatorio'):
        if st.button('🔄 Gerar Relatório', key='btn_gerar_relatorio',
                     use_container_width=True):
            st.session_state['gerar_relatorio'] = True
            st.rerun()
        st.info('Clique em "Gerar Relatório" para carregar os dados.')
        return

    # ==================== IMPORTA A FUNÇÃO ====================
    try:
        from relatorio_resolvidos import gerar_relatorio
    except ImportError as e:
        st.error(f'❌ Erro ao importar: {e}')
        return

    # ==================== ENGINE ====================
    from data import get_engine
    engine = get_engine()

    if engine is None:
        st.error('❌ Não foi possível conectar ao banco.')
        return

    # ==================== PERÍODO ====================
    if df['criado_data'].notna().any():
        data_inicio = df['criado_data'].min().date()
        data_fim = df['criado_data'].max().date()
    else:
        data_inicio = data_fim = datetime.now().date()

    # ==================== GERA O RELATÓRIO ====================
    with st.spinner('Gerando relatório...'):
        try:
# ==================== QUERY DIRETO (sem depender do script) ====================
            query = f'''
            WITH
            -- 1. Tickets que FECHARAM no período
            tickets_fechados AS (
                SELECT DISTINCT ticket_id
                FROM movimentacoes
                WHERE para_status = 'Fechado'
                AND data_movimentacao >= '{data_inicio} 00:00:00'
                AND data_movimentacao <= '{data_fim} 23:59:59'
            ),

            -- 2. Tickets que passaram por RESOLVIDO (obrigatório)
            tickets_resolvidos AS (
                SELECT DISTINCT ticket_id
                FROM movimentacoes
                WHERE para_status = 'Resolvido'
            ),

            -- 3. Só os que FECHARAM **E** PASSARAM por RESOLVIDO
            tickets_validos AS (
                SELECT tf.ticket_id
                FROM tickets_fechados tf
                INNER JOIN tickets_resolvidos tr ON tr.ticket_id = tf.ticket_id
            ),

            -- 4. Primeiro resolvido
            primeiro_resolvido AS (
                SELECT
                    ticket_id,
                    data_movimentacao,
                    autor,
                    ROW_NUMBER() OVER (
                        PARTITION BY ticket_id
                        ORDER BY data_movimentacao ASC, id ASC
                    ) AS rn
                FROM movimentacoes
                WHERE para_status = 'Resolvido'
                AND ticket_id IN (SELECT ticket_id FROM tickets_validos)
            ),

            -- 5. Último resolvido ANTES do Fechado
            ultimo_resolvido AS (
                SELECT
                    m.ticket_id,
                    m.data_movimentacao,
                    m.autor,
                    ROW_NUMBER() OVER (
                        PARTITION BY m.ticket_id
                        ORDER BY m.data_movimentacao DESC, m.id DESC
                    ) AS rn
                FROM movimentacoes m
                WHERE m.para_status = 'Resolvido'
                AND m.ticket_id IN (SELECT ticket_id FROM tickets_validos)
                AND m.data_movimentacao <= COALESCE(
                    (SELECT MAX(m2.data_movimentacao)
                    FROM movimentacoes m2
                    WHERE m2.ticket_id = m.ticket_id
                        AND m2.para_status = 'Fechado'),
                    '9999-12-31'
                )
            )

            SELECT
                t.id AS "ID Ticket",
                pr.data_movimentacao AS "Data 1º Resolvido",
                pr.autor AS "Alterado por (1º)",
                ur.data_movimentacao AS "Data Último Resolvido",
                ur.autor AS "Alterado por (Último)",
                t.previsao AS "Previsão"
            FROM tickets t
            INNER JOIN tickets_validos tv ON tv.ticket_id = t.id
            LEFT JOIN primeiro_resolvido pr ON pr.ticket_id = t.id AND pr.rn = 1
            LEFT JOIN ultimo_resolvido ur ON ur.ticket_id = t.id AND ur.rn = 1
            ORDER BY pr.data_movimentacao ASC
            '''

            df_relatorio = pd.read_sql(query, engine)
            
        except Exception as e:
            st.error(f'❌ Erro ao gerar relatório: {e}')
            st.exception(e)
            return

    if df_relatorio.empty:
        empty_state(
            titulo='Sem tickets no período',
            descricao='Nenhum ticket fechou no período filtrado.',
            icone='inbox',
        )
        return

    # ==================== KPIs ====================
    total = len(df_relatorio)
    com_1resolvido = df_relatorio['Data 1º Resolvido'].notna().sum()
    com_ultimo = df_relatorio['Data Último Resolvido'].notna().sum()
    reabertos = (
        (df_relatorio['Data 1º Resolvido'] != df_relatorio['Data Último Resolvido'])
        & df_relatorio['Data 1º Resolvido'].notna()
        & df_relatorio['Data Último Resolvido'].notna()
    ).sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Tickets Fechados', f'{total}', icone='check-circle')
    with col2:
        kpi('Com 1º Resolvido', f'{com_1resolvido}',
            pill=f'{com_1resolvido/total*100:.0f}%' if total else '—',
            pill_tipo='positive' if com_1resolvido == total else 'neutral',
            icone='clock')
    with col3:
        kpi('Com Último Resolvido', f'{com_ultimo}',
            pill=f'{com_ultimo/total*100:.0f}%' if total else '—',
            pill_tipo='positive' if com_ultimo == total else 'neutral',
            icone='check-circle')
    with col4:
        kpi('Reabertos', f'{reabertos}',
            pill='Atenção' if reabertos > 0 else 'OK',
            pill_tipo='negative' if reabertos > 0 else 'positive',
            icone='refresh-cw')

    st.markdown('')

    # ==================== TABELA ====================
    with chart_card(
        'Preview do Relatório',
        f'{total} tickets fechados entre {data_inicio.strftime("%d/%m/%Y")} e {data_fim.strftime("%d/%m/%Y")}',
        icone='bar-chart',
    ):
        df_exibir = df_relatorio.copy()
        for col in ['Data 1º Resolvido', 'Data Último Resolvido', 'Previsão']:
            if col in df_exibir.columns:
                df_exibir[col] = pd.to_datetime(df_exibir[col], errors='coerce')
                df_exibir[col] = df_exibir[col].dt.strftime('%d/%m/%Y %H:%M')

        st.dataframe(
            df_exibir.head(20),
            use_container_width=True,
            hide_index=True,
        )

        if total > 20:
            st.caption(f'Mostrando 20 de {total} registros. Baixe o Excel para ver todos.')

    # ==================== BOTÃO EXPORTAR ====================
    st.markdown('')

    col_esq, col_centro, col_dir = st.columns([1, 2, 1])
    with col_centro:
        excel_buffer = _gerar_excel(df_relatorio)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        nome_arquivo = f'resolvidos_{data_inicio}_a_{data_fim}_{timestamp}.xlsx'

        st.download_button(
            label='📥 Baixar Relatório (Excel)',
            data=excel_buffer,
            file_name=nome_arquivo,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True,
            key='download_relatorio_resolvidos',
        )


def _gerar_excel(df: pd.DataFrame) -> io.BytesIO:
    """Gera Excel em memória."""
    df_export = df.copy()

    for col in ['Data 1º Resolvido', 'Data Último Resolvido', 'Previsão']:
        if col in df_export.columns:
            df_export[col] = pd.to_datetime(df_export[col], errors='coerce')
            df_export[col] = df_export[col].dt.strftime('%d/%m/%Y %H:%M')

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, sheet_name='Resolvidos', index=False)

        ws = writer.sheets['Resolvidos']
        for col in ws.columns:
            max_len = max((len(str(c.value or '')) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    buffer.seek(0)
    return buffer