# ============================================================
# dashboard/config.py — Constantes e configuração
# ============================================================
"""
Configuração central: paths, cores, paleta, parâmetros.
Alterar aqui = altera em todo o dashboard.
"""

from pathlib import Path

# ==================== PATHS ====================
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = RAIZ_PROJETO / 'dados' / 'tickets.db'

# ==================== PALETA DE CORES ====================
COR_GOLD = '#c9a666'
COR_BAR = '#8b96a8'
COR_SUCCESS = '#7fc99b'
COR_DANGER = '#e0867a'
COR_WARNING = '#d9ac53'
COR_TEXT = '#eae7e1'
COR_TEXT_SEC = '#9299a6'
COR_TEXT_TER = '#5c6270'
COR_GRID = 'rgba(255,255,255,.05)'

# ==================== MENU DE NAVEGAÇÃO ====================
# Adicionar nova página aqui é o único passo necessário
# (a função `render` da página precisa existir em pages/)
MENU_PAGINAS = [
    'Visão Geral',
    'Tempo de Resposta',
    'SLA',
    'Produtividade',
    'Backlog',
    'Roteamento',
    'Reincidência',
]

# ==================== STATUS PADRÃO ====================
STATUS_FECHADOS = ['Resolvido', 'Fechado', 'Cancelado', 'Duplicado']