# ============================================================
# gerar_11_roadmap.py
# ============================================================

import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from scripts.docs._base import gerar_de_template, rodar_sozinho


def gerar(forcar=False):
    return gerar_de_template(
        '11_roadmap.md',
        '11_ROADMAP',
        forcar=forcar
    )


if __name__ == '__main__':
    rodar_sozinho(gerar)