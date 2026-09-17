# ============================================================
# dashboard/theme.py — CSS global e configuração visual
# ============================================================
"""
Todo o CSS do dashboard. Se precisar mudar aparência,
edite aqui — não espalhe CSS pelas páginas.
"""

import streamlit as st


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap');

:root{
    --bg-main:#141821;
    --card:#1b2029;
    --border:rgba(255,255,255,.07);
    --text:#eae7e1;
    --text-sec:#9299a6;
    --text-ter:#5c6270;
    --bar:#8b96a8;
    --bar-track:rgba(255,255,255,.045);
    --gold:#c9a666;
    --success:#7fc99b;
    --danger:#e0867a;
    --warning:#d9ac53;
}

/* ============================================
   BASE
   ============================================ */
html, body, [class*="css"] {
    font-family:'Inter',-apple-system,sans-serif !important;
    color:var(--text);
}

.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background:var(--bg-main) !important;
}

[data-testid="stSidebar"] {
    background:#0c0e13 !important;
    border-right:1px solid var(--border);
}

/* ============================================
   TIPOGRAFIA
   ============================================ */
h1 {
    font-family:'Fraunces',serif !important;
    font-weight:300 !important;
    font-size:28px !important;
    letter-spacing:.3px;
    text-transform:uppercase;
    color:var(--text) !important;
}
h1 b { font-weight:600 !important; }

h2, h3 {
    font-family:'Fraunces',serif !important;
    font-weight:500 !important;
    color:var(--text) !important;
}

/* ============================================
   LIMPEZA DO CHROME DO STREAMLIT
   ============================================ */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* NÃO esconder a toolbar inteira — pode conter o botão da sidebar */
[data-testid="stToolbar"] {
    background: transparent !important;
}

[data-testid="stDecoration"] { display: none; }
[data-testid="stStatusWidget"] { display: none; }

/* ============================================
   SIDEBAR — CONTROLE DE ABRIR/FECHAR
   Estratégia:
     1. Esconde o botão de FECHAR (sidebar fica permanente)
     2. Deixa o botão de REABRIR visível como fallback
   ============================================ */

/* 1. botão de FECHAR a sidebar */
[data-testid="stSidebar"] {
    background: #0c0e13 !important;
    border-right: 1px solid var(--border);
}

/* 2. Botão de REABRIR — só aparece quando a sidebar está fechada */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 2147483647 !important;
    position: fixed !important;
    top: 12px !important;
    left: 12px !important;
    background: #1b2029 !important;
    border: 1px solid #c9a666 !important;
    border-radius: 8px !important;
    padding: 8px !important;
    width: 42px !important;
    height: 42px !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.4) !important;
}

[data-testid="stSidebarCollapsedControl"]:hover,
[data-testid="collapsedControl"]:hover {
    background: #20262f !important;
    border-color: #c9a666 !important;
}

[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] svg {
    fill: #c9a666 !important;
    color: #c9a666 !important;
    width: 22px !important;
    height: 22px !important;
}

/* ============================================
   LAYOUT PRINCIPAL
   ============================================ */
.block-container {
    padding-top:2rem !important;
    padding-bottom:3rem !important;
    max-width:1400px;
}

/* ============================================
   NAVEGAÇÃO (radio vertical na sidebar)
   ============================================ */
[data-testid="stSidebar"] [role="radiogroup"] > label {
    padding:10px 14px !important;
    border-radius:6px;
    border-left:3px solid transparent;
    font-size:13.5px;
    color:var(--text-sec) !important;
    cursor:pointer;
    margin-bottom:2px;
    background:transparent;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background:rgba(255,255,255,.03);
    color:var(--text) !important;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background:rgba(255,255,255,.05);
    border-left-color:var(--gold);
    color:var(--text) !important;
    font-weight:600;
}
[data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {
    display:none;
}
[data-testid="stSidebar"] [role="radiogroup"] > label p {
    color:inherit !important;
    font-size:13.5px !important;
}

/* ============================================
   COMPONENTES — KPI CARD
   ============================================ */
.kpi-card {
    background:var(--card);
    border:1px solid var(--border);
    border-radius:10px;
    padding:18px;
    min-height:112px;
}
.kpi-label {
    font-size:11.5px; color:var(--text-sec);
    letter-spacing:.2px; margin-bottom:10px;
}
.kpi-value-row {
    display:flex; align-items:baseline;
    gap:9px; flex-wrap:wrap;
}
.kpi-value {
    font-family:'Fraunces',serif; font-size:26px;
    font-weight:600; color:var(--text); line-height:1;
}
.kpi-pill {
    font-size:11px; font-weight:600;
    padding:2px 8px; border-radius:5px; white-space:nowrap;
}
.kpi-pill.positive { background:rgba(127,201,155,.1); color:var(--success); }
.kpi-pill.negative { background:rgba(224,134,122,.1); color:var(--danger); }
.kpi-pill.neutral  { background:rgba(255,255,255,.05); color:var(--text-sec); }
.kpi-help {
    font-size:11px; color:var(--text-ter); margin-top:7px;
}

/* ============================================
   COMPONENTES — HBAR LIST (barras horizontais)
   ============================================ */
.hbar-list { display:flex; flex-direction:column; gap:9px; }
.hbar-row { display:flex; align-items:center; gap:12px; }
.hbar-label {
    flex:0 0 148px; font-size:12.5px;
    color:var(--text-sec); line-height:1.3;
}
.hbar-track {
    flex:1; height:27px; background:var(--bar-track);
    border-radius:4px; position:relative; overflow:hidden;
}
.hbar-fill {
    height:100%; background:var(--bar); border-radius:4px;
}
.hbar-fill.accent { background:var(--danger); }
.hbar-value {
    position:absolute; top:0; left:10px; height:100%;
    display:flex; align-items:center; font-size:12px;
    font-weight:600; color:var(--text);
}

/* ============================================
   COMPONENTES — CALLOUT
   ============================================ */
.callout {
    background:var(--card);
    border:1px solid var(--border);
    border-left:3px solid var(--text-ter);
    padding:12px 16px; border-radius:6px;
    font-size:13px; line-height:1.55;
    margin:8px 0; color:var(--text-sec);
}
.callout b { color:var(--text); }
.callout .tag {
    display:inline-block; font-size:10.5px; font-weight:700;
    letter-spacing:.5px; text-transform:uppercase; margin-right:8px;
}
.callout.info    { border-left-color:var(--text-sec); }
.callout.info .tag { color:var(--text-sec); }
.callout.warning { border-left-color:var(--warning); }
.callout.warning .tag { color:var(--warning); }
.callout.success { border-left-color:var(--success); }
.callout.success .tag { color:var(--success); }

/* ============================================
   COMPONENTES — PANEL TITLE / SEPARADOR / CAPTION
   ============================================ */
.panel-title {
    font-size:15px;
    color:var(--text-sec);
    margin-bottom:18px;
    font-weight:400;
}
.panel-title b { color:var(--text); font-weight:600; }

.sep {
    border:none; border-top:1px solid var(--border); margin:26px 0;
}

.page-caption {
    font-size:13.5px; color:var(--text-sec);
    margin:-4px 0 26px 0;
}

/* ============================================
   FILTROS — contador
   ============================================ */
.filtered-count {
    padding:16px 4px 4px 4px;
    border-top:1px solid var(--border);
    margin-top:16px;
}
.filtered-count .num {
    font-family:'Fraunces',serif; font-size:26px;
    font-weight:600; color:var(--text);
}
.filtered-count .lbl {
    font-size:11px; color:var(--text-ter); letter-spacing:.3px;
}
</style>
"""


def aplicar_tema():
    """Injeta o CSS global. Chame uma vez em app.py."""
    st.markdown(CSS, unsafe_allow_html=True)