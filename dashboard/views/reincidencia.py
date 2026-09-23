# ============================================================
# dashboard/views/reincidencia.py
# ============================================================
# Duas análises em uma única aba:
#
#   SEÇÃO 1 — FREQUÊNCIA POR SOLICITANTE
#       Quantos tickets cada pessoa abriu
#
#   SEÇÃO 2 — REABERTURA
#       Tickets que voltaram após "Resolvido" ou "Fechado"
# ============================================================

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
    botao_exportar, legenda_grafico, info_grafico,
)
from config import COR_GOLD, COR_SUCCESS, COR_DANGER, COR_WARNING
from data import carregar_movimentacoes


# ============================================================
# ANÁLISE DE REABERTURA
# ============================================================
def detectar_reaberturas(df_movs, data_inicio=None, data_fim=None):
    """
    Detecta tickets que foram reabertos no período.
    
    Uma reabertura = de_status em ('Resolvido', 'Fechado')
                 E para_status em ('Em atendimento', 'Aguardando confirmação do usuário')
    
    Filtra por data_movimentacao dentro do período [data_inicio, data_fim].
    """
    if df_movs.empty:
        return pd.DataFrame(columns=[
            'ticket_id', 'reaberto_vezes',
            'data_primeira_reabertura', 'data_ultima_reabertura'
        ])

    df = df_movs.copy()
    df['data_movimentacao'] = pd.to_datetime(df['data_movimentacao'], errors='coerce')
    df = df.dropna(subset=['data_movimentacao'])

    # Filtro por período (data da movimentação)
    if data_inicio is not None:
        df = df[df['data_movimentacao'].dt.date >= data_inicio]
    if data_fim is not None:
        df = df[df['data_movimentacao'].dt.date <= data_fim]

    if df.empty:
        return pd.DataFrame(columns=[
            'ticket_id', 'reaberto_vezes',
            'data_primeira_reabertura', 'data_ultima_reabertura'
        ])

    # Filtra apenas as reaberturas
    status_reaberto = ['Resolvido', 'Fechado']
    status_voltou = ['Em atendimento', 'Aguardando confirmação do usuário']

    df_reab = df[
        df['de_status'].isin(status_reaberto) &
        df['para_status'].isin(status_voltou)
    ].copy()

    if df_reab.empty:
        return pd.DataFrame(columns=[
            'ticket_id', 'reaberto_vezes',
            'data_primeira_reabertura', 'data_ultima_reabertura'
        ])

    # Agrupa por ticket
    resultado = df_reab.groupby('ticket_id').agg(
        reaberto_vezes=('id', 'count'),
        data_primeira_reabertura=('data_movimentacao', 'min'),
        data_ultima_reabertura=('data_movimentacao', 'max'),
    ).reset_index()

    return resultado


# ============================================================
# RENDER
# ============================================================
def render(df):
    page_header('Reincidência', 'de Tickets',
                'Análise de frequência por solicitante e reabertura de tickets.')

    # ============================================================
    # SEÇÃO 1 — FREQUÊNCIA POR SOLICITANTE
    # ============================================================
    st.markdown('## 📊 Seção 1 — Frequência por Solicitante')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Quantos tickets cada pessoa abriu no período filtrado'
                '</div>',
                unsafe_allow_html=True)

    # Filtra solicitantes válidos
    df_sol = df[
        df['solicitante'].notna() &
        (df['solicitante'] != '') &
        (df['solicitante'] != 'Não informado')
    ].copy()

    if df_sol.empty:
        callout('warning', 'Atenção', 'Sem solicitantes identificados no período.')
    else:
        # Agrega por solicitante
        agg = df_sol.groupby('solicitante').agg(
            total=('id', 'count'),
            primeiro=('criado_data', 'min'),
            ultimo=('criado_data', 'max'),
            categorias=('categoria', lambda x: x.nunique()),
        ).reset_index()
        agg.columns = ['Solicitante', 'Total', 'Primeiro', 'Último', 'Categorias']

        # KPIs
        total_solicitantes = len(agg)
        reincidentes = len(agg[agg['Total'] >= 2])
        muito_reincidentes = len(agg[agg['Total'] >= 5])
        taxa = (reincidentes / total_solicitantes * 100) if total_solicitantes else 0
        media = agg['Total'].mean()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            kpi('Solicitantes Únicos', f'{total_solicitantes}')
        with col2:
            kpi('Com 2+ Tickets', f'{reincidentes}',
                pill=f'{taxa:.0f}%',
                pill_tipo='negative' if taxa > 30 else 'neutral')
        with col3:
            kpi('Média Tickets/Pessoa', f'{media:.1f}')
        with col4:
            kpi('Com 5+ Tickets', f'{muito_reincidentes}',
                pill='⚠️ Atenção' if muito_reincidentes > 0 else 'OK',
                pill_tipo='negative' if muito_reincidentes > 0 else 'positive')

        st.markdown('')

        # Distribuição + Top 10
        col_a, col_b = st.columns(2)

        with col_a:
            painel_title('Distribuição de <b>tickets por solicitante</b>')
            dist = agg['Total'].value_counts().sort_index().reset_index()
            dist.columns = ['qtd', 'solicitantes']

            dist_final = dist[dist['qtd'] <= 4].copy()
            qtd_5mais = dist[dist['qtd'] >= 5]['solicitantes'].sum()
            if qtd_5mais > 0:
                dist_final = pd.concat([
                    dist_final,
                    pd.DataFrame([{'qtd': '5+', 'solicitantes': qtd_5mais}])
                ])

            hbar_list([
                {'label': str(r['qtd']) + (' ticket' if r['qtd'] == 1 else ' tickets'),
                 'value': int(r['solicitantes']),
                 'formatted': str(int(r['solicitantes'])),
                 'accent': str(r['qtd']) == '5+'}
                for _, r in dist_final.iterrows()
            ])

        with col_b:
            painel_title('Top 10 <b>solicitantes</b>')
            top = agg.nlargest(10, 'Total').sort_values('Total')

            hbar_list([
                {'label': r['Solicitante'][:22],
                 'value': int(r['Total']),
                 'formatted': str(int(r['Total'])),
                 'accent': r['Total'] >= 5}
                for _, r in top.iterrows()
            ])

        # Insights
        if not agg.empty:
            top1 = agg.nlargest(1, 'Total').iloc[0]
            if top1['Total'] >= 5:
                callout('warning', 'Atenção',
                        f'<b>{top1["Solicitante"]}</b> abriu '
                        f'<b>{int(top1["Total"])} tickets</b> '
                        f'em {int(top1["Categorias"])} categoria(s).')

    separador()

    # ============================================================
    # SEÇÃO 2 — REABERTURA (DEBUG)
    # ============================================================
    st.markdown('## 🔄 Seção 2 — Reabertura de Tickets')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Tickets que voltaram para "Em atendimento" após serem '
                'marcados como "Resolvido" ou "Fechado"'
                '</div>',
                unsafe_allow_html=True)

    # Carrega movimentações
    df_movs = carregar_movimentacoes()

    st.markdown('### 🐛 DEBUG PASSO A PASSO')

    # --- PASSO 1: O que veio do banco? ---
    st.write(f"**1. Movimentações carregadas:** `{len(df_movs)}`")
    if not df_movs.empty:
        st.write(f"   - Colunas: `{df_movs.columns.tolist()}`")
        st.write(f"   - Tipo de `de_status`: `{df_movs['de_status'].dtype}`")
        st.write(f"   - Tipo de `para_status`: `{df_movs['para_status'].dtype}`")
        st.write(f"   - Tipo de `data_movimentacao`: `{df_movs['data_movimentacao'].dtype}`")
        st.write(f"   - Amostra:")
        st.dataframe(df_movs[['ticket_id', 'data_movimentacao', 'de_status', 'para_status']].head(10))

    # --- PASSO 2: Quantas reaberturas o filtro SQL direto pega? ---
    if not df_movs.empty:
        df_reab_raw = df_movs[
            df_movs['de_status'].isin(['Resolvido', 'Fechado']) &
            df_movs['para_status'].isin(['Em atendimento', 'Aguardando confirmação do usuário'])
        ]
        st.write(f"**2. Reaberturas via filtro direto (sem função):** `{len(df_reab_raw)}`")

        # --- PASSO 3: Quantas a função detectar_reaberturas retorna? ---
        df_reab_func = detectar_reaberturas(df_movs)
        st.write(f"**3. Reaberturas via `detectar_reaberturas(df_movs)`:** `{len(df_reab_func)}`")
        if not df_reab_func.empty:
            st.dataframe(df_reab_func.head(10))

        # --- PASSO 4: Quantos IDs do df filtrado batem? ---
        ids_filtrados = set(df['id'].astype(str).tolist())
        st.write(f"**4. Total de IDs no df filtrado:** `{len(ids_filtrados)}`")
        if not df_reab_func.empty:
            df_reab_func['ticket_id'] = df_reab_func['ticket_id'].astype(str)
            matches = df_reab_func['ticket_id'].isin(ids_filtrados).sum()
            st.write(f"**5. Tickets reabertos que estão no df filtrado:** `{matches}`")

            # Mostra exemplos dos que NÃO batem
            nao_batem = df_reab_func[~df_reab_func['ticket_id'].isin(ids_filtrados)]
            if not nao_batem.empty:
                st.write(f"   ⚠️ Exemplos de reabertos que NÃO estão no filtro:")
                st.write(f"   - IDs reabertos: `{nao_batem['ticket_id'].head(5).tolist()}`")
                st.write(f"   - Amostra de IDs filtrados: `{list(ids_filtrados)[:5]}`")

    # ============================================================
    # EXPORTAR
    # ============================================================
    separador()

    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        # Exporta um resumo consolidado
        df_export = df_sol if not df_sol.empty else pd.DataFrame()
        botao_exportar(df_export, 'reincidencia', key='export_reincidencia')