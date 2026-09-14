# ============================================================
# gerar_05_regras_negocio.py
# ============================================================

import os
import sys

# Adiciona a raiz do projeto ao sys.path (funciona de qualquer pasta)
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from scripts.docs._base import gerar_de_template, rodar_sozinho


def gerar(forcar=False):
    return gerar_de_template(
        '05_regras_negocio.md',
        '05_REGRAS_DE_NEGOCIO',
        forcar=forcar
    )


if __name__ == '__main__':
    rodar_sozinho(gerar)