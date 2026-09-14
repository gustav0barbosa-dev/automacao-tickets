#!/usr/bin/env python
# coding: utf-8
# ============================================================
# gerar_docs.py - Orquestrador dos geradores de documentação
# ============================================================
"""
Roda todos os geradores em scripts/docs/ em sequência.

Uso:
    python scripts/gerar_docs.py                  # preserva existentes
    python scripts/gerar_docs.py --forcar         # sobrescreve tudo
    python scripts/gerar_docs.py --doc 04         # só o doc 04
    python scripts/gerar_docs.py --listar         # lista disponíveis
"""

import argparse
import importlib
import os
import sys

# Adiciona a raiz do projeto ao sys.path para importar 'scripts.docs.*'
RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ_PROJETO)

from scripts.docs import GERADORES
from scripts.docs._base import PASTA_DOCS


def rodar_gerador(nome_modulo, forcar=False):
    """Importa e roda um gerador específico."""
    try:
        modulo = importlib.import_module(f'scripts.docs.{nome_modulo}')
        return modulo.gerar(forcar=forcar)
    except Exception as e:
        print(f'❌ Erro em {nome_modulo}: {e}')
        return False


def listar_disponiveis():
    print('\n📚 Geradores disponíveis:')
    for nome in GERADORES:
        print(f'   - {nome}')


def main():
    parser = argparse.ArgumentParser(description='Gera a documentação técnica.')
    parser.add_argument('--forcar', action='store_true',
                        help='Sobrescreve arquivos existentes.')
    parser.add_argument('--doc', type=str, default=None,
                        help='Gera apenas o doc com prefixo (ex: 04).')
    parser.add_argument('--listar', action='store_true',
                        help='Lista os geradores disponíveis.')
    args = parser.parse_args()

    if args.listar:
        listar_disponiveis()
        return

    print('=' * 60)
    print('GERADOR DE DOCUMENTAÇÃO — AUTOMAÇÃO HELP360')
    print('=' * 60)
    print(f'📁 Pasta de saída: {PASTA_DOCS}')
    print(f'⚙️  Modo: {"SOBRESCREVER" if args.forcar else "PRESERVAR existentes"}')
    print()

    if args.doc:
        alvo = next((n for n in GERADORES if n.startswith(f'gerar_{args.doc}')), None)
        if not alvo:
            print(f'❌ Nenhum gerador com prefixo "{args.doc}".')
            listar_disponiveis()
            return
        rodar_gerador(alvo, forcar=args.forcar)
        return

    # Roda todos
    total = 0
    for nome in GERADORES:
        if rodar_gerador(nome, forcar=args.forcar):
            total += 1

    print()
    print('=' * 60)
    print(f'✅ {total} arquivo(s) gerado(s) em: {PASTA_DOCS}')
    print('=' * 60)

    if total > 0:
        print('\n💡 Para commitar:')
        print('   git add docs/')
        print('   git commit -m "Atualiza documentacao tecnica"')
        print('   git push')


if __name__ == '__main__':
    main()