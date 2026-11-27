# ============================================================
# dashboard/config.py — Constantes e configuração
# ============================================================

from pathlib import Path

# ==================== PATHS ====================
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = RAIZ_PROJETO / 'dados' / 'tickets.db'

# ==================== PALETA ====================
COR_GOLD = '#c9a666'
COR_BAR = '#8b96a8'
COR_SUCCESS = '#7fc99b'
COR_DANGER = '#e0867a'
COR_WARNING = '#d9ac53'
COR_TEXT = '#eae7e1'
COR_TEXT_SEC = '#9299a6'
COR_TEXT_TER = '#5c6270'
COR_GRID = 'rgba(255,255,255,.05)'
COR_INFO = '#6fa8dc'

# ==================== MENU ====================
MENU_PAGINAS = [
    'SLA + Reincidência',   # Etapa 2 — Pessoa A
    'Produtividade + Roteamento',  # Etapa 3 — Pessoa A
    'Validação de Motivos',  # Fase 3 — Etapa 2
    'Monitoramento',         # Fase 3 — Etapa 5
    'Inteligência de Tickets',  # Fase 4 — Nova área de inteligência operacional
]

# ==================== STATUS ====================
STATUS_FECHADOS = ['Resolvido', 'Fechado', 'Cancelado', 'Duplicado']

# ==================== OUTLIERS ====================
# Limite para considerar outlier em análises de tempo
# Tickets com mais dias que isso são excluídos de médias
LIMITE_OUTLIER_DIAS = 365

# Mínimo de dias em aberto para considerar "fantasma"
LIMITE_FANTASMA_DIAS = 365

# ==================== MENU AGRUPADO ====================
MENU_GRUPOS = [
    {
        'titulo': 'ANÁLISE',
        'icone': 'chart-line',
        'paginas': [
            'Visão Geral',
            'SLA + Reincidência',
            'Produtividade + Roteamento',
        ],
    },
    {
        'titulo': 'OPERAÇÃO',
        'icone': 'inbox',
        'paginas': [
            'Validação de Motivos',
            'Monitoramento',
        ],
    },
    {
        'titulo': 'INTELIGÊNCIA',
        'icone': 'brain',
        'paginas': [
            'Inteligência de Tickets',
        ],
    },
]