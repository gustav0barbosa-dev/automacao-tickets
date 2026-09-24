# ============================================================
# dashboard/app.py — Ponto de entrada
# ============================================================
"""
Dashboard da Automação Help360.

Uso:
    streamlit run dashboard/app.py
"""
import unicodedata
import sys
from pathlib import Path

# Adiciona a pasta dashboard/ ao sys.path para permitir imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from auth import tela_login, logout, usuario_atual

# ⬇️ BLOQUEIA O DASHBOARD ATÉ AUTENTICAR
if not tela_login():
    st.stop()

from config import MENU_PAGINAS
from theme import aplicar_tema
from data import carregar_tickets
from filters import aplicar_filtros


# ==================== CONFIG ====================
st.set_page_config(
    page_title='Help360 · Painel de Análise',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

# Força a sidebar a abrir se estiver fechada (via URL param)
if 'sidebar' not in st.session_state:
    st.session_state.sidebar = True

aplicar_tema()


# ==================== CSS CUSTOMIZADO ====================
st.markdown(
    """
    <style>
    /* Botão de logout dourado */
    section[data-testid="stSidebar"] .st-key-btn_logout button {
        background: linear-gradient(135deg, #c9a666 0%, #8a7340 100%) !important;
        color: #1a1a1a !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        transition: all 0.2s ease !important;
    }

    section[data-testid="stSidebar"] .st-key-btn_logout button:hover {
        background: linear-gradient(135deg, #d9b676 0%, #9a8350 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(201, 166, 102, 0.3);
    }

    /* Bloco do usuário no rodapé */
    .user-footer {
        padding: 12px 6px 8px 6px;
        border-top: 1px solid rgba(255, 255, 255, .07);
        margin-top: 24px;
    }

    .user-label {
        font-size: 10.5px;
        color: #5c6270;
        text-transform: uppercase;
        letter-spacing: .5px;
        margin-bottom: 4px;
    }

    .user-name {
        font-size: 13px;
        color: #c9a666;
        font-weight: 600;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================== ROTEAMENTO DE PÁGINAS ====================
def slugify(nome):
    """
    Converte 'Tempo de Resposta' → 'tempo_resposta'
    e 'Reincidência' → 'reincidencia'.
    Remove acentos e palavras conectoras (de, da, do, das, dos, e).
    """
    # Remove acentos
    nfkd = unicodedata.normalize('NFKD', nome)
    sem_acento = ''.join(c for c in nfkd if not unicodedata.combining(c))

    # Minúsculas e limpeza
    slug = sem_acento.lower().strip()

    # Remove palavras conectoras
    stopwords = {'de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o'}
    palavras = [p for p in slug.split() if p not in stopwords]

    return '_'.join(palavras)


def carregar_pagina(nome_pagina):
    """Carrega dinamicamente o módulo da página."""
    slug = slugify(nome_pagina)
    modulo = __import__(f'views.{slug}', fromlist=['render'])
    return modulo


def main():
    # ==================== SIDEBAR BRANDING ====================
    st.sidebar.markdown(
        '<div style="padding:4px 6px 24px 6px;">'
        '  <div style="font-family:Fraunces,serif;font-size:22px;'
        '              font-weight:600;color:#eae7e1;letter-spacing:.3px;">'
        '    HELP360'
        '  </div>'
        '  <div style="font-size:11.5px;color:#5c6270;margin-top:4px;">'
        '    Dashboard de Análise'
        '  </div>'
        '</div>'
        '<hr style="border:none;border-top:1px solid rgba(255,255,255,.07);'
        '           margin:0 0 18px 0;">',
        unsafe_allow_html=True,
    )

    # ==================== CARREGA DADOS ====================
    df = carregar_tickets()

    if df is None or df.empty:
        st.error('❌ Banco de dados não encontrado ou vazio.')
        st.info('Execute primeiro:\n\n```\npython src/programa4_persistir.py\n```')
        return

    # ==================== NAVEGAÇÃO ====================
    pagina = st.sidebar.radio(
        'Navegação',
        options=MENU_PAGINAS,
        label_visibility='collapsed',
    )

    st.sidebar.markdown(
        '<hr style="border:none;border-top:1px solid rgba(255,255,255,.07);'
        '           margin:18px 0;">',
        unsafe_allow_html=True,
    )

    # ==================== FILTROS ====================
    df_filtrado = aplicar_filtros(df)

    # ==================== RENDERIZA PÁGINA ====================
    try:
        modulo = carregar_pagina(pagina)
        modulo.render(df_filtrado)
    except ImportError as e:
        st.error(f'❌ Página "{pagina}" não implementada: {e}')
        st.info('Crie o arquivo em `dashboard/pages/`.')

    # ==================== RODAPÉ: USUÁRIO + LOGOUT ====================
    st.sidebar.markdown(
        '<div class="user-footer">'
        '  <div class="user-label">Conectado como</div>'
        f'  <div class="user-name">👤 {usuario_atual()}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.sidebar.button('🚪  Sair', use_container_width=True, key='btn_logout'):
        logout()



if __name__ == '__main__':
    main()