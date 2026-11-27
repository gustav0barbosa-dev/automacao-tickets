#!/usr/bin/env python
# ============================================================
# scripts/exportar_sqlite_para_sql.py
# ============================================================
"""
Exporta as tabelas do SQLite local para um arquivo SQL (dados.sql)
com INSERTs prontos para serem colados no SQL Editor do Neon.

Útil quando a porta 5432 está bloqueada na rede local: o arquivo
gerado pode ser executado diretamente no painel web do Neon.

Características:
    - Não conecta ao Neon.
    - Lê o SQLite via pandas (read_sql).
    - Converte datas para 'YYYY-MM-DD HH:MM:SS' (ou 'YYYY-MM-DD'
      para colunas de data) e nulos para NULL.
    - Gera INSERT INTO "tabela" ("col", ...) VALUES (...);
      ON CONFLICT DO NOTHING;
    - Envolve tudo em BEGIN; ... COMMIT;
    - Por padrão aplica a anonimização LGPD do projeto.

Uso:
    python scripts/exportar_sqlite_para_sql.py
    python scripts/exportar_sqlite_para_sql.py --output dados/dados.sql
    python scripts/exportar_sqlite_para_sql.py --tables tickets,movimentacoes
    python scripts/exportar_sqlite_para_sql.py --no-anonimizar
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SQLITE_PADRAO = RAIZ / 'dados' / 'tickets.db'
SAIDA_PADRAO = RAIZ / 'dados' / 'dados.sql'
SCHEMA_PADRAO = 'public'

ORDEM_TABELAS = [
    'areas',
    'analistas',
    'tickets',
    'movimentacoes',
    'mensagens',
    'snapshots',
]
TABELAS_IGNORADAS = {'sqlite_sequence'}

# Colunas cujo valor é uma data (sem horário) no SQLite.
COLUNAS_APENAS_DATA = {'snapshot_data'}

# Colunas que no Postgres são inteiras (evita gerar 4.0 em coluna INTEGER).
COLUNAS_INTEIRAS_CONHECIDAS = {
    'id', 'ticket_id', 'enriquecido', 'respondido', 'acao_interna',
    'pendente_usuario', 'backlog', 'dias_uteis_resolucao',
    'sla_criticidade_ok', 'meta_diaria', 'ativo',
    'primeira_acao_responsavel', 'tickets_total', 'tickets_novos',
    'tickets_atualizados', 'tickets_mudaram', 'tickets_enriquecidos',
    'peso_criticidade',
}

# Colunas de data/hora (heurística + lista explícita).
COLUNAS_DATAHORA_EXPLICITAS = {
    'criado_data',
    'alterado_data',
    'previsao',
    'data_resolvido',
    'data_1_resolvido',
    'previsao_esperada',
    'data_movimentacao',
    'data_hora',
    'data_execucao',
    'enriquecido_em',
    'criado_em',
    'atualizado_em',
    'atualizado_em',
}

sys.path.insert(0, str(RAIZ / 'src'))

logger = logging.getLogger('exportar_sqlite_para_sql')


def _is_null(valor: Any) -> bool:
    if valor is None:
        return True
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def _eh_coluna_data(coluna: str) -> bool:
    nome = (coluna or '').lower()
    if nome in COLUNAS_DATAHORA_EXPLICITAS:
        return True
    if nome in COLUNAS_APENAS_DATA:
        return True
    if 'data' in nome or 'hora' in nome or 'previsao' in nome:
        return True
    if 'execucao' in nome or nome.endswith('_em'):
        return True
    return False


def _eh_coluna_apenas_data(coluna: str) -> bool:
    nome = (coluna or '').lower()
    if nome in COLUNAS_APENAS_DATA:
        return True
    return 'snapshot' in nome and 'data' in nome


def _converter_valor(coluna: str, valor: Any) -> Any:
    """Converte um valor do SQLite para um tipo Python pronto para SQL."""
    if _is_null(valor):
        return None

    # Colunas inteiras conhecidas: evita 4.0 em coluna INTEGER.
    if (coluna or '').lower() in COLUNAS_INTEIRAS_CONHECIDAS:
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return valor
        if numero.is_integer():
            return int(numero)
        return numero

    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, default=str)

    if isinstance(valor, (pd.Timestamp,)):
        if _eh_coluna_apenas_data(coluna):
            return valor.date()
        return valor

    if isinstance(valor, (np.integer,)):
        return int(valor)
    if isinstance(valor, (np.floating,)):
        valor_float = float(valor)
        if math.isnan(valor_float) or math.isinf(valor_float):
            return None
        return valor_float
    if isinstance(valor, (np.bool_,)):
        return bool(valor)
    if isinstance(valor, (np.ndarray,)):
        return valor.tolist()

    if isinstance(valor, str) and _eh_coluna_data(coluna):
        ts = pd.to_datetime(valor, errors='coerce', dayfirst=False)
        if pd.isna(ts):
            return valor
        if _eh_coluna_apenas_data(coluna):
            return ts.date()
        return ts.to_pydatetime() if isinstance(ts, pd.Timestamp) else ts

    return valor


def _sql_literal(valor: Any, coluna: str = '') -> str:
    """Converte um valor Python em literal SQL seguro."""
    if _is_null(valor):
        return 'NULL'

    if isinstance(valor, bool):
        return 'TRUE' if valor else 'FALSE'

    if isinstance(valor, (int, np.integer)):
        return str(int(valor))

    if isinstance(valor, (float, np.floating)):
        if math.isnan(valor) or math.isinf(valor):
            return 'NULL'
        return repr(float(valor))

    if isinstance(valor, (datetime,)):
        return "'" + valor.strftime('%Y-%m-%d %H:%M:%S') + "'"

    if isinstance(valor, (pd.Timestamp,)):
        if _eh_coluna_apenas_data(coluna):
            return "'" + valor.strftime('%Y-%m-%d') + "'"
        return "'" + valor.strftime('%Y-%m-%d %H:%M:%S') + "'"

    # datetime.date (sem horário)
    if hasattr(valor, 'isoformat') and not hasattr(valor, 'hour'):
        return "'" + valor.isoformat() + "'"

    if isinstance(valor, (dict, list)):
        texto = json.dumps(valor, ensure_ascii=False, default=str)
        return "'" + texto.replace("'", "''") + "'"

    if isinstance(valor, bytes):
        return "NULL"

    texto = str(valor).replace('\x00', '')
    return "'" + texto.replace("'", "''") + "'"


def _listar_tabelas_sqlite(conn: sqlite3.Connection) -> list[str]:
    linhas = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    tabelas = [nome for (nome,) in linhas if nome not in TABELAS_IGNORADAS]
    # Ordem respeitando FKs.
    ordenadas = [t for t in ORDEM_TABELAS if t in tabelas]
    ordenadas += [t for t in tabelas if t not in ordenadas]
    return ordenadas


def _ler_tabela(conn: sqlite3.Connection, tabela: str) -> pd.DataFrame:
    sql = f'SELECT * FROM "{tabela}"'
    return pd.read_sql_query(sql, conn)


def _anonimizar_dataframe(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    try:
        from utils_anonimizacao import CAMPOS_POR_TABELA, anonimizar_texto
    except ImportError as exc:
        raise RuntimeError(
            'Não foi possível importar src/utils_anonimizacao.py. '
            'Execute a partir da raiz do projeto ou use --no-anonimizar.'
        ) from exc

    campos = CAMPOS_POR_TABELA.get(tabela, [])
    for campo in campos:
        if campo not in df.columns:
            continue
        logger.info('  Anonimizando %s.%s', tabela, campo)
        df[campo] = df[campo].map(
            lambda valor: valor if _is_null(valor) else anonimizar_texto(valor)
        )
    return df


def _quote_ident(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


def _gerar_insert(
    tabela: str,
    colunas: list[str],
    valores: list[Any],
    schema: str = 'public',
) -> str:
    cols_sql = ', '.join(_quote_ident(c) for c in colunas)
    vals_sql = ', '.join(_sql_literal(v, c) for v, c in zip(valores, colunas))
    tabela_sql = f'{_quote_ident(schema)}.{_quote_ident(tabela)}'
    return (
        f'INSERT INTO {tabela_sql} ({cols_sql}) '
        f'VALUES ({vals_sql}) ON CONFLICT DO NOTHING;'
    )


def _processar_tabela(
    conn: sqlite3.Connection,
    tabela: str,
    anonimizar: bool,
    arquivo,
    schema: str = 'public',
) -> int:
    logger.info('=' * 70)
    logger.info('TABELA: %s', tabela)

    df = _ler_tabela(conn, tabela)
    logger.info('  %d registros lidos do SQLite', len(df))

    if df.empty:
        logger.info('  Tabela vazia; pulando.')
        arquivo.write(f'-- Tabela {tabela}: vazia, nada a inserir.\n')
        return 0

    if anonimizar:
        df = _anonimizar_dataframe(df, tabela)

    colunas = list(df.columns)
    total = 0
    for _, linha in df.iterrows():
        valores_convertidos = [
            _converter_valor(col, linha[col]) for col in colunas
        ]
        arquivo.write(
            _gerar_insert(tabela, colunas, valores_convertidos, schema) + '\n'
        )
        total += 1

    logger.info('  %d INSERTs gerados.', total)
    return total


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Exporta o SQLite local para um arquivo SQL (dados.sql) '
                    'pronto para o SQL Editor do Neon.'
    )
    parser.add_argument(
        '--sqlite',
        default=str(SQLITE_PADRAO),
        help=f'Caminho do tickets.db (default: {SQLITE_PADRAO}).',
    )
    parser.add_argument(
        '--output',
        default=str(SAIDA_PADRAO),
        help=f'Arquivo .sql de saída (default: {SAIDA_PADRAO}).',
    )
    parser.add_argument(
        '--tables',
        default=None,
        help='Lista separada por vírgula. Default: todas as tabelas.',
    )
    parser.add_argument(
        '--schema',
        default=SCHEMA_PADRAO,
        help=f'Schema de destino (default: {SCHEMA_PADRAO}).',
    )
    parser.add_argument(
        '--no-anonimizar',
        action='store_true',
        help='Desativa a anonimização LGPD (NÃO recomendado).',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stdout,
    )

    sqlite_path = Path(args.sqlite).expanduser().resolve()
    if not sqlite_path.exists():
        logger.error('SQLite não encontrado: %s', sqlite_path)
        return 1

    saida_path = Path(args.output).expanduser().resolve()
    saida_path.parent.mkdir(parents=True, exist_ok=True)

    anonimizar = not args.no_anonimizar

    conn = sqlite3.connect(sqlite_path)
    conn.execute('PRAGMA query_only = ON')

    try:
        tabelas_sqlite = _listar_tabelas_sqlite(conn)
        logger.info('Tabelas no SQLite: %s', tabelas_sqlite)

        if args.tables:
            tabelas = [
                t.strip() for t in args.tables.split(',') if t.strip()
            ]
        else:
            tabelas = tabelas_sqlite

        tabelas = [t for t in tabelas if t in tabelas_sqlite]
        if not tabelas:
            logger.error('Nenhuma tabela válida para exportar.')
            return 1

        logger.info('Ordem de exportação: %s', tabelas)
        logger.info('Saída: %s', saida_path)
        logger.info('Anonimizar: %s', anonimizar)

        total = 0
        with saida_path.open('w', encoding='utf-8', newline='\n') as arquivo:
            arquivo.write('-- ============================================================\n')
            arquivo.write('-- Exportação SQLite -> PostgreSQL (Neon)\n')
            arquivo.write(f'-- Gerado a partir de: {sqlite_path.name}\n')
            arquivo.write('-- Cole este arquivo no SQL Editor do Neon.\n')
            arquivo.write('-- ============================================================\n\n')
            arquivo.write('BEGIN;\n\n')

            for tabela in tabelas:
                arquivo.write(f'-- ---------- {tabela} ----------\n')
                total += _processar_tabela(
                    conn, tabela, anonimizar, arquivo, args.schema
                )
                arquivo.write('\n')

            arquivo.write('COMMIT;\n')

        logger.info('=' * 70)
        logger.info('CONCLUÍDO: %d INSERTs gravados em %s', total, saida_path)
        logger.info('=' * 70)
        return 0

    except RuntimeError as exc:
        logger.error('ERRO: %s', exc)
        return 1
    except KeyboardInterrupt:
        logger.warning('Interrompido pelo usuário.')
        return 130
    except Exception:
        logger.exception('Erro inesperado durante a exportação.')
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
