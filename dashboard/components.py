# ============================================================
# dashboard/components.py — Componentes visuais reutilizáveis
# ============================================================
"""
Componentes visuais usados em todas as páginas.
Se precisar mudar aparência, edite aqui.
"""

import streamlit as st
import plotly.graph_objects as go
from lucide import lucide
from contextlib import contextmanager

from config import (
    COR_GOLD, COR_BAR, COR_DANGER, COR_TEXT,
    COR_TEXT_SEC, COR_TEXT_TER, COR_GRID,
)


# ==================== COMPONENTES HTML ====================
def kpi(label, valor, pill=None, pill_tipo='neutral', ajuda=None,
        icone=None, tendencia=None, tendencia_valor=None):
    """
    KPI card com wrapper para espaçamento consistente.
    """
    pill_html = f'<span class="kpi-pill {pill_tipo}">{pill}</span>' if pill else ''
    icone_html = lucide(icone, 16) if icone else ''

    trend_html = ''
    if tendencia and tendencia_valor:
        seta = '↑' if tendencia == 'up' else '↓'
        cls = 'positive' if tendencia == 'up' else 'negative'
        trend_html = (
            f'<div class="kpi-trend">'
            f'<span class="kpi-trend-value {cls}">{seta} {tendencia_valor}</span>'
            f'<span>vs. período anterior</span>'
            f'</div>'
        )

    ajuda_html = f'<div class="kpi-help">{ajuda}</div>' if ajuda else ''

    # ⬇️ WRAPPER com margin-bottom
    html = (
        f'<div style="margin-bottom:18px;">'
        f'<div class="kpi-card">'
        f'<div class="kpi-header">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-icon">{icone_html}</div>'
        f'</div>'
        f'<div class="kpi-value-row" style="display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;">'
        f'<span class="kpi-value">{valor}</span>'
        f'{pill_html}'
        f'</div>'
        f'{trend_html}'
        f'{ajuda_html}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def hbar_list(items):
    """Lista de barras horizontais (HTML em linha única)."""
    if not items:
        st.markdown('<div style="color:#5c6270;">sem dados</div>',
                    unsafe_allow_html=True)
        return

    max_val = max(i['value'] for i in items) or 1
    rows = []

    for it in items:
        pct = max(2, (it['value'] / max_val) * 100)
        accent = ' accent' if it.get('accent') else ''
        label = it['label']
        fmt = it.get('formatted', it['value'])

        row = (
            f'<div class="hbar-row">'
            f'<div class="hbar-label">{label}</div>'
            f'<div class="hbar-track">'
            f'<div class="hbar-fill{accent}" style="width:{pct:.1f}%;"></div>'
            f'<div class="hbar-value">{fmt}</div>'
            f'</div>'
            f'</div>'
        )
        rows.append(row)

    html = f'<div class="hbar-list">{"".join(rows)}</div>'
    st.markdown(html, unsafe_allow_html=True)


def callout(tipo, tag, texto):
    """Callout com borda lateral (HTML em linha única)."""
    html = (
        f'<div class="callout {tipo}">'
        f'<span class="tag">{tag}</span>{texto}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def painel_title(texto_html):
    """Título de painel."""
    st.markdown(f'<div class="panel-title">{texto_html}</div>',
                unsafe_allow_html=True)


def separador():
    st.markdown('<hr class="sep">', unsafe_allow_html=True)


def page_header(titulo_normal, titulo_bold, caption):
    """Cabeçalho de página."""
    st.markdown(
        f'<h1>{titulo_normal} <b>{titulo_bold}</b></h1>'
        f'<div class="page-caption">{caption}</div>',
        unsafe_allow_html=True,
    )


def callout(tipo, tag, texto):
    """Callout com borda lateral colorida."""
    st.markdown(f'''
        <div class="callout {tipo}">
            <span class="tag">{tag}</span>{texto}
        </div>
    ''', unsafe_allow_html=True)


def painel_title(texto_html):
    """Título de painel."""
    st.markdown(f'<div class="panel-title">{texto_html}</div>',
                unsafe_allow_html=True)


def separador():
    st.markdown('<hr class="sep">', unsafe_allow_html=True)


def page_header(titulo_normal, titulo_bold, caption):
    """Cabeçalho de página padrão."""
    st.markdown(f'<h1>{titulo_normal} <b>{titulo_bold}</b></h1>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="page-caption">{caption}</div>',
                unsafe_allow_html=True)


# ==================== PLOTLY ====================
def aplicar_tema_plotly(fig, altura=320):
    """Aplica o tema dark ao gráfico."""
    fig.update_layout(
        height=altura,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', color=COR_TEXT_SEC, size=12),
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        hoverlabel=dict(
            bgcolor='#1b2029',
            bordercolor=COR_GOLD,
            font=dict(color=COR_TEXT, size=12),
        ),
    )
    fig.update_xaxes(
        gridcolor=COR_GRID, zerolinecolor=COR_GRID,
        tickfont=dict(color=COR_TEXT_TER),
        linecolor=COR_GRID,
    )
    fig.update_yaxes(
        gridcolor=COR_GRID, zerolinecolor=COR_GRID,
        tickfont=dict(color=COR_TEXT_TER),
        linecolor=COR_GRID,
    )
    return fig

# ==================== EXPORTAR ====================
import io
from datetime import datetime

import pandas as pd


def botao_exportar(df, nome_arquivo, key=None):
    """
    Renderiza um botão de download do DataFrame em Excel.

    Args:
        df: DataFrame a exportar
        nome_arquivo: nome base (sem extensão)
        key: chave única (Streamlit exige para múltiplos botões)
    """
    if df is None or df.empty:
        return

    # Cria buffer em memória
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')

    buffer.seek(0)

    # Nome com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    nome_final = f'{nome_arquivo}_{timestamp}.xlsx'

    st.download_button(
        label='📥 Baixar Excel',
        data=buffer.getvalue(),
        file_name=nome_final,
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key=key or f'export_{nome_arquivo}',
        use_container_width=False,
    )

# ==================== LEGENDAS DE GRÁFICOS ====================
def legenda_grafico(itens):
    """
    Renderiza uma legenda customizada abaixo de um gráfico.
    HTML em linha única (evita que Markdown trate como bloco de código).
    """
    elementos = []

    for it in itens:
        cor = it.get('cor', '#8b96a8')
        label = it.get('label', '')
        tipo = it.get('tipo', 'circulo')

        if tipo == 'linha':
            icone = f'<div style="width:20px;height:3px;background:{cor};border-radius:2px;"></div>'
        elif tipo == 'barra':
            icone = f'<div style="width:14px;height:14px;background:{cor};border-radius:3px;"></div>'
        else:
            icone = f'<div style="width:12px;height:12px;background:{cor};border-radius:50%;"></div>'

        elementos.append(
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'{icone}'
            f'<span style="font-size:12px;color:#9299a6;">{label}</span>'
            f'</div>'
        )

    html = (
        f'<div style="display:flex;gap:20px;flex-wrap:wrap;'
        f'padding:10px 14px;margin-top:8px;'
        f'background:rgba(255,255,255,.02);border-radius:6px;">'
        f'{"".join(elementos)}'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


def info_grafico(texto):
    """
    Renderiza uma caixa de ajuda abaixo do gráfico.
    HTML em linha única.
    """
    html = (
        f'<div style="display:flex;gap:10px;align-items:flex-start;'
        f'padding:10px 14px;margin-top:8px;'
        f'background:rgba(201,166,102,.06);'
        f'border-left:3px solid #c9a666;border-radius:6px;">'
        f'<div style="font-size:14px;color:#c9a666;">ℹ️</div>'
        f'<div style="font-size:12.5px;color:#9299a6;line-height:1.5;">'
        f'{texto}'
        f'</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)

# ==================== HELPERS DE OUTLIERS ====================
from config import LIMITE_OUTLIER_DIAS, LIMITE_FANTASMA_DIAS


def filtrar_outliers(df, coluna='dias_aberto', limite=LIMITE_OUTLIER_DIAS):
    """
    Filtra outliers de um DataFrame.

    Returns:
        (df_clean, n_removidos)
    """
    if df.empty or coluna not in df.columns:
        return df, 0

    df_clean = df[df[coluna] <= limite].copy()
    n_removidos = len(df) - len(df_clean)

    return df_clean, n_removidos


def alerta_fantasmas(df, coluna='dias_aberto', limite=LIMITE_FANTASMA_DIAS):
    """
    Renderiza um alerta sobre tickets "fantasmas" (muito antigos).

    Args:
        df: DataFrame com os tickets
        coluna: coluna de dias
        limite: limite de dias para considerar fantasma
    """
    if df.empty or coluna not in df.columns:
        return

    df_fantasmas = df[df[coluna] > limite].copy()
    n = len(df_fantasmas)

    if n == 0:
        return

    # Card de alerta
    html = (
        f'<div style="display:flex;gap:12px;align-items:center;'
        f'padding:14px 18px;margin-top:16px;'
        f'background:rgba(224,134,122,.08);'
        f'border:1px solid rgba(224,134,122,.2);'
        f'border-left:3px solid #e0867a;border-radius:8px;">'
        f'<div style="font-size:20px;">👻</div>'
        f'<div style="flex:1;">'
        f'<div style="font-size:13px;color:#e0867a;font-weight:600;margin-bottom:2px;">'
        f'{n} ticket(s) em aberto há mais de {limite} dias'
        f'</div>'
        f'<div style="font-size:12px;color:#9299a6;">'
        f'Estes tickets foram excluídos do cálculo de média. '
        f'Considere verificar e fechar os mais antigos.'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    # Expander com detalhes
    with st.expander(f'Ver os {n} tickets fantasmas'):
        tabela = df_fantasmas.nlargest(20, coluna)[
            ['id', 'titulo', 'status', 'responsavel_atual', coluna]
        ].copy()
        tabela.columns = ['ID', 'Título', 'Status', 'Responsável', 'Dias']
        tabela['Título'] = tabela['Título'].str.slice(0, 60)
        st.dataframe(tabela, use_container_width=True, hide_index=True)

# ==================== FASE 1 — CHART-CARD ====================
@contextmanager
def chart_card(titulo=None, descricao=None, icone=None, compact=False):
    css_class = 'chart-card compact' if compact else 'chart-card'

    icone_html = (
        f'<span style="color:#c9a666;margin-right:6px;">{lucide(icone, 16)}</span>'
        if icone else ''
    )
    desc_html = f'<div class="chart-card-desc">{descricao}</div>' if descricao else ''

    header_html = ''
    if titulo:
        header_html = (
            f'<div class="chart-card-header">'
            f'<div>'
            f'<div class="chart-card-title">{icone_html}{titulo}</div>'
            f'{desc_html}'
            f'</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="chart-card-wrapper">'  # ← CLASSE
        f'<div class="{css_class}">{header_html}',
        unsafe_allow_html=True,
    )

    try:
        yield
    finally:
        st.markdown('</div></div>', unsafe_allow_html=True) 


# ==================== FASE 1 — KPI MELHORADO ====================
def kpi(label, valor, pill=None, pill_tipo='neutral', ajuda=None,
        icone=None, tendencia=None, tendencia_valor=None):
    pill_html = f'<span class="kpi-pill {pill_tipo}">{pill}</span>' if pill else ''
    icone_html = lucide(icone, 16) if icone else ''

    trend_html = ''
    if tendencia and tendencia_valor:
        seta = '↑' if tendencia == 'up' else '↓'
        cls = 'positive' if tendencia == 'up' else 'negative'
        trend_html = (
            f'<div class="kpi-trend">'
            f'<span class="kpi-trend-value {cls}">{seta} {tendencia_valor}</span>'
            f'</div>'
        )

    ajuda_html = f'<div class="kpi-help">{ajuda}</div>' if ajuda else ''

    # ⬇️ WRAPPER com classe
    html = (
        f'<div class="kpi-wrapper">'
        f'<div class="kpi-card">'
        f'<div class="kpi-header">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-icon">{icone_html}</div>'
        f'</div>'
        f'<div class="kpi-value-row" style="display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;">'
        f'<span class="kpi-value">{valor}</span>'
        f'{pill_html}'
        f'</div>'
        f'{trend_html}'
        f'{ajuda_html}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ==================== FASE 1 — HEADER GLOBAL ====================
def global_header(titulo_pagina, caption, usuario=None):
    """
    Cabeçalho global (barra superior) + título da página.

    Uso:
        global_header('Visão Geral', 'Panorama dos tickets.', usuario='gustavo')
    """
    user_html = ''
    if usuario:
        user_html = (
            f'<div class="global-header-user">'
            f'{lucide("user", 14)} <span>{usuario}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="global-header">'
        f'<div class="global-header-left">'
        f'<span style="color:var(--gold);">{lucide("activity", 20)}</span>'
        f'<span class="global-header-title">HELP360 ANALYTICS</span>'
        f'</div>'
        f'<div class="global-header-right">'
        f'<span class="global-header-icon">{lucide("bell", 18)}</span>'
        f'{user_html}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Título da página
    st.markdown(
        f'<h1 style="margin-top:8px;">{titulo_pagina}</h1>'
        f'<div class="page-caption">{caption}</div>',
        unsafe_allow_html=True,
    )


# ==================== FASE 1 — SIDEBAR SECTION ====================
def sidebar_section(titulo):
    """Rótulo de seção na sidebar."""
    st.sidebar.markdown(
        f'<div class="sidebar-section">{titulo}</div>',
        unsafe_allow_html=True,
    )

# ==================== FASE 3 — SIDEBAR GROUP ====================
def sidebar_group(titulo, icone):
    """Rótulo de grupo na sidebar."""
    st.sidebar.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;'
        f'padding:18px 14px 6px 14px;">'
        f'<span style="color:#c9a666;opacity:.8;">{lucide(icone, 12)}</span>'
        f'<span style="font-size:10px;color:#5c6270;letter-spacing:1.4px;'
        f'text-transform:uppercase;font-weight:700;">{titulo}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ==================== FASE 3 — EMPTY STATE ====================
def empty_state(titulo='Nenhum dado encontrado',
                descricao='Tente ajustar os filtros.',
                icone='search', acao_label=None, acao_key=None):
    """
    Estado vazio profissional.

    Uso:
        if df.empty:
            empty_state(
                titulo='Nenhum ticket encontrado',
                descricao='Tente ajustar os filtros.',
                acao_label='Limpar filtros',
                acao_key='limpar_filtros',
            )
    """
    st.markdown(
        f'<div style="display:flex;flex-direction:column;align-items:center;'
        f'justify-content:center;padding:60px 20px;text-align:center;">'
        f'<div style="color:#5c6270;margin-bottom:20px;">'
        f'{lucide(icone, 48, "#5c6270", 1.5)}</div>'
        f'<div style="font-family:Fraunces,serif;font-size:20px;'
        f'font-weight:600;color:#eae7e1;margin-bottom:8px;">{titulo}</div>'
        f'<div style="font-size:13px;color:#9299a6;max-width:400px;">'
        f'{descricao}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if acao_label:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(acao_label, key=acao_key, use_container_width=True):
                st.rerun()


# ==================== FASE 3 — INSIGHT CARD ====================
def insight_card(tipo, titulo, valor, detalhe,
                 acao_label=None, acao_key=None, cor_custom=None):
    """
    Card de insight com ação clicável.

    Args:
        tipo: 'success' | 'warning' | 'danger' | 'info'
        titulo: ex: 'Backlog'
        valor: ex: '32 tickets'
        detalhe: ex: '> 30 dias'
        acao_label: ex: 'Ver tickets'
        acao_key: chave única
    """
    cores = {
        'success': ('#7fc99b', 'check-circle'),
        'warning': ('#d9ac53', 'alert-triangle'),
        'danger':  ('#e0867a', 'alert-circle'),
        'info':    ('#8b96a8', 'info'),
    }
    cor, icone = cores.get(tipo, ('#8b96a8', 'info'))
    if cor_custom:
        cor = cor_custom

    st.markdown(
        f'<div style="background:#1b2029;border:1px solid rgba(255,255,255,.07);'
        f'border-radius:12px;padding:18px 20px;height:100%;'
        f'border-left:3px solid {cor};transition:all .2s ease;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">'
        f'<span style="color:{cor};">{lucide(icone, 16)}</span>'
        f'<span style="font-size:11px;color:#5c6270;letter-spacing:.8px;'
        f'text-transform:uppercase;font-weight:600;">{titulo}</span>'
        f'</div>'
        f'<div style="font-family:Fraunces,serif;font-size:22px;'
        f'font-weight:600;color:#eae7e1;line-height:1.2;margin-bottom:6px;">'
        f'{valor}</div>'
        f'<div style="font-size:12px;color:#9299a6;margin-bottom:10px;">'
        f'{detalhe}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if acao_label:
        if st.button(acao_label, key=acao_key, use_container_width=True):
            return True
    return False


# ==================== FASE 4 — TABELA CUSTOMIZADA ====================
def tabela_customizada(df, colunas, altura_max=500, dentro_de_card=False):
    """
    Tabela customizada com badges e hover.

    Args:
        df: DataFrame
        colunas: lista de dicts (ver doc anterior)
        altura_max: altura máxima em px
        dentro_de_card: se True, remove o `border` e `border-radius`
                        (quando a tabela está dentro de um chart_card)
    """
    if df.empty:
        empty_state()
        return

    # Classe extra se estiver dentro de card
    classe_extra = '' if not dentro_de_card else ' tabela-no-card'

    html = f'<div style="max-height:{altura_max}px;overflow-y:auto;">'
    html += f'<table class="tabela-custom{classe_extra}">'

    # Header
    html += '<thead><tr>'
    for col in colunas:
        align_class = ' class="num"' if col.get('tipo') == 'num' else ''
        html += f'<th{align_class}>{col["label"]}</th>'
    html += '</tr></thead><tbody>'

    # Linhas
    for _, row in df.iterrows():
        html += '<tr>'
        for col in colunas:
            campo = col['campo']
            valor = row.get(campo)
            tipo = col.get('tipo', 'texto')
            css_class = 'num' if tipo == 'num' else ''

            # ---------- FORMATAÇÃO ----------
            if tipo == 'badge' and 'badge_map' in col:
                badge_tipo = col['badge_map'].get(valor, 'neutral')
                conteudo = f'<span class="badge badge-{badge_tipo}">{valor}</span>'

            elif tipo == 'data' and pd.notna(valor):
                try:
                    fmt = col.get('formato', '%d/%m/%Y')
                    conteudo = pd.to_datetime(valor).strftime(fmt)
                except Exception:
                    conteudo = '—'

            elif tipo == 'num':
                try:
                    conteudo = f'{float(valor):,.0f}' if pd.notna(valor) else '—'
                except Exception:
                    conteudo = '—'

            else:
                if pd.notna(valor):
                    v = str(valor)
                    if col.get('truncate'):
                        v = v[:60] + ('…' if len(v) > 60 else '')
                    conteudo = v
                else:
                    conteudo = '—'

            if col.get('truncate'):
                css_class += ' truncate'

            align_class = f' class="{css_class.strip()}"' if css_class.strip() else ''
            html += f'<td{align_class}>{conteudo}</td>'
        html += '</tr>'

    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)


# ==================== FASE 4 — MAPA DE BADGES ====================
# Mapas reutilizáveis para badges
BADGES_PRIORIDADE = {
    'Crítica': 'prio-critica',
    'Alta':    'prio-alta',
    'Média':   'prio-media',
    'Baixa':   'prio-baixa',
    'Baixa-1': 'prio-baixa',
    'Baixa-2': 'prio-baixa',
    'Baixa-3': 'prio-baixa',
}

BADGES_SLA = {
    'cumprido':  'success',
    'estourado': 'danger',
}

BADGES_STATUS = {
    'Fechado':    'neutral',
    'Resolvido':  'success',
    'Em atendimento': 'info',
    'Aguardando confirmação do usuário': 'warning',
    'Aguardando Deploy': 'warning',
    'Em Análise': 'info',
}

def card_com_tabela(titulo, descricao, icone, df, colunas, altura_max=500):
    """
    Renderiza um card com tabela dentro (HTML único).
    
    Resolve o problema do `with chart_card()` que não mantém o contexto HTML.
    """
    if df.empty:
        empty_state()
        return
    
    icone_html = lucide(icone, 16) if icone else ''
    
    # ---------- HEADER DO CARD ----------
    html = (
        f'<div style="margin-bottom:18px;">'
        f'<div style="background:#1b2029;border:1px solid rgba(255,255,255,.07);'
        f'border-radius:12px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.08);">'
        f'<div style="background:#1b2029;border:1px solid rgba(255,255,255,.07);'
        f'border-radius:12px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.08);">'
        # Header
        f'<div style="padding:18px 24px 14px 24px;'
        f'border-bottom:1px solid rgba(255,255,255,.07);">'
        f'<div style="display:flex;align-items:center;gap:8px;'
        f'font-family:Fraunces,serif;font-size:16px;font-weight:500;color:#eae7e1;">'
        f'<span style="color:#c9a666;">{icone_html}</span>'
        f'{titulo}'
        f'</div>'
        f'<div style="font-size:12.5px;color:#5c6270;margin-top:4px;">'
        f'{descricao}</div>'
        f'</div>'
        # Tabela
        f'<div style="max-height:{altura_max}px;overflow-y:auto;">'
        f'<table style="width:100%;border-collapse:collapse;font-size:12.5px;">'
    )
    
    # ---------- HEADER DA TABELA ----------
    html += '<thead><tr>'
    for col in colunas:
        align = 'right' if col.get('tipo') == 'num' else 'left'
        html += (
            f'<th style="padding:11px 14px;text-align:{align};'
            f'font-size:10.5px;color:#5c6270;letter-spacing:.8px;'
            f'text-transform:uppercase;font-weight:600;'
            f'border-bottom:1px solid rgba(255,255,255,.07);'
            f'position:sticky;top:0;background:#1b2029;z-index:1;">'
            f'{col["label"]}</th>'
        )
    html += '</tr></thead><tbody>'
    
    # ---------- LINHAS ----------
    for _, row in df.iterrows():
        html += '<tr style="transition:background .12s ease;">'
        for col in colunas:
            campo = col['campo']
            valor = row.get(campo)
            tipo = col.get('tipo', 'texto')
            align = 'right' if tipo == 'num' else 'left'
            
            # Formatação
            if tipo == 'badge' and 'badge_map' in col:
                badge_tipo = col['badge_map'].get(valor, 'neutral')
                conteudo = f'<span class="badge badge-{badge_tipo}">{valor}</span>'
            elif tipo == 'num':
                try:
                    conteudo = f'{float(valor):,.0f}' if pd.notna(valor) else '—'
                except Exception:
                    conteudo = '—'
            else:
                if pd.notna(valor):
                    v = str(valor)
                    if col.get('truncate'):
                        v = v[:60] + ('…' if len(v) > 60 else '')
                    conteudo = v
                else:
                    conteudo = '—'
            
            html += (
                f'<td style="padding:10px 14px;text-align:{align};'
                f'color:#eae7e1;border-bottom:1px solid rgba(255,255,255,.04);'
                f'{"font-variant-numeric:tabular-nums;" if tipo == "num" else ""}">'
                f'{conteudo}</td>'
            )
        html += '</tr>'

def card_com_barras(titulo, descricao, icone, items, altura_min=0):
    """
    Renderiza um card com barras horizontais dentro (HTML único).
    
    Resolve o problema do `with chart_card()` que não mantém o contexto HTML.
    """
    if not items:
        empty_state()
        return
    
    icone_html = lucide(icone, 16) if icone else ''
    max_val = max(i['value'] for i in items) or 1
    
    # ---------- HEADER DO CARD ----------
    html = (
        f'<div style="background:#1b2029;border:1px solid rgba(255,255,255,.07);'
        f'border-radius:12px;padding:22px 24px;'
        f'box-shadow:0 1px 2px rgba(0,0,0,.08);'
        f'margin-bottom:18px;">'
        # Header
        f'<div style="display:flex;align-items:flex-start;gap:12px;'
        f'margin-bottom:18px;">'
        f'<div>'
        f'<div style="display:flex;align-items:center;gap:8px;'
        f'font-family:Fraunces,serif;font-size:16px;font-weight:500;color:#eae7e1;">'
        f'<span style="color:#c9a666;">{icone_html}</span>'
        f'{titulo}'
        f'</div>'
        f'<div style="font-size:12.5px;color:#5c6270;margin-top:4px;">'
        f'{descricao}</div>'
        f'</div>'
        f'</div>'
        # Barras
        f'<div style="display:flex;flex-direction:column;gap:9px;">'
    )
    
    for it in items:
        pct = max(2, (it['value'] / max_val) * 100)
        accent = it.get('accent', False)
        cor = '#e0867a' if accent else '#8b96a8'
        label = it['label']
        fmt = it.get('formatted', it['value'])
        
        html += (
            f'<div style="display:flex;align-items:center;gap:12px;">'
            f'<div style="flex:0 0 180px;font-size:12.5px;color:#9299a6;'
            f'line-height:1.3;">{label}</div>'
            f'<div style="flex:1;height:27px;background:rgba(255,255,255,.045);'
            f'border-radius:4px;position:relative;overflow:hidden;">'
            f'<div style="height:100%;width:{pct:.1f}%;background:{cor};'
            f'border-radius:4px;"></div>'
            f'<div style="position:absolute;top:0;left:10px;height:100%;'
            f'display:flex;align-items:center;font-size:12px;'
            f'font-weight:600;color:#eae7e1;">{fmt}</div>'
            f'</div>'
            f'</div>'
        )
    
    html += '</tbody></table></div></div></div>'
    st.markdown(html, unsafe_allow_html=True)
    