# ============================================================
# _base.py - Funções compartilhadas pelos geradores de docs
# ============================================================
"""
Módulo com funções utilitárias usadas por todos os geradores
de documentos em scripts/docs/.

Os conteúdos ficam em scripts/docs/templates/*.md (markdown puro)
e os scripts gerar_XX.py apenas copiam para docs/.
"""

import os
import shutil
from datetime import datetime


# Caminhos
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_DOCS = os.path.join(_RAIZ, 'docs')
PASTA_TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')


def garantir_pastas():
    """Cria as pastas necessárias se não existirem."""
    os.makedirs(PASTA_DOCS, exist_ok=True)
    os.makedirs(PASTA_TEMPLATES, exist_ok=True)


def gerar_de_template(nome_template, nome_saida, forcar=False):
    """
    Copia um arquivo de templates/ para docs/.

    Args:
        nome_template: nome do arquivo em templates/ (ex: '04_modelo_dados.md')
        nome_saida: nome do arquivo em docs/ (ex: '04_MODELO_DADOS')
        forcar: se True, sobrescreve

    Returns:
        True se escreveu, False se pulou
    """
    garantir_pastas()

    caminho_template = os.path.join(PASTA_TEMPLATES, nome_template)
    caminho_saida = os.path.join(PASTA_DOCS, f'{nome_saida}.md')

    if not os.path.exists(caminho_template):
        print(f'❌ Template não encontrado: {caminho_template}')
        return False

    if os.path.exists(caminho_saida) and not forcar:
        print(f'⏭️  {nome_saida}.md já existe (use --forcar para sobrescrever)')
        return False

    # Adiciona rodapé com data de geração
    with open(caminho_template, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    with open(caminho_saida, 'w', encoding='utf-8') as f:
        f.write(conteudo)

    tamanho_kb = os.path.getsize(caminho_saida) / 1024
    print(f'✅ {nome_saida}.md ({tamanho_kb:.1f} KB)')
    return True


def rodar_sozinho(gerar_func):
    """Helper para rodar um gerador individualmente."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--forcar', action='store_true',
                        help='Sobrescreve arquivo existente')
    args = parser.parse_args()

    print('=' * 60)
    print(f'GERADOR DE DOC — {gerar_func.__name__}')
    print('=' * 60)
    print(f'📁 Saída: {PASTA_DOCS}')
    print(f'📁 Templates: {PASTA_TEMPLATES}')
    print(f'⚙️  Modo: {"SOBRESCREVER" if args.forcar else "PRESERVAR"}')
    print()

    gerar_func(forcar=args.forcar)