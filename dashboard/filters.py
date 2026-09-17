# ============================================================
# dashboard/filters.py — Sidebar de filtros
# ============================================================

from datetime import datetime
import streamlit as st


def aplicar_filtros(df):
    """Aplica filtros globais do sidebar. Retorna df filtrado."""
    st.sidebar.markdown('### 🔍 Filtros')

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

    st.sidebar.markdown('**Status**')
    status_opts = sorted(df['status'].dropna().unique().tolist())
    status_sel = st.sidebar.multiselect(
        'Status', options=status_opts, default=status_opts,
        label_visibility='collapsed',
    )
    if status_sel:
        df = df[df['status'].isin(status_sel)]

    st.sidebar.markdown('**Categoria**')
    cat_opts = sorted(df['categoria'].dropna().unique().tolist())
    cat_sel = st.sidebar.multiselect(
        'Categoria', options=cat_opts, default=[],
        placeholder='Todas as categorias',
        label_visibility='collapsed',
    )
    if cat_sel:
        df = df[df['categoria'].isin(cat_sel)]

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

    # Filtro por Empresa (Atlantic vs SPPREV)
    st.sidebar.markdown('**Tipo de Empresa**')
    empresa_opts = ['Atlantic Solutions', 'SPPREV']

    empresa_sel = st.sidebar.multiselect(
        'Tipo Empresa',
        options=empresa_opts,
        default=[],
        placeholder='Todas as empresas',
        label_visibility='collapsed',
    )

    if empresa_sel:
        # Mapeia responsável → empresa
        conn = sqlite3.connect(CAMINHO_BANCO)
        analistas = pd.read_sql(
            'SELECT nome, empresa_tipo FROM analistas', conn
        )
        conn.close()

        # Ajusta o rótulo para bater com o df
        mapa = dict(zip(analistas['nome'], analistas['empresa_tipo']))

        # Traduz escolha para tipo interno
        tipos = []
        if 'Atlantic Solutions' in empresa_sel:
            tipos.append('Atlantic')
        if 'SPPREV' in empresa_sel:
            tipos.append('SPPREV')

        df['empresa_responsavel'] = df['responsavel_atual'].map(mapa).fillna('Outro')
        df = df[df['empresa_responsavel'].isin(tipos)]

        # Filtro por Status de Resposta
    st.sidebar.markdown('**Status de Resposta**')
    respostas = st.sidebar.radio(
        'Status de Resposta',
        options=['Todos', 'Não respondidos', 'Respondidos'],
        index=0,
        label_visibility='collapsed',
    )

    if respostas == 'Não respondidos':
        df = df[df['respondido'] == 0]
    elif respostas == 'Respondidos':
        df = df[df['respondido'] == 1]

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