# ============================================================
# dashboard/components.py — Componentes visuais reutilizáveis
# ============================================================
"""
Componentes visuais usados em todas as páginas.
Se precisar mudar aparência, edite aqui.
"""

import streamlit as st
import plotly.graph_objects as go

from config import (
    COR_GOLD, COR_BAR, COR_DANGER, COR_TEXT,
    COR_TEXT_SEC, COR_TEXT_TER, COR_GRID,
)


# ==================== COMPONENTES HTML ====================
def kpi(label, valor, pill=None, pill_tipo='neutral', ajuda=None):
    """Renderiza um KPI card (HTML em linha única)."""
    pill_html = f'<span class="kpi-pill {pill_tipo}">{pill}</span>' if pill else ''
    help_html = f'<div class="kpi-help">{ajuda}</div>' if ajuda else ''

    html = (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value-row">'
        f'<span class="kpi-value">{valor}</span>'
        f'{pill_html}'
        f'</div>'
        f'{help_html}'
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