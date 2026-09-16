# ============================================================
# consultas_roteamento.py
# ============================================================
"""
Consultas de análise de ROTEAMENTO e GARGALOS.

Uso:
    python scripts/consultas_roteamento.py               # todas
    python scripts/consultas_roteamento.py --consulta 3
"""

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'


def conectar():
    if not BANCO.exists():
        print(f'❌ Banco não encontrado: {BANCO}')
        sys.exit(1)
    return sqlite3.connect(BANCO)


def titulo(t):
    print()
    print('=' * 78)
    print(f'  {t}')
    print('=' * 78)


def mostrar(df, limite=None):
    if limite:
        df = df.head(limite)
    if df.empty:
        print('  (sem dados)')
        return
    with pd.option_context('display.max_columns', None,
                            'display.width', 200,
                            'display.max_colwidth', 50):
        print(df.to_string(index=False))


# ============================================================
# CONSULTAS
# ============================================================

def c1_pulos_por_ticket(conn):
    """Quantos 'pulos' (trocas de autor) cada ticket teve."""
    titulo('1. PULOS POR TICKET')
    df = pd.read_sql('''
        WITH sequencia AS (
            SELECT
                ticket_id,
                autor,
                data_movimentacao,
                LAG(autor) OVER (PARTITION BY ticket_id ORDER BY data_movimentacao) AS autor_anterior
            FROM movimentacoes
            WHERE autor IS NOT NULL
              AND data_movimentacao IS NOT NULL
        )
        SELECT
            ticket_id,
            COUNT(DISTINCT autor) AS pessoas_envolvidas,
            SUM(CASE WHEN autor != autor_anterior AND autor_anterior IS NOT NULL
                     THEN 1 ELSE 0 END) AS pulos
        FROM sequencia
        GROUP BY ticket_id
        ORDER BY pulos DESC, ticket_id
    ''', conn)

    mostrar(df, limite=20)


def c2_ranking_encaminhadores(conn):
    """Quem mais encaminha tickets (movimenta sem resolver)."""
    titulo('2. QUEM MAIS MOVIMENTA TICKETS')
    df = pd.read_sql('''
        SELECT
            autor,
            COUNT(*) AS total_movimentacoes,
            COUNT(DISTINCT ticket_id) AS tickets_distintos
        FROM movimentacoes
        WHERE autor IS NOT NULL
        GROUP BY autor
        ORDER BY total_movimentacoes DESC
        LIMIT 15
    ''', conn)
    mostrar(df)


def c3_fluxo_autores(conn):
    """Sequência de quem tocou cada ticket (primeiros 10 tickets)."""
    titulo('3. FLUXO DE AUTORES (amostra)')

    df = pd.read_sql('''
        SELECT
            ticket_id,
            data_movimentacao,
            autor,
            para_status
        FROM movimentacoes
        WHERE ticket_id IN (
            SELECT ticket_id FROM movimentacoes
            WHERE autor IS NOT NULL
            GROUP BY ticket_id
            HAVING COUNT(DISTINCT autor) >= 3
            LIMIT 5
        )
        ORDER BY ticket_id, data_movimentacao
    ''', conn)

    # Agrupa por ticket para visualizar o fluxo
    for tid, grupo in df.groupby('ticket_id'):
        print(f'\n▶ Ticket {tid}:')
        for _, r in grupo.iterrows():
            data = r['data_movimentacao']
            print(f'   {data} | {r["autor"]:<28} → {r["para_status"]}')


def c4_tempo_entre_movimentacoes(conn):
    """Tempo médio entre movimentações por autor."""
    titulo('4. TEMPO MÉDIO ENTRE MOVIMENTAÇÕES')
    df = pd.read_sql('''
        WITH diffs AS (
            SELECT
                ticket_id,
                autor,
                data_movimentacao,
                LAG(data_movimentacao) OVER (
                    PARTITION BY ticket_id ORDER BY data_movimentacao
                ) AS data_anterior
            FROM movimentacoes
            WHERE data_movimentacao IS NOT NULL
        )
        SELECT
            autor,
            COUNT(*) AS movimentacoes,
            ROUND(AVG(
                (julianday(data_movimentacao) - julianday(data_anterior)) * 24
            ), 1) AS horas_entre_movs,
            ROUND(MAX(
                (julianday(data_movimentacao) - julianday(data_anterior)) * 24
            ), 0) AS maior_gap_horas
        FROM diffs
        WHERE data_anterior IS NOT NULL
          AND autor IS NOT NULL
        GROUP BY autor
        HAVING COUNT(*) >= 2
        ORDER BY horas_entre_movs DESC
        LIMIT 15
    ''', conn)
    mostrar(df)


def c5_mensagens_por_autor(conn):
    """Quem mais escreve mensagens."""
    titulo('5. QUEM MAIS ESCREVE MENSAGENS')
    df = pd.read_sql('''
        SELECT
            autor,
            COUNT(*) AS mensagens,
            COUNT(DISTINCT ticket_id) AS tickets_distintos
        FROM mensagens
        WHERE autor IS NOT NULL
        GROUP BY autor
        ORDER BY mensagens DESC
        LIMIT 15
    ''', conn)
    mostrar(df)


def c6_tickets_parados(conn):
    """Tickets que tiveram grande gap (> 5 dias) entre movimentações."""
    titulo('6. TICKETS COM MAIOR GAP ENTRE MOVIMENTAÇÕES')
    df = pd.read_sql('''
        WITH diffs AS (
            SELECT
                ticket_id,
                autor,
                data_movimentacao,
                LAG(data_movimentacao) OVER (
                    PARTITION BY ticket_id ORDER BY data_movimentacao
                ) AS data_anterior,
                LAG(autor) OVER (
                    PARTITION BY ticket_id ORDER BY data_movimentacao
                ) AS autor_anterior
            FROM movimentacoes
            WHERE data_movimentacao IS NOT NULL
        )
        SELECT
            ticket_id,
            autor_anterior AS quem_deixou,
            autor AS quem_recebeu,
            ROUND((julianday(data_movimentacao) - julianday(data_anterior)), 1) AS dias_parado
        FROM diffs
        WHERE data_anterior IS NOT NULL
          AND (julianday(data_movimentacao) - julianday(data_anterior)) > 5
        ORDER BY dias_parado DESC
        LIMIT 20
    ''', conn)
    mostrar(df)


def c7_pessoas_por_ticket(conn):
    """Distribuição de quantas pessoas tocam cada ticket."""
    titulo('7. QUANTAS PESSOAS TOCAM CADA TICKET')
    df = pd.read_sql('''
        WITH seq AS (
            SELECT
                ticket_id,
                COUNT(DISTINCT autor) AS pessoas
            FROM movimentacoes
            WHERE autor IS NOT NULL
            GROUP BY ticket_id
        )
        SELECT
            pessoas,
            COUNT(*) AS quantidade_tickets,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM seq), 1) AS percentual
        FROM seq
        GROUP BY pessoas
        ORDER BY pessoas
    ''', conn)
    mostrar(df)


# ============================================================
CONSULTAS = {
    1: ('Pulos por Ticket', c1_pulos_por_ticket),
    2: ('Ranking Encaminhadores', c2_ranking_encaminhadores),
    3: ('Fluxo de Autores', c3_fluxo_autores),
    4: ('Tempo entre Movimentações', c4_tempo_entre_movimentacoes),
    5: ('Mensagens por Autor', c5_mensagens_por_autor),
    6: ('Tickets Parados', c6_tickets_parados),
    7: ('Pessoas por Ticket', c7_pessoas_por_ticket),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--consulta', type=int)
    parser.add_argument('--listar', action='store_true')
    args = parser.parse_args()

    if args.listar:
        print('\n📋 Consultas disponíveis:')
        for n, (nome, _) in CONSULTAS.items():
            print(f'   {n:>2}. {nome}')
        return

    conn = conectar()

    if args.consulta:
        if args.consulta not in CONSULTAS:
            print(f'❌ Consulta {args.consulta} não existe.')
            return
        _, func = CONSULTAS[args.consulta]
        func(conn)
    else:
        for n, (nome, func) in CONSULTAS.items():
            try:
                func(conn)
            except Exception as e:
                print(f'⚠️ Erro na consulta {n}: {e}')

    conn.close()


if __name__ == '__main__':
    main()