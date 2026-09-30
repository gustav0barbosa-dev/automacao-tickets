# ============================================================
# dashboard/views/relatorios.py — Relatórios customizados
# ============================================================

import io
from datetime import datetime

import pandas as pd
import streamlit as st
from data import get_engine

from components import (
    global_header, chart_card, empty_state, kpi,
)
from lucide import lucide


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

    # ==================== GERA O RELATÓRIO ====================
    # Usa o df filtrado do dashboard
    try:
        from scripts.relatorio_resolvidos import gerar_relatorio
    except ImportError:
        # Fallback: importa do caminho correto
        import sys
        from pathlib import Path
        RAIZ = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(RAIZ / 'scripts'))
        from relatorio_resolvidos import gerar_relatorio

    # Extrai período do df filtrado
    if df['criado_data'].notna().any():
        data_inicio = df['criado_data'].min().date()
        data_fim = df['criado_data'].max().date()
    else:
        data_inicio = data_fim = datetime.now().date()

    # Gera o relatório
    with st.spinner('Gerando relatório...'):
        engine = get_engine()
        try:
            df_relatorio = gerar_relatorio(
                str(data_inicio),
                str(data_fim),
                engine=engine,
            )
        except Exception as e:
            st.error(f'❌ Erro ao gerar relatório: {e}')

            # ==================== DEBUG: mostra o schema ====================
            with st.expander('🔍 Debug: Schema do banco'):
                from data import get_engine
                from sqlalchemy import text

                engine = get_engine()
                if engine:
                    with engine.connect() as conn:
                        st.write('**Colunas de tickets:**')
                        r = conn.execute(text('''
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_name = 'tickets'
                            ORDER BY ordinal_position
                        '''))
                        st.dataframe([dict(row._mapping) for row in r])

                        st.write('**Colunas de movimentacoes:**')
                        r = conn.execute(text('''
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_name = 'movimentacoes'
                            ORDER BY ordinal_position
                        '''))
                        st.dataframe([dict(row._mapping) for row in r])
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
    reabertos = ((df_relatorio['Data 1º Resolvido'] != df_relatorio['Data Último Resolvido'])
                 & df_relatorio['Data 1º Resolvido'].notna()
                 & df_relatorio['Data Último Resolvido'].notna()).sum()

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
        # Formata datas pra exibição
        df_exibir = df_relatorio.copy()
        for col in ['Data 1º Resolvido', 'Data Último Resolvido', 'Previsão']:
            if col in df_exibir.columns:
                df_exibir[col] = pd.to_datetime(df_exibir[col], errors='coerce')
                df_exibir[col] = df_exibir[col].dt.strftime('%d/%m/%Y %H:%M')

        # Mostra as 20 primeiras
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
        # Gera o Excel em memória
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

    # Formata datas
    for col in ['Data 1º Resolvido', 'Data Último Resolvido', 'Previsão']:
        if col in df_export.columns:
            df_export[col] = pd.to_datetime(df_export[col], errors='coerce')
            df_export[col] = df_export[col].dt.strftime('%d/%m/%Y %H:%M')

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, sheet_name='Resolvidos', index=False)

        # Ajusta largura das colunas
        ws = writer.sheets['Resolvidos']
        for col in ws.columns:
            max_len = max((len(str(c.value or '')) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    buffer.seek(0)
    return buffer