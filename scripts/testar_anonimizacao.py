"""
Testa a anonimização com dados reais do banco.
"""
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))

from utils_anonimizacao import anonimizar_texto, contar_dados_pessoais

BANCO = RAIZ / 'dados' / 'tickets.db'


def main():
    conn = sqlite3.connect(BANCO)
    conn.row_factory = sqlite3.Row

    # Pega 10 exemplos de titulo e conteudo
    print('=' * 80)
    print('EXEMPLOS DE ANONIMIZAÇÃO — TICKETS.TITULO')
    print('=' * 80)

    cur = conn.execute('''
        SELECT id, titulo FROM tickets
        WHERE titulo LIKE '%CPF%'
           OR titulo LIKE '%Ação Judicial%'
           OR titulo LIKE '%Reativação%'
        LIMIT 5
    ''')

    for row in cur:
        original = row['titulo']
        anonimizado = anonimizar_texto(original)
        print(f'\nID {row["id"]}:')
        print(f'  ANTES: {original[:100]}')
        print(f'  DEPOIS: {anonimizado[:100]}')
        print(f'  Detectado: {contar_dados_pessoais(original)}')

    print('\n' + '=' * 80)
    print('EXEMPLOS DE ANONIMIZAÇÃO — MENSAGENS.CONTEUDO')
    print('=' * 80)

    cur = conn.execute('''
        SELECT id, conteudo FROM mensagens
        WHERE conteudo IS NOT NULL
        LIMIT 5
    ''')

    for row in cur:
        original = row['conteudo']
        anonimizado = anonimizar_texto(original)
        print(f'\nID {row["id"]}:')
        print(f'  ANTES: {original[:150]}')
        print(f'  DEPOIS: {anonimizado[:150]}')
        print(f'  Detectado: {contar_dados_pessoais(original)}')

    conn.close()


if __name__ == '__main__':
    main()