# ============================================================
# gerar_04_modelo_dados.py
# ============================================================

from scripts.docs._base import escrever, rodar_sozinho


CONTEUDO = """# 04 — Modelo de Dados

> ⚠️ **Documento em construção.**
> Será preenchido com o schema SQLite completo na Fase 1 do roadmap.

---

**Versão:** 2.0
**Público-alvo:** Desenvolvedores, DBAs

(conteúdo a ser preenchido)
"""


def gerar(forcar=False):
    return escrever('04_MODELO_DADOS', CONTEUDO, forcar=forcar)


if __name__ == '__main__':
    rodar_sozinho(gerar)