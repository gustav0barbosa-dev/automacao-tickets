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

        /* Fase 4 — paleta semântica */
    --info: #6fa8dc;
    --success-strong: #4ade80;
    --danger-strong: #ef4444;
    --warning-strong: #f59e0b;
    
    /* Fase 4 — sombras */
    --shadow-sm: 0 1px 2px rgba(0,0,0,.08);
    --shadow-md: 0 4px 12px rgba(0,0,0,.12);
    --shadow-lg: 0 8px 24px rgba(0,0,0,.16);
    
    /* Fase 4 — radius */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
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

/* ============================================
   FASE 1 — CHART-CARD (agrupar gráficos)
   ============================================ */
.chart-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 18px;
    transition: border-color .2s ease;
}
.chart-card:hover {
    border-color: rgba(201,166,102,.2);
}
.chart-card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 18px;
}
.chart-card-title {
    font-family: 'Fraunces', serif;
    font-size: 16px;
    font-weight: 500;
    color: var(--text);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.chart-card-desc {
    font-size: 12.5px;
    color: var(--text-ter);
    margin-top: 4px;
}
.chart-card-actions {
    display: flex;
    gap: 8px;
    align-items: center;
}

/* ============================================
   FASE 1 — KPI CARD MELHORADO
   ============================================ */
.kpi-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    min-height: 120px;
    position: relative;
    transition: all .2s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.kpi-card:hover {
    border-color: rgba(201,166,102,.2);
    box-shadow: 0 4px 16px rgba(0,0,0,.15);
    transform: translateY(-1px);
}
.kpi-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}
.kpi-label {
    font-size: 11px;
    color: var(--text-sec);
    letter-spacing: .8px;
    text-transform: uppercase;
    font-weight: 600;
}
.kpi-icon {
    color: var(--text-ter);
    opacity: .7;
}
.kpi-value {
    font-family: 'Fraunces', serif;
    font-size: 28px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.1;
    margin-bottom: 6px;
}
.kpi-trend {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11.5px;
    color: var(--text-sec);
}
.kpi-trend-value {
    font-weight: 600;
}
.kpi-trend-value.positive { color: var(--success); }
.kpi-trend-value.negative { color: var(--danger); }

/* ============================================
   FASE 1 — HEADER GLOBAL
   ============================================ */
.global-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 4px 16px 4px;
    margin-bottom: 12px;
    border-bottom: 1px solid var(--border);
}
.global-header-left {
    display: flex;
    align-items: center;
    gap: 12px;
}
.global-header-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    letter-spacing: .3px;
}
.global-header-right {
    display: flex;
    align-items: center;
    gap: 14px;
}
.global-header-user {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-radius: 8px;
    background: rgba(255,255,255,.03);
    font-size: 12.5px;
    color: var(--text-sec);
}
.global-header-icon {
    color: var(--text-ter);
    cursor: pointer;
    transition: color .15s ease;
}
.global-header-icon:hover {
    color: var(--gold);
}

/* ============================================
   FASE 1 — SIDEBAR AGRUPADA
   ============================================ */
.sidebar-section {
    font-size: 10.5px;
    color: var(--text-ter);
    letter-spacing: 1.2px;
    text-transform: uppercase;
    font-weight: 600;
    padding: 18px 14px 8px 14px;
    margin: 0;
}

/* Botões de navegação da sidebar */
section[data-testid="stSidebar"] button[kind="secondary"] {
    background: transparent !important;
    border: none !important;
    color: #9299a6 !important;
    font-size: 13px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 8px 14px !important;
    border-radius: 6px !important;
}

section[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,.03) !important;
    color: #eae7e1 !important;
}

section[data-testid="stSidebar"] button[kind="primary"] {
    background: rgba(201,166,102,.12) !important;
    border: none !important;
    border-left: 3px solid #c9a666 !important;
    color: #eae7e1 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 8px 14px !important;
    border-radius: 6px !important;
}

/* Botões de navegação mais discretos */
section[data-testid="stSidebar"] button[kind="secondary"] p,
section[data-testid="stSidebar"] button[kind="primary"] p {
    font-size: 13px !important;
    text-align: left !important;
    width: 100% !important;
}

section[data-testid="stSidebar"] button[kind="secondary"],
section[data-testid="stSidebar"] button[kind="primary"] {
    justify-content: flex-start !important;
    padding: 8px 14px !important;
}

section[data-testid="stSidebar"] button[kind="secondary"] p {
    color: #9299a6 !important;
}

section[data-testid="stSidebar"] button[kind="primary"] p {
    color: #eae7e1 !important;
    font-weight: 600 !important;
}

/* ============================================
   FASE 3 — BOTÕES DE NAVEGAÇÃO (sidebar)
   ============================================ */
section[data-testid="stSidebar"] button[kind="secondary"],
section[data-testid="stSidebar"] button[kind="primary"] {
    display: flex !important;
    justify-content: flex-start !important;
    align-items: center !important;
    text-align: left !important;
    padding: 10px 16px !important;
    margin: 2px 0 !important;
    border: none !important;
    border-radius: 6px !important;
    background: transparent !important;
    box-shadow: none !important;
    width: 100% !important;
    transition: background .15s ease, color .15s ease !important;
}

/* Força o conteúdo interno a alinhar à esquerda */
section[data-testid="stSidebar"] button[kind="secondary"] > div,
section[data-testid="stSidebar"] button[kind="primary"] > div {
    display: flex !important;
    justify-content: flex-start !important;
    align-items: center !important;
    width: 100% !important;
    text-align: left !important;
}

/* Texto dos botões */
section[data-testid="stSidebar"] button[kind="secondary"] p,
section[data-testid="stSidebar"] button[kind="primary"] p {
    font-size: 13.5px !important;
    text-align: left !important;
    width: 100% !important;
    margin: 0 !important;
}

/* Estado normal (inativo) */
section[data-testid="stSidebar"] button[kind="secondary"] p {
    color: #9299a6 !important;
    font-weight: 400 !important;
}

/* Hover (inativo) */
section[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,.03) !important;
}
section[data-testid="stSidebar"] button[kind="secondary"]:hover p {
    color: #eae7e1 !important;
}

/* Ativo (primary) */
section[data-testid="stSidebar"] button[kind="primary"] {
    background: rgba(201,166,102,.08) !important;
    border-left: 3px solid #c9a666 !important;
    border-radius: 6px 0 0 6px !important;
}
section[data-testid="stSidebar"] button[kind="primary"] p {
    color: #eae7e1 !important;
    font-weight: 600 !important;
}

/* ============================================
   FASE 4 — BADGES SEMÂNTICOS
   ============================================ */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: var(--radius-sm);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .3px;
    white-space: nowrap;
}
.badge-success { background: rgba(127,201,155,.12); color: var(--success); }
.badge-danger  { background: rgba(224,134,122,.12); color: var(--danger); }
.badge-warning { background: rgba(217,172,83,.12);  color: var(--warning); }
.badge-info    { background: rgba(111,168,220,.12); color: var(--info); }
.badge-neutral { background: rgba(255,255,255,.05); color: var(--text-sec); }

/* Badges de prioridade */
.badge-prio-critica { background: rgba(239,68,68,.15); color: #ef4444; }
.badge-prio-alta    { background: rgba(249,115,22,.15); color: #f97316; }
.badge-prio-media   { background: rgba(217,172,83,.15); color: #d9ac53; }
.badge-prio-baixa   { background: rgba(111,168,220,.15); color: #6fa8dc; }

/* ============================================
   FASE 4 — TABELA CUSTOMIZADA
   ============================================ */
.tabela-custom {
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
    background: var(--card);
    border-radius: var(--radius-md);
    overflow: hidden;
    border: 1px solid var(--border);
}
.tabela-custom thead {
    background: rgba(255,255,255,.02);
    position: sticky;
    top: 0;
    z-index: 1;
}
.tabela-custom th {
    padding: 11px 14px;
    text-align: left;
    font-size: 10.5px;
    color: var(--text-ter);
    letter-spacing: .8px;
    text-transform: uppercase;
    font-weight: 600;
    border-bottom: 1px solid var(--border);
}
.tabela-custom td {
    padding: 10px 14px;
    color: var(--text);
    border-bottom: 1px solid rgba(255,255,255,.04);
}
.tabela-custom tbody tr {
    transition: background .12s ease;
}
.tabela-custom tbody tr:hover {
    background: rgba(201,166,102,.04);
}
.tabela-custom tbody tr:last-child td {
    border-bottom: none;
}
.tabela-custom .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}
.tabela-custom .truncate {
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* ============================================
   FASE 4 — SOMBRAS EM CARDS
   ============================================ */
.kpi-card,
.chart-card {
    box-shadow: var(--shadow-sm);
}
.kpi-card:hover,
.chart-card:hover {
    box-shadow: var(--shadow-md);
}

/* ============================================
   AJUSTE 1 — CHART-CARD COM TABELA (compacto)
   ============================================ */
.chart-card.compact {
    padding: 0;
}
.chart-card.compact .chart-card-header {
    padding: 18px 24px 14px 24px;
    margin-bottom: 0;
    border-bottom: 1px solid var(--border);
}
.chart-card.compact .tabela-custom {
    border: none;
    border-radius: 0;
    max-height: 500px;
    overflow-y: auto;
}

/* ============================================
   AJUSTE 2 — ALINHAMENTO DA TABELA
   ============================================ */
.tabela-custom th,
.tabela-custom td {
    text-align: left;
}
.tabela-custom th.num,
.tabela-custom td.num {
    text-align: right !important;
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum";
    padding-right: 18px;
}

/* ============================================
   AJUSTE 3 — SEM TÍTULO DUPLICADO
   ============================================ */
/* Se a tabela for filha direta de um chart-card, remove a borda própria */
.chart-card > .tabela-custom {
    border: none;
    border-radius: 0;
}

</style>
"""


def aplicar_tema():
    """Injeta o CSS global. Chame uma vez em app.py."""
    st.markdown(CSS, unsafe_allow_html=True)