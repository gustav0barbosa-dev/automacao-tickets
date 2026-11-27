#!/usr/bin/env python
# ============================================================
# scripts/migrar_sqlite_para_postgres.py
# ============================================================
"""
Migra os dados do SQLite local para o PostgreSQL do Neon.

Regras importantes:
    - NÃO executa DROP, TRUNCATE ou CREATE TABLE.
    - Insere apenas nas tabelas que já existem no Neon.
    - Usa ON CONFLICT DO NOTHING para ser idempotente.
    - Converte tipos com base no schema REAL do PostgreSQL
      (timestamp, date, boolean, integer, numeric, json, etc.).
    - Por padrão, aplica a anonimização LGPD já usada pelo projeto.
      Use --no-anonimizar para desativar.

Conexão:
    A URL é lida de NEON_DATABASE_URL. Por compatibilidade, aceita
    DATABASE_URL como fallback (com aviso).

Uso:
    python scripts/migrar_sqlite_para_postgres.py
    python scripts/migrar_sqlite_para_postgres.py --dry-run
    python scripts/migrar_sqlite_para_postgres.py --tables tickets,movimentacoes
    python scripts/migrar_sqlite_para_postgres.py --no-anonimizar

RLS:
    Execute com o usuário owner/service do Neon (ex.: neondb_owner).
    As políticas de RLS e os GRANTs para o role `authenticated` são
    aplicados à Data API, não a esta conexão administrativa.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.pool import NullPool

# ==================== CONFIGURAÇÃO ====================
RAIZ = Path(__file__).resolve().parent.parent
SQLITE_PADRAO = RAIZ / 'dados' / 'tickets.db'
SCHEMA_PADRAO = 'public'
BATCH_SIZE_PADRAO = 500
TIMEZONE_PADRAO = 'America/Sao_Paulo'

# Ordem respeita as dependências de FK (tickets antes de movimentações/mensagens).
ORDEM_TABELAS = [
    'areas',
    'analistas',
    'tickets',
    'movimentacoes',
    'mensagens',
    'snapshots',
]
TABELAS_IGNORADAS = {'sqlite_sequence'}

# Adiciona src/ ao path para importar a anonimização do projeto.
sys.path.insert(0, str(RAIZ / 'src'))

logger = logging.getLogger('migracao_sqlite_neon')


class MigrationError(RuntimeError):
    """Erro controlado da migração."""


@dataclass(frozen=True)
class ColunaDestino:
    nome: str
    data_type: str
    udt_name: str
    nullable: bool
    default: str | None
    identity: str | None       # ALWAYS | BY DEFAULT | None
    generated: str | None      # ALWAYS | NEVER


@dataclass(frozen=True)
class PlanoTabela:
    tabela: str
    colunas: list[ColunaDestino]
    pk: list[str]
    colunas_inseriveis: list[str]
    identity_always: bool


# ==================== .ENV / URL ====================
def _carregar_env_local() -> None:
    """Carrega .env da raiz sem sobrescrever variáveis já definidas."""
    caminho = RAIZ / '.env'
    if not caminho.exists():
        return

    try:
        for linha in caminho.read_text(encoding='utf-8-sig').splitlines():
            linha = linha.strip()
            if not linha or linha.startswith('#') or '=' not in linha:
                continue

            if linha.startswith('export '):
                linha = linha[len('export '):].strip()

            chave, _, valor = linha.partition('=')
            chave = chave.strip()
            valor = valor.strip().strip('"').strip("'")

            if chave and chave not in os.environ:
                os.environ[chave] = valor
    except OSError:
        pass


def _driver_postgres_disponivel() -> str | None:
    """
    Escolhe um driver PostgreSQL instalado.

    Prefere psycopg2 (compatível com a documentação e com o .venv do
    projeto); cai para psycopg (v3) se for o único disponível.
    """
    try:
        import psycopg2  # noqa: F401
        return 'postgresql+psycopg2'
    except ImportError:
        pass

    try:
        import psycopg  # noqa: F401
        return 'postgresql+psycopg'
    except ImportError:
        return None


def _normalizar_url(url: str) -> str:
    """
    Normaliza a URL para o SQLAlchemy:

    - Converte postgres:// em postgresql://.
    - Escolhe um driver instalado (psycopg2 ou psycopg v3).
    - Remove channel_binding=require (drivers/libpq antigos rejeitam).
    - Garante sslmode=require quando não informado.
    """
    url = (url or '').strip()
    if not url:
        raise MigrationError('NEON_DATABASE_URL está vazia.')

    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]

    driver = _driver_postgres_disponivel()
    if driver is None:
        raise MigrationError(
            'Nenhum driver PostgreSQL instalado. Rode: '
            'pip install psycopg2-binary  (ou psycopg[binary]).'
        )

    partes = urlsplit(url)
    if partes.scheme in ('postgresql', 'postgres'):
        esquema = driver
    elif partes.scheme.startswith('postgresql+'):
        esquema = partes.scheme
    else:
        esquema = partes.scheme

    query = [
        (chave, valor)
        for chave, valor in parse_qsl(partes.query, keep_blank_values=True)
        if chave.lower() != 'channel_binding'
    ]

    if not any(chave.lower() == 'sslmode' for chave, _ in query):
        query.append(('sslmode', 'require'))

    return urlunsplit((
        esquema,
        partes.netloc,
        partes.path,
        urlencode(query),
        partes.fragment,
    ))


def _url_mascarada(url: str) -> str:
    """Retorna a URL sem a senha, para logs."""
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return '<URL inválida>'


# ==================== HELPERS ====================
_IDENTIFICADOR_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _quote_ident(nome: str) -> str:
    """Valida e coloca um identificador SQL entre aspas duplas."""
    if not _IDENTIFICADOR_RE.match(nome or ''):
        raise MigrationError(f'Identificador inválido: {nome!r}')
    return f'"{nome}"'


def _is_null(valor: Any) -> bool:
    """pd.isna seguro para escalares, listas e dicionários."""
    if valor is None:
        return True
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def _to_bool(valor: Any) -> bool | None:
    if _is_null(valor):
        return None
    if isinstance(valor, (bool, np.bool_)):
        return bool(valor)
    if isinstance(valor, (int, float, np.integer, np.floating)):
        return bool(int(valor))

    texto = str(valor).strip().lower()
    if texto in {'1', 'true', 't', 'yes', 'y', 'sim', 's'}:
        return True
    if texto in {'0', 'false', 'f', 'no', 'n', 'nao', 'não'}:
        return False

    # Aceita "0.0", "1.0", etc.
    try:
        return bool(float(texto))
    except ValueError:
        return None


def _to_text(valor: Any) -> str | None:
    if _is_null(valor):
        return None
    if isinstance(valor, str):
        # PostgreSQL não aceita NUL em colunas text.
        return valor.replace('\x00', '')
    return str(valor)


def _to_json(valor: Any) -> str | None:
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, default=str)
    if _is_null(valor):
        return None
    return str(valor)


def _to_python(valor: Any) -> Any:
    """Converte tipos numpy/pandas para tipos nativos aceitos pelo psycopg2."""
    if _is_null(valor):
        return None
    if isinstance(valor, pd.Timestamp):
        return valor.to_pydatetime()
    if isinstance(valor, np.datetime64):
        return pd.Timestamp(valor).to_pydatetime()
    if isinstance(valor, np.ndarray):
        return valor.tolist()
    if isinstance(valor, np.integer):
        return int(valor)
    if isinstance(valor, np.floating):
        return float(valor)
    if isinstance(valor, np.bool_):
        return bool(valor)
    return valor


# ==================== LEITURA DO SQLITE ====================
def _listar_tabelas_sqlite(conn: sqlite3.Connection) -> list[str]:
    linhas = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [nome for (nome,) in linhas if nome not in TABELAS_IGNORADAS]


def _ler_tabela_sqlite(conn: sqlite3.Connection, tabela: str) -> pd.DataFrame:
    sql = f'SELECT * FROM {_quote_ident(tabela)}'
    return pd.read_sql_query(sql, conn)


def _anonimizar_dataframe(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """Aplica a anonimização LGPD configurada no projeto."""
    try:
        from utils_anonimizacao import CAMPOS_POR_TABELA, anonimizar_texto
    except ImportError as exc:
        raise MigrationError(
            'Não foi possível importar src/utils_anonimizacao.py. '
            'Execute o script a partir da raiz do projeto ou use '
            '--no-anonimizar.'
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


# ==================== INTROSPECÇÃO DO POSTGRESQL ====================
def _tabela_existe(conn, schema: str, tabela: str) -> bool:
    return bool(conn.execute(
        text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema
              AND table_name = :tabela
              AND table_type = 'BASE TABLE'
        """),
        {'schema': schema, 'tabela': tabela},
    ).scalar())


def _colunas_destino(conn, schema: str, tabela: str) -> list[ColunaDestino]:
    linhas = conn.execute(
        text("""
            SELECT column_name,
                   data_type,
                   udt_name,
                   is_nullable,
                   column_default,
                   is_identity,
                   identity_generation,
                   is_generated
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :tabela
            ORDER BY ordinal_position
        """),
        {'schema': schema, 'tabela': tabela},
    ).mappings().all()

    return [
        ColunaDestino(
            nome=linha['column_name'],
            data_type=(linha['data_type'] or '').lower(),
            udt_name=(linha['udt_name'] or '').lower(),
            nullable=linha['is_nullable'] == 'YES',
            default=linha['column_default'],
            identity=(
                linha['identity_generation']
                if linha['is_identity'] == 'YES'
                else None
            ),
            generated=linha['is_generated'],
        )
        for linha in linhas
    ]


def _pk_destino(conn, schema: str, tabela: str) -> list[str]:
    linhas = conn.execute(
        text("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = :schema
              AND tc.table_name = :tabela
            ORDER BY kcu.ordinal_position
        """),
        {'schema': schema, 'tabela': tabela},
    ).scalars().all()
    return list(linhas)


def _montar_plano(
    conn,
    schema: str,
    tabela: str,
    colunas_origem: list[str],
) -> PlanoTabela:
    colunas = _colunas_destino(conn, schema, tabela)
    pk = _pk_destino(conn, schema, tabela)

    origem = set(colunas_origem)
    inseriveis = [
        coluna.nome
        for coluna in colunas
        if coluna.nome in origem
        and (coluna.generated or 'NEVER').upper() != 'ALWAYS'
    ]

    if not inseriveis:
        raise MigrationError(
            f'{tabela}: nenhuma coluna em comum entre origem e destino.'
        )

    obrigatorias_ausentes = [
        coluna.nome
        for coluna in colunas
        if not coluna.nullable
        and not coluna.default
        and not coluna.identity
        and (coluna.generated or 'NEVER').upper() != 'ALWAYS'
        and coluna.nome not in inseriveis
    ]
    if obrigatorias_ausentes:
        raise MigrationError(
            f'{tabela}: colunas NOT NULL sem default ausentes na origem: '
            f'{obrigatorias_ausentes}'
        )

    identity_always = any(
        coluna.identity
        and coluna.identity.upper() == 'ALWAYS'
        and coluna.nome in inseriveis
        for coluna in colunas
    )

    ignoradas = sorted(origem - set(inseriveis))
    if ignoradas:
        logger.warning(
            '  Colunas da origem ignoradas (não existem no destino): %s',
            ignoradas,
        )

    return PlanoTabela(
        tabela=tabela,
        colunas=colunas,
        pk=pk,
        colunas_inseriveis=inseriveis,
        identity_always=identity_always,
    )


# ==================== CONVERSÃO DE TIPOS ====================
def _converter_dataframe(df: pd.DataFrame, plano: PlanoTabela) -> pd.DataFrame:
    """
    Converte as colunas de acordo com o tipo REAL da coluna no PostgreSQL.

    Observação: para colunas timestamptz, enviamos datetimes naive e
    configuramos o TimeZone da sessão (padrão America/Sao_Paulo), para
    que o PostgreSQL interprete os horários locais corretamente.
    """
    convertidas: dict[str, pd.Series] = {}

    for coluna in plano.colunas:
        if coluna.nome not in df.columns:
            continue

        serie = df[coluna.nome]
        tipo = coluna.data_type

        if tipo == 'boolean':
            convertidas[coluna.nome] = serie.map(_to_bool)

        elif tipo in ('timestamp with time zone', 'timestamp without time zone'):
            convertidas[coluna.nome] = pd.to_datetime(serie, errors='coerce')

        elif tipo == 'date':
            convertidas[coluna.nome] = (
                pd.to_datetime(serie, errors='coerce').dt.date
            )

        elif tipo in ('smallint', 'integer', 'bigint'):
            convertidas[coluna.nome] = (
                pd.to_numeric(serie, errors='coerce').astype('Int64')
            )

        elif tipo in ('numeric', 'real', 'double precision'):
            convertidas[coluna.nome] = pd.to_numeric(serie, errors='coerce')

        elif tipo in ('json', 'jsonb'):
            convertidas[coluna.nome] = serie.map(_to_json)

        elif tipo in (
            'text',
            'character varying',
            'character',
            'uuid',
            'inet',
            'cidr',
            'macaddr',
        ):
            convertidas[coluna.nome] = serie.map(_to_text)

        else:
            # Tipos não previstos (enum, array, bytea etc.): mantém o valor.
            convertidas[coluna.nome] = serie

    return pd.DataFrame(convertidas, index=df.index)


def _validar_obrigatorios(df: pd.DataFrame, plano: PlanoTabela) -> None:
    """Falha cedo se uma coluna NOT NULL inserível tiver valores nulos."""
    for coluna in plano.colunas:
        if coluna.nome not in plano.colunas_inseriveis:
            continue
        if coluna.nullable or coluna.identity:
            continue
        if (coluna.generated or 'NEVER').upper() == 'ALWAYS':
            continue

        nulos = int(df[coluna.nome].isna().sum())
        if nulos:
            raise MigrationError(
                f'{plano.tabela}.{coluna.nome}: {nulos} valores nulos, '
                'mas a coluna é NOT NULL no destino.'
            )


# ==================== INSERT ====================
def _sql_insert(plano: PlanoTabela) -> str:
    colunas = ', '.join(_quote_ident(c) for c in plano.colunas_inseriveis)
    placeholders = ', '.join(
        f':v{indice}' for indice in range(len(plano.colunas_inseriveis))
    )

    overriding = ' OVERRIDING SYSTEM VALUE' if plano.identity_always else ''

    # Só usa ON CONFLICT (pk) se TODAS as colunas da PK forem inseridas.
    if plano.pk and all(col in plano.colunas_inseriveis for col in plano.pk):
        conflito = (
            ' ON CONFLICT ('
            + ', '.join(_quote_ident(c) for c in plano.pk)
            + ') DO NOTHING'
        )
    else:
        conflito = ' ON CONFLICT DO NOTHING'

    return (
        f'INSERT INTO {_quote_ident(plano.tabela)} ({colunas})'
        f'{overriding} VALUES ({placeholders}){conflito}'
    )


def _registros(df: pd.DataFrame, colunas: list[str]) -> list[dict[str, Any]]:
    registros: list[dict[str, Any]] = []
    for linha in df[colunas].itertuples(index=False, name=None):
        registros.append({
            f'v{indice}': _to_python(valor)
            for indice, valor in enumerate(linha)
        })
    return registros


def _resetar_sequences(conn, schema: str, tabela: str, pk: list[str]) -> None:
    """
    Ajusta as sequences após inserir IDs explícitos.

    Sem isso, o próximo INSERT da aplicação pode falhar com
    "duplicate key value violates unique constraint".
    """
    tabela_qualificada = f'{schema}.{tabela}'

    for coluna in pk:
        try:
            sequencia = conn.execute(
                text('SELECT pg_get_serial_sequence(:tabela, :coluna)'),
                {'tabela': tabela_qualificada, 'coluna': coluna},
            ).scalar()
        except Exception:
            sequencia = None

        if not sequencia:
            continue

        maximo = conn.execute(
            text(
                f'SELECT MAX({_quote_ident(coluna)}) '
                f'FROM {_quote_ident(tabela)}'
            )
        ).scalar()

        if maximo is None:
            continue

        try:
            maximo_int = int(maximo)
            valor = max(maximo_int, 1)
            chamado = maximo_int > 0
        except (TypeError, ValueError):
            continue

        conn.execute(
            text(
                'SELECT setval(CAST(:sequencia AS regclass), :valor, :chamado)'
            ),
            {'sequencia': sequencia, 'valor': valor, 'chamado': chamado},
        )
        logger.info('  Sequence %s ajustada para %d', sequencia, valor)


# ==================== MIGRAÇÃO DE UMA TABELA ====================
def _migrar_tabela(
    engine: Engine,
    sqlite_conn: sqlite3.Connection,
    tabela: str,
    schema: str,
    batch_size: int,
    timezone: str,
    anonimizar: bool,
    dry_run: bool,
) -> int:
    logger.info('=' * 70)
    logger.info('TABELA: %s', tabela)

    df = _ler_tabela_sqlite(sqlite_conn, tabela)
    logger.info('  %d registros lidos do SQLite', len(df))

    if df.empty:
        logger.info('  Tabela vazia; pulando.')
        return 0

    if anonimizar:
        df = _anonimizar_dataframe(df, tabela)

    with engine.connect() as conn:
        if not _tabela_existe(conn, schema, tabela):
            raise MigrationError(
                f'{tabela}: tabela não existe no schema {schema!r} do Neon. '
                'O script não cria tabelas (regra: sem DROP/CREATE).'
            )

        plano = _montar_plano(conn, schema, tabela, list(df.columns))

    df_convertido = _converter_dataframe(df, plano)
    df_convertido = df_convertido[plano.colunas_inseriveis]

    _validar_obrigatorios(df_convertido, plano)

    if dry_run:
        logger.info(
            '  [dry-run] %d registros seriam processados.',
            len(df_convertido),
        )
        return 0

    sql_insert = _sql_insert(plano)

    with engine.begin() as conn:
        # Timezone da sessão: importante para colunas timestamptz.
        conn.execute(
            text("SELECT set_config('TimeZone', :timezone, false)"),
            {'timezone': timezone},
        )

        antes = conn.execute(
            text(f'SELECT COUNT(*) FROM {_quote_ident(tabela)}')
        ).scalar_one()

        total = len(df_convertido)
        for inicio in range(0, total, batch_size):
            lote = df_convertido.iloc[inicio:inicio + batch_size]
            registros = _registros(lote, plano.colunas_inseriveis)

            if not registros:
                continue

            conn.execute(text(sql_insert), registros)
            logger.info(
                '  Lote %d-%d de %d enviado',
                inicio + 1,
                min(inicio + batch_size, total),
                total,
            )

        depois = conn.execute(
            text(f'SELECT COUNT(*) FROM {_quote_ident(tabela)}')
        ).scalar_one()

        _resetar_sequences(conn, schema, tabela, plano.pk)

    inseridos = depois - antes
    logger.info(
        '  OK: %d registros processados, %d novos inseridos '
        '(%d já existiam).',
        total,
        inseridos,
        total - inseridos,
    )
    return inseridos


# ==================== MAIN ====================
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Migra dados do SQLite local para o Neon PostgreSQL '
                    'sem DROP/CREATE e com idempotência.'
    )
    parser.add_argument(
        '--sqlite',
        default=os.environ.get('SQLITE_PATH', str(SQLITE_PADRAO)),
        help='Caminho do tickets.db (default: dados/tickets.db).',
    )
    parser.add_argument(
        '--schema',
        default=os.environ.get('NEON_SCHEMA', SCHEMA_PADRAO),
        help='Schema do PostgreSQL (default: public).',
    )
    parser.add_argument(
        '--tables',
        default=None,
        help='Lista separada por vírgula. Default: todas as tabelas.',
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=int(os.environ.get('MIGRATION_BATCH_SIZE', BATCH_SIZE_PADRAO)),
        help=f'Tamanho do lote (default: {BATCH_SIZE_PADRAO}).',
    )
    parser.add_argument(
        '--timezone',
        default=os.environ.get('MIGRATION_TIMEZONE', TIMEZONE_PADRAO),
        help=f'TimeZone da sessão para timestamptz (default: {TIMEZONE_PADRAO}).',
    )
    parser.add_argument(
        '--no-anonimizar',
        action='store_true',
        help='Desativa a anonimização LGPD (NÃO recomendado).',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Lê e converte os dados, mas não insere nada.',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _carregar_env_local()
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

    if args.batch_size < 1:
        logger.error('--batch-size deve ser >= 1.')
        return 1

    url_bruta = os.environ.get('NEON_DATABASE_URL')
    if not url_bruta:
        url_bruta = os.environ.get('DATABASE_URL')
        if url_bruta:
            logger.warning(
                'NEON_DATABASE_URL não definida; usando DATABASE_URL '
                'como fallback.'
            )

    if not url_bruta:
        logger.error(
            'NEON_DATABASE_URL não definida. Configure a variável de '
            'ambiente (ou o .env) com a string de conexão do Neon.'
        )
        return 1

    try:
        url = _normalizar_url(url_bruta)
    except MigrationError as exc:
        logger.error('%s', exc)
        return 1

    logger.info('=' * 70)
    logger.info('MIGRAÇÃO SQLITE -> NEON POSTGRESQL')
    logger.info('=' * 70)
    logger.info('SQLite: %s', sqlite_path)
    logger.info('Neon:   %s', _url_mascarada(url))
    logger.info('Schema: %s', args.schema)
    logger.info('Lote:   %d', args.batch_size)
    logger.info('TZ:     %s', args.timezone)
    logger.info('Anonimizar: %s', not args.no_anonimizar)
    logger.info('Dry-run: %s', args.dry_run)

    engine = create_engine(
        url,
        poolclass=NullPool,
        connect_args={
            'connect_timeout': 20,
            'application_name': 'migracao_sqlite_neon',
        },
    )

    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        logger.info('Conexão com o Neon OK.')
    except Exception as exc:
        logger.error('Falha ao conectar no Neon: %s', exc)
        logger.error(
            'Dica: confirme a NEON_DATABASE_URL e se a porta 5432 está '
            'liberada na sua rede. Em redes que bloqueiam 5432, execute '
            'o script no Railway/GitHub Actions ou use o SQL Editor do Neon.'
        )
        engine.dispose()
        return 1

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.execute('PRAGMA query_only = ON')

    try:
        tabelas_sqlite = _listar_tabelas_sqlite(sqlite_conn)
        logger.info('Tabelas no SQLite: %s', tabelas_sqlite)

        if args.tables:
            tabelas = [
                tabela.strip()
                for tabela in args.tables.split(',')
                if tabela.strip()
            ]
        else:
            tabelas = [t for t in ORDEM_TABELAS if t in tabelas_sqlite]
            tabelas += [t for t in tabelas_sqlite if t not in tabelas]

        logger.info('Ordem de migração: %s', tabelas)

        total_inseridos = 0
        for tabela in tabelas:
            if tabela not in tabelas_sqlite:
                logger.warning(
                    'Tabela %s não existe no SQLite; pulando.', tabela
                )
                continue

            total_inseridos += _migrar_tabela(
                engine=engine,
                sqlite_conn=sqlite_conn,
                tabela=tabela,
                schema=args.schema,
                batch_size=args.batch_size,
                timezone=args.timezone,
                anonimizar=not args.no_anonimizar,
                dry_run=args.dry_run,
            )

        logger.info('=' * 70)
        if args.dry_run:
            logger.info('DRY-RUN concluído. Nenhum dado foi inserido.')
        else:
            logger.info(
                'CONCLUÍDO: %d novos registros inseridos no Neon.',
                total_inseridos,
            )
        logger.info('=' * 70)
        return 0

    except MigrationError as exc:
        logger.error('ERRO DE MIGRAÇÃO: %s', exc)
        return 1
    except KeyboardInterrupt:
        logger.warning('Interrompido pelo usuário.')
        return 130
    except Exception:
        logger.exception('Erro inesperado durante a migração.')
        return 1
    finally:
        sqlite_conn.close()
        engine.dispose()


if __name__ == '__main__':
    sys.exit(main())
