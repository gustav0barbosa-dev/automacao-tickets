# ============================================================
# gerar_06_analises.py
# ============================================================

import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from scripts.docs._base import gerar_de_template, rodar_sozinho


def gerar(forcar=False):
    return gerar_de_template(
        '06_analises.md',
        '06_ANALISES_E_METRICAS',
        forcar=forcar
    )


if __name__ == '__main__':
    rodar_sozinho(gerar)