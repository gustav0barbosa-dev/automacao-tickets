# ============================================================
# _base.py - Funções compartilhadas pelos geradores de docs
# ============================================================
"""
Módulo com funções utilitárias usadas por todos os geradores
de documentos em scripts/docs/.
"""

import os
from datetime import datetime


# Caminhos
PASTA_DOCS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'docs'
)


def garantir_pasta():
    """Cria a pasta docs/ se não existir."""
    os.makedirs(PASTA_DOCS, exist_ok=True)
    return PASTA_DOCS


def escrever(nome_arquivo, conteudo, forcar=False):
    """
    Escreve um arquivo .md em docs/.

    Args:
        nome_arquivo: nome sem extensão (ex: '04_MODELO_DADOS')
        conteudo: string markdown
        forcar: se True, sobrescreve

    Returns:
        True se escreveu, False se pulou
    """
    garantir_pasta()
    caminho = os.path.join(PASTA_DOCS, f'{nome_arquivo}.md')

    if os.path.exists(caminho) and not forcar:
        print(f'⏭️  {nome_arquivo}.md já existe (use forcar=True)')
        return False

    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)

    tamanho_kb = os.path.getsize(caminho) / 1024
    print(f'✅ {nome_arquivo}.md ({tamanho_kb:.1f} KB)')
    return True


def rodar_sozinho(gerar_func):
    """
    Helper para rodar um gerador individualmente via linha de comando.
    Uso no final de cada script:

        if __name__ == '__main__':
            rodar_sozinho(gerar)
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--forcar', action='store_true',
                        help='Sobrescreve arquivo existente')
    args = parser.parse_args()

    print('=' * 60)
    print(f'GERADOR DE DOC — {gerar_func.__name__}')
    print('=' * 60)
    print(f'📁 Saída: {PASTA_DOCS}')
    print(f'⚙️  Modo: {"SOBRESCREVER" if args.forcar else "PRESERVAR"}')
    print()

    gerar_func(forcar=args.forcar)