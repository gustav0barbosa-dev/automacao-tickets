# ============================================================
# consultas.py - Consultas prontas no banco SQLite
# ============================================================
"""
Roda consultas pré-definidas no banco tickets.db e imprime
os resultados formatados.

Uso:
    python scripts/consultas.py               # roda todas
    python scripts/consultas.py --consulta 3  # roda uma específica
    python scripts/consultas.py --listar      # lista disponíveis
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd


# ==================== CAMINHOS ====================
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = RAIZ_PROJETO / 'dados' / 'tickets.db'


# ==================== CONEXÃO ====================
def conectar():
    if not CAMINHO_BANCO.exists():
        print(f'❌ Banco não encontrado: {CAMINHO_BANCO}')
        print('   Rode "python src/programa4_persistir.py" primeiro.')
        sys.exit(1)
    return sqlite3.connect(CAMINHO_BANCO)


# ==================== HELPERS ====================
def titulo(texto):
    print()
    print('=' * 70)
    print(f'  {texto}')
    print('=' * 70)


def subtitulo(texto):
    print(f'\n▸ {texto}')


def mostrar_df(df, limite=None):
    """Imprime DataFrame formatado."""
    if limite:
        df = df.head(limite)
    if df.empty:
        print('   (sem dados)')
        return
    with pd.option_context('display.max_columns', None,
                           'display.width', 200,
                           'display.max_colwidth', 40):
        print(df.to_string(index=False))


# ==================== CONSULTAS ====================

def consulta_1_visao_geral(conn):
    """Visão geral do banco."""
    titulo('1. VISÃO GERAL DO BANCO')

    total = pd.read_sql('SELECT COUNT(*) AS total FROM tickets', conn).iloc[0, 0]
    por_status = pd.read_sql("""
        SELECT status, COUNT(*) AS quantidade
        FROM tickets
        GROUP BY status
        ORDER BY quantidade DESC
    """, conn)

    subtitulo(f'Total de tickets: {total}')
    subtitulo('Por status:')
    mostrar_df(por_status)

    # Período coberto
    periodo = pd.read_sql("""
        SELECT
            MIN(criado_data) AS primeiro,
            MAX(criado_data) AS ultimo
        FROM tickets
        WHERE criado_data IS NOT NULL
    """, conn)
    subtitulo('Período coberto:')
    mostrar_df(periodo)


def consulta_2_tempo_resposta(conn):
    """Tempo de resposta por categoria."""
    titulo('2. TEMPO DE RESOLUÇÃO POR CATEGORIA')

    df = pd.read_sql("""
        SELECT
            categoria,
            COUNT(*) AS total,
            ROUND(AVG(horas_resolucao) / 24, 1) AS dias_medio,
            ROUND(AVG(horas_1a_resposta) / 24, 1) AS dias_ate_1a_resposta
        FROM vw_tempo_resposta
        WHERE categoria IS NOT NULL
        GROUP BY categoria
        HAVING COUNT(*) >= 5
        ORDER BY dias_medio DESC
        LIMIT 15
    """, conn)

    mostrar_df(df)


def consulta_3_sla(conn):
    """Cumprimento de SLA."""
    titulo('3. CUMPRIMENTO DE SLA')

    geral = pd.read_sql("""
        SELECT
            status_sla,
            COUNT(*) AS quantidade,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM vw_sla), 1) AS percentual
        FROM vw_sla
        GROUP BY status_sla
        ORDER BY quantidade DESC
    """, conn)

    subtitulo('Geral:')
    mostrar_df(geral)

    por_categoria = pd.read_sql("""
        SELECT
            categoria,
            COUNT(*) AS total,
            SUM(CASE WHEN status_sla = 'cumprido' THEN 1 ELSE 0 END) AS cumpridos,
            ROUND(
                100.0 * SUM(CASE WHEN status_sla = 'cumprido' THEN 1 ELSE 0 END)
                / COUNT(*), 1
            ) AS percentual_sla
        FROM vw_sla
        WHERE categoria IS NOT NULL
        GROUP BY categoria
        HAVING COUNT(*) >= 5
        ORDER BY percentual_sla ASC
        LIMIT 15
    """, conn)

    subtitulo('Por categoria (piores primeiro):')
    mostrar_df(por_categoria)


def consulta_4_produtividade(conn):
    """Produtividade por responsável."""
    titulo('4. PRODUTIVIDADE POR RESPONSÁVEL')

    df = pd.read_sql("""
        SELECT
            responsavel_atual AS responsavel,
            COUNT(*) AS total_tickets,
            SUM(CASE WHEN status = 'Resolvido' THEN 1 ELSE 0 END) AS resolvidos,
            SUM(CASE WHEN status NOT IN ('Resolvido', 'Fechado', 'Cancelado')
                     THEN 1 ELSE 0 END) AS em_aberto,
            ROUND(AVG(
                CASE WHEN data_resolvido IS NOT NULL
                     THEN (julianday(data_resolvido) - julianday(criado_data))
                END
            ), 1) AS dias_medio_resolucao
        FROM tickets
        WHERE responsavel_atual IS NOT NULL
          AND responsavel_atual != ''
          AND responsavel_atual != 'Não informado'
        GROUP BY responsavel_atual
        HAVING COUNT(*) >= 5
        ORDER BY total_tickets DESC
        LIMIT 20
    """, conn)

    mostrar_df(df)


def consulta_5_backlog(conn):
    """Backlog atual e aging."""
    titulo('5. BACKLOG ATUAL')

    df = pd.read_sql("""
        SELECT
            status,
            COUNT(*) AS quantidade,
            ROUND(AVG(julianday('now') - julianday(criado_data)), 1) AS dias_medio_aberto
        FROM tickets
        WHERE status NOT IN ('Resolvido', 'Fechado', 'Cancelado', 'Duplicado')
        GROUP BY status
        ORDER BY quantidade DESC
    """, conn)

    mostrar_df(df)

    # Por categoria
    subtitulo('Top 10 categorias com mais backlog:')
    cats = pd.read_sql("""
        SELECT
            categoria,
            COUNT(*) AS em_aberto
        FROM tickets
        WHERE status NOT IN ('Resolvido', 'Fechado', 'Cancelado', 'Duplicado')
          AND categoria IS NOT NULL
        GROUP BY categoria
        ORDER BY em_aberto DESC
        LIMIT 10
    """, conn)
    mostrar_df(cats)


def consulta_6_sazonalidade(conn):
    """Volume por mês/ano."""
    titulo('6. SAZONALIDADE — VOLUME POR MÊS')

    df = pd.read_sql("""
        SELECT
            strftime('%Y-%m', criado_data) AS mes,
            COUNT(*) AS tickets_criados
        FROM tickets
        WHERE criado_data IS NOT NULL
        GROUP BY mes
        ORDER BY mes DESC
        LIMIT 24
    """, conn)

    mostrar_df(df)


def consulta_7_reincidencia(conn):
    """Solicitantes com mais tickets."""
    titulo('7. TOP 10 SOLICITANTES')

    df = pd.read_sql("""
        SELECT
            solicitante,
            COUNT(*) AS total_tickets,
            MIN(criado_data) AS primeiro,
            MAX(criado_data) AS ultimo
        FROM tickets
        WHERE solicitante IS NOT NULL
          AND solicitante != ''
        GROUP BY solicitante
        ORDER BY total_tickets DESC
        LIMIT 10
    """, conn)

    mostrar_df(df)


def consulta_8_tempo_por_prioridade(conn):
    """Tempo por prioridade."""
    titulo('8. TEMPO DE RESOLUÇÃO POR PRIORIDADE')

    df = pd.read_sql("""
        SELECT
            prioridade,
            COUNT(*) AS total,
            ROUND(AVG(
                CASE WHEN data_resolvido IS NOT NULL
                     THEN (julianday(data_resolvido) - julianday(criado_data))
                END
            ), 1) AS dias_medio
        FROM tickets
        WHERE prioridade IS NOT NULL
        GROUP BY prioridade
        ORDER BY dias_medio DESC
    """, conn)

    mostrar_df(df)


def consulta_9_top_categorias(conn):
    """Volume por categoria."""
    titulo('9. TOP 15 CATEGORIAS POR VOLUME')

    df = pd.read_sql("""
        SELECT
            categoria,
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Resolvido' THEN 1 ELSE 0 END) AS resolvidos,
            ROUND(
                100.0 * SUM(CASE WHEN status = 'Resolvido' THEN 1 ELSE 0 END)
                / COUNT(*), 1
            ) AS percentual_resolvido
        FROM tickets
        WHERE categoria IS NOT NULL
        GROUP BY categoria
        ORDER BY total DESC
        LIMIT 15
    """, conn)

    mostrar_df(df)


def consulta_10_tickets_parados(conn):
    """Tickets abertos há mais tempo."""
    titulo('10. TICKETS ABERTOS HÁ MAIS TEMPO')

    df = pd.read_sql("""
        SELECT
            id,
            substr(titulo, 1, 50) AS titulo,
            status,
            responsavel_atual AS responsavel,
            CAST(julianday('now') - julianday(criado_data) AS INTEGER) AS dias_aberto
        FROM tickets
        WHERE status NOT IN ('Resolvido', 'Fechado', 'Cancelado', 'Duplicado')
        ORDER BY dias_aberto DESC
        LIMIT 20
    """, conn)

    mostrar_df(df)


# ==================== REGISTRO ====================
CONSULTAS = {
    1:  ('Visão Geral',                  consulta_1_visao_geral),
    2:  ('Tempo de Resposta',            consulta_2_tempo_resposta),
    3:  ('SLA',                          consulta_3_sla),
    4:  ('Produtividade',                consulta_4_produtividade),
    5:  ('Backlog',                      consulta_5_backlog),
    6:  ('Sazonalidade',                 consulta_6_sazonalidade),
    7:  ('Reincidência',                 consulta_7_reincidencia),
    8:  ('Tempo por Prioridade',         consulta_8_tempo_por_prioridade),
    9:  ('Top Categorias',               consulta_9_top_categorias),
    10: ('Tickets Parados',              consulta_10_tickets_parados),
}


# ==================== MAIN ====================
def main():
    parser = argparse.ArgumentParser(description='Consultas prontas no banco.')
    parser.add_argument('--consulta', type=int, help='Número da consulta (1-10)')
    parser.add_argument('--listar', action='store_true', help='Lista as consultas')
    args = parser.parse_args()

    if args.listar:
        print('\n📋 Consultas disponíveis:')
        for num, (nome, _) in CONSULTAS.items():
            print(f'   {num:>2}. {nome}')
        return

    conn = conectar()

    if args.consulta:
        if args.consulta not in CONSULTAS:
            print(f'❌ Consulta {args.consulta} não existe.')
            return
        nome, func = CONSULTAS[args.consulta]
        func(conn)
    else:
        for num, (nome, func) in CONSULTAS.items():
            try:
                func(conn)
            except Exception as e:
                print(f'⚠️ Erro na consulta {num} ({nome}): {e}')

    conn.close()
    print('\n' + '=' * 70)
    print('  ✅ CONSULTAS CONCLUÍDAS')
    print('=' * 70)


if __name__ == '__main__':
    main()