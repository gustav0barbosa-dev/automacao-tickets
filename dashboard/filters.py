# ============================================================
# dashboard/filters.py — Sidebar de filtros
# ============================================================

from datetime import datetime
import streamlit as st


def aplicar_filtros(df):
    """Aplica filtros globais do sidebar. Retorna df filtrado."""

    st.sidebar.markdown('### 🔍 Filtros')

    # ==================== PERÍODO ====================
    if df['criado_data'].notna().any():
        data_min = df['criado_data'].min().date()
        data_max = df['criado_data'].max().date()
    else:
        data_min = data_max = datetime.now().date()

    periodo = st.sidebar.date_input(
        'Período (criado em)',
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max,
    )
    if len(periodo) == 2:
        ini, fim = periodo
        df = df[
            (df['criado_data'].dt.date >= ini) &
            (df['criado_data'].dt.date <= fim)
        ]

    # ==================== STATUS ====================
    st.sidebar.markdown('**Status**')
    status_opts = sorted(df['status'].dropna().unique().tolist())
    status_sel = st.sidebar.multiselect(
        'Status', options=status_opts, default=status_opts,
        label_visibility='collapsed',
    )
    if status_sel:
        df = df[df['status'].isin(status_sel)]

    # ==================== CATEGORIA ====================
    st.sidebar.markdown('**Categoria**')
    cat_opts = sorted(df['categoria'].dropna().unique().tolist())
    cat_sel = st.sidebar.multiselect(
        'Categoria', options=cat_opts, default=[],
        placeholder='Todas as categorias',
        label_visibility='collapsed',
    )
    if cat_sel:
        df = df[df['categoria'].isin(cat_sel)]

    # ==================== RESPONSÁVEL ====================
    st.sidebar.markdown('**Responsável**')
    resp_opts = sorted([
        r for r in df['responsavel_atual'].dropna().unique()
        if r and r != 'Não informado'
    ])
    resp_sel = st.sidebar.multiselect(
        'Responsável', options=resp_opts, default=[],
        placeholder='Todos os responsáveis',
        label_visibility='collapsed',
    )
    if resp_sel:
        df = df[df['responsavel_atual'].isin(resp_sel)]

    # ==================== TIPO DE EMPRESA ====================
    st.sidebar.markdown('**Tipo de Empresa**')
    empresa_opts = ['SPPREV', 'Atlantic', 'Externo', 'Outro']

    if 'responsavel_empresa' in df.columns:
        existentes = df['responsavel_empresa'].dropna().unique().tolist()
        empresa_opts = [e for e in empresa_opts if e in existentes]

    empresa_sel = st.sidebar.multiselect(
        'Tipo Empresa',
        options=empresa_opts,
        default=[],
        placeholder='Todas as empresas',
        label_visibility='collapsed',
    )
    if empresa_sel and 'responsavel_empresa' in df.columns:
        df = df[df['responsavel_empresa'].isin(empresa_sel)]

    # ==================== STATUS DE RESPOSTA ====================
    st.sidebar.markdown('**Status de Resposta**')
    respostas = st.sidebar.radio(
        'Status de Resposta',
        options=['Todos', 'Respondidos', 'Não respondidos'],
        index=0,
        label_visibility='collapsed',
    )
    if respostas == 'Respondidos' and 'respondido' in df.columns:
        df = df[df['respondido'] == 1]
    elif respostas == 'Não respondidos' and 'respondido' in df.columns:
        df = df[df['respondido'] == 0]

    # ==================== BACKLOG ====================
    st.sidebar.markdown('**Backlog**')
    backlog_sel = st.sidebar.radio(
        'Backlog',
        options=['Todos', 'Em backlog', 'Fora do backlog'],
        index=0,
        label_visibility='collapsed',
    )
    if backlog_sel == 'Em backlog' and 'backlog' in df.columns:
        df = df[df['backlog'] == 1]
    elif backlog_sel == 'Fora do backlog' and 'backlog' in df.columns:
        df = df[df['backlog'] == 0]

    # ==================== AÇÃO INTERNA (DESTAQUE) ====================
    st.sidebar.markdown(
        '<div style="border-top:2px solid #c9a666; margin:18px 0 12px 0; padding-top:10px;">'
        '<div style="font-size:11px; color:#c9a666; text-transform:uppercase; '
        'letter-spacing:1px; font-weight:600;">⚡ Ação Interna</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    acao_sel = st.sidebar.radio(
        'Ação Interna',
        options=['Todos', 'Resp. = Alterador', 'Resp. ≠ Alterador'],
        index=0,
        label_visibility='collapsed',
    )
    if acao_sel == 'Resp. = Alterador' and 'acao_interna' in df.columns:
        df = df[df['acao_interna'] == 1]
    elif acao_sel == 'Resp. ≠ Alterador' and 'acao_interna' in df.columns:
        df = df[df['acao_interna'] == 0]

    # ==================== CONTADOR ====================
    st.sidebar.markdown(f'''
        <div class="filtered-count">
            <div class="num">{len(df)}</div>
            <div class="lbl">TICKETS FILTRADOS</div>
        </div>
        <div style="font-size:11px;color:#5c6270;padding:10px 4px 0 4px;">
            Atualizado em {datetime.now():%d/%m/%Y · %H:%M}
        </div>
    ''', unsafe_allow_html=True)

    return df