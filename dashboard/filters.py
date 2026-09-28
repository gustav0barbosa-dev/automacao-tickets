# ============================================================
# dashboard/filters.py — Sidebar de filtros (refatorado)
# ============================================================

from datetime import datetime
import streamlit as st

from lucide import lucide


def _secao(titulo, icone):
    """Rótulo de seção na sidebar."""
    st.sidebar.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;'
        f'padding:18px 14px 8px 14px;">'
        f'<span style="color:#c9a666;">{lucide(icone, 14)}</span>'
        f'<span style="font-size:10.5px;color:#5c6270;letter-spacing:1.2px;'
        f'text-transform:uppercase;font-weight:600;">{titulo}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _campo(label, key, widget):
    """Renderiza um campo de filtro padronizado."""
    st.sidebar.markdown(
        f'<div style="font-size:11px;color:#9299a6;padding:6px 14px 4px 14px;">{label}</div>',
        unsafe_allow_html=True,
    )
    return widget


def aplicar_filtros(df):
    """Aplica filtros globais do sidebar. Retorna df filtrado."""

    # ==================== CABEÇALHO ====================
    st.sidebar.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;'
        f'padding:8px 14px 4px 14px;">'
        f'<span style="color:#c9a666;">{lucide("filter", 16)}</span>'
        f'<span style="font-size:13px;font-weight:600;color:#eae7e1;">Filtros</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ==================== BUSCA POR ID ====================
    _secao('Busca', 'search')
    busca_id = st.sidebar.text_input(
        'Buscar por ID',
        placeholder='Ex: 111239 (aceita vírgula)',
        label_visibility='collapsed',
        key='busca_id',
    )
    if busca_id.strip():
        try:
            ids_busca = [int(x.strip()) for x in busca_id.split(',') if x.strip().isdigit()]
            if ids_busca:
                df = df[df['id'].isin(ids_busca)]
        except Exception:
            pass

    # ==================== PERÍODO ====================
    _secao('Período', 'clock')
    if df['criado_data'].notna().any():
        data_min = df['criado_data'].min().date()
        data_max = df['criado_data'].max().date()
    else:
        data_min = data_max = datetime.now().date()

    periodo = st.sidebar.date_input(
        'Período',
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max,
        label_visibility='collapsed',
    )
    if len(periodo) == 2:
        ini, fim = periodo
        df = df[
            (df['criado_data'].dt.date >= ini) &
            (df['criado_data'].dt.date <= fim)
        ]

    # ==================== CLASSIFICAÇÃO ====================
    _secao('Classificação', 'filter')

    status_opts = sorted(df['status'].dropna().unique().tolist())
    status_sel = _campo(
        'Status',
        'status',
        st.sidebar.multiselect(
            'Status', options=status_opts, default=status_opts,
            label_visibility='collapsed', key='f_status',
        ),
    )
    if status_sel:
        df = df[df['status'].isin(status_sel)]

    cat_opts = sorted(df['categoria'].dropna().unique().tolist())
    cat_sel = _campo(
        'Categoria',
        'categoria',
        st.sidebar.multiselect(
            'Categoria', options=cat_opts, default=[],
            placeholder='Todas as categorias',
            label_visibility='collapsed', key='f_categoria',
        ),
    )
    if cat_sel:
        df = df[df['categoria'].isin(cat_sel)]

    # ==================== ORIGEM ====================
    _secao('Origem', 'users')

    resp_opts = sorted([
        r for r in df['responsavel_atual'].dropna().unique()
        if r and r != 'Não informado'
    ])
    resp_sel = _campo(
        'Responsável',
        'responsavel',
        st.sidebar.multiselect(
            'Responsável', options=resp_opts, default=[],
            placeholder='Todos',
            label_visibility='collapsed', key='f_resp',
        ),
    )
    if resp_sel:
        df = df[df['responsavel_atual'].isin(resp_sel)]

    sol_opts = sorted([
        s for s in df['solicitante'].dropna().unique()
        if s and s != 'Não informado'
    ])
    sol_sel = _campo(
        'Solicitante',
        'solicitante',
        st.sidebar.multiselect(
            'Solicitante', options=sol_opts, default=[],
            placeholder='Todos',
            label_visibility='collapsed', key='f_sol',
        ),
    )
    if sol_sel:
        df = df[df['solicitante'].isin(sol_sel)]

    # ==================== ESTADO ====================
    _secao('Estado', 'activity')

    respostas = _campo(
        'Resposta',
        'resposta',
        st.sidebar.radio(
            'Status de Resposta',
            options=['Todos', 'Respondidos', 'Não respondidos'],
            index=0, label_visibility='collapsed', key='f_resp_status',
        ),
    )
    if respostas == 'Respondidos' and 'respondido' in df.columns:
        df = df[df['respondido'] == 1]
    elif respostas == 'Não respondidos' and 'respondido' in df.columns:
        df = df[df['respondido'] == 0]

    backlog_sel = _campo(
        'Backlog',
        'backlog',
        st.sidebar.radio(
            'Backlog',
            options=['Todos', 'Em backlog', 'Fora do backlog'],
            index=0, label_visibility='collapsed', key='f_backlog',
        ),
    )
    if backlog_sel == 'Em backlog' and 'backlog' in df.columns:
        df = df[df['backlog'] == 1]
    elif backlog_sel == 'Fora do backlog' and 'backlog' in df.columns:
        df = df[df['backlog'] == 0]

    reininc_sel = _campo(
        'Reincidência',
        'reinc',
        st.sidebar.radio(
            'Só Reincidentes',
            options=['Todos', 'Só reincidentes'],
            index=0, label_visibility='collapsed', key='filtro_reinc',
        ),
    )
    if reininc_sel == 'Só reincidentes':
        contagem = df.groupby('solicitante')['id'].count()
        reincidentes = contagem[contagem >= 2].index.tolist()
        df = df[df['solicitante'].isin(reincidentes)]

    # ==================== EMPRESA ====================
    _secao('Empresa', 'zap')

    empresa_opts = ['SPPREV', 'Atlantic', 'Externo', 'Outro']
    if 'responsavel_empresa' in df.columns:
        existentes = df['responsavel_empresa'].dropna().unique().tolist()
        empresa_opts = [e for e in empresa_opts if e in existentes]

    empresa_sel = _campo(
        'Tipo de empresa',
        'empresa',
        st.sidebar.multiselect(
            'Tipo Empresa', options=empresa_opts, default=[],
            placeholder='Todas',
            label_visibility='collapsed', key='f_empresa',
        ),
    )
    if empresa_sel and 'responsavel_empresa' in df.columns:
        df = df[df['responsavel_empresa'].isin(empresa_sel)]

    # ==================== AÇÃO INTERNA ====================
    _secao('Ação interna', 'zap')
    acao_sel = st.sidebar.radio(
        'Ação Interna',
        options=['Todos', 'Resp. = Alterador', 'Resp. ≠ Alterador'],
        index=0, label_visibility='collapsed', key='f_acao_interna',
    )
    if acao_sel == 'Resp. = Alterador' and 'acao_interna' in df.columns:
        df = df[df['acao_interna'] == 1]
    elif acao_sel == 'Resp. ≠ Alterador' and 'acao_interna' in df.columns:
        df = df[df['acao_interna'] == 0]

    # ==================== CONTADOR ====================
    st.sidebar.markdown(f'''
        <div class="filtered-count">
            <div class="num">{len(df)}</div>
            <div class="lbl">TICKETS ENCONTRADOS</div>
        </div>
        <div style="font-size:10.5px;color:#5c6270;padding:10px 4px 16px 4px;">
            Atualizado em {datetime.now():%d/%m · %H:%M}
        </div>
    ''', unsafe_allow_html=True)

    return df