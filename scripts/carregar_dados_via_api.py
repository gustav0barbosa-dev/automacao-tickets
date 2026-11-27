#!/usr/bin/env python
# ============================================================
# scripts/carregar_dados_via_api.py
# ============================================================
"""
Carrega as tabelas do SQLite local para o Neon usando a Data API
(HTTP/HTTPS), contornando o bloqueio da porta 5432.

Fluxo:
    1. Login na Neon Auth (Better Auth) para obter o JWT.
    2. Para cada tabela (na ordem de FK), lê o SQLite, converte
       tipos e envia em lotes de 500 registros via POST na Data API.
    3. Usa Prefer: resolution=ignore-duplicates para idempotência.

Variáveis de ambiente necessárias:
    NEON_AUTH_URL          https://...neonauth.../neondb/auth
    NEON_DATA_API_URL      https://...apirest.../neondb/rest/v1
    NEON_ADMIN_EMAIL       e-mail do usuário admin no Neon Auth
    NEON_ADMIN_PASSWORD    senha desse usuário

Opcionais:
    NEON_DATABASE_URL / DATABASE_URL   não usadas aqui (apenas para o
                                       script de migração direta)
    SQLITE_PATH                        caminho do tickets.db
    BATCH_SIZE                         tamanho do lote (default 500)
    MIGRATION_TIMEZONE                 não usado (conversão para string)

Uso:
    python scripts/carregar_dados_via_api.py
    python scripts/carregar_dados_via_api.py --tables tickets,movimentacoes
    python scripts/carregar_dados_via_api.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
# Permite importar src/utils_anonimizacao.py mesmo quando o script é
# executado a partir de qualquer diretório.
if str(RAIZ / 'src') not in sys.path:
    sys.path.insert(0, str(RAIZ / 'src'))

SQLITE_PADRAO = RAIZ / 'dados' / 'tickets.db'

ORDEM_TABELAS = [
    'areas',
    'analistas',
    'tickets',
    'movimentacoes',
    'mensagens',
    'snapshots',
]
TABELAS_IGNORADAS = {'sqlite_sequence'}

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
}

COLUNAS_APENAS_DATA = {'snapshot_data'}

COLUNAS_INTEIRAS_CONHECIDAS = {
    'id', 'ticket_id', 'enriquecido', 'respondido', 'acao_interna',
    'pendente_usuario', 'backlog', 'dias_uteis_resolucao',
    'sla_criticidade_ok', 'meta_diaria', 'ativo',
    'primeira_acao_responsavel', 'tickets_total', 'tickets_novos',
    'tickets_atualizados', 'tickets_mudaram', 'tickets_enriquecidos',
    'peso_criticidade',
}

logger = logging.getLogger('carregar_dados_via_api')


class AuthExpiredError(RuntimeError):
    """Sinaliza que o JWT expirou (HTTP 401)."""


# ==================== .ENV ====================
def _carregar_env_local() -> None:
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


_carregar_env_local()


def _obter_config(nome: str) -> str | None:
    valor = os.environ.get(nome)
    if valor and valor.strip():
        return valor.strip()
    return None


# ==================== HELPERS ====================
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
    """Converte um valor do SQLite para algo serializável em JSON."""
    if _is_null(valor):
        return None

    nome = (coluna or '').lower()

    if nome in COLUNAS_INTEIRAS_CONHECIDAS:
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return valor
        if numero.is_integer():
            return int(numero)
        return numero

    if isinstance(valor, (dict, list)):
        return valor

    if isinstance(valor, (pd.Timestamp,)):
        if _eh_coluna_apenas_data(coluna):
            return valor.date().isoformat()
        return valor.strftime('%Y-%m-%d %H:%M:%S')

    if isinstance(valor, (np.integer,)):
        return int(valor)
    if isinstance(valor, (np.floating,)):
        v = float(valor)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(valor, (np.bool_,)):
        return bool(valor)
    if isinstance(valor, (np.ndarray,)):
        return valor.tolist()

    if isinstance(valor, str) and _eh_coluna_data(coluna):
        ts = pd.to_datetime(valor, errors='coerce', dayfirst=False)
        if pd.isna(ts):
            return valor
        if _eh_coluna_apenas_data(coluna):
            return ts.date().isoformat()
        return ts.strftime('%Y-%m-%d %H:%M:%S')

    if isinstance(valor, str):
        return valor.replace('\x00', '')

    return valor


def _converter_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Converte um DataFrame em lista de dicts JSON-serializáveis."""
    registros: list[dict[str, Any]] = []
    colunas = list(df.columns)
    for _, linha in df.iterrows():
        registro = {}
        for col in colunas:
            registro[col] = _converter_valor(col, linha[col])
        registros.append(registro)
    return registros


# ==================== INTROSPECÇÃO DO SCHEMA NO NEON ====================
def _colunas_via_openapi(data_api_url: str, tabela: str, jwt: str) -> list[str] | None:
    """
    Fallback para tabelas vazias: consulta o OpenAPI do PostgREST
    para descobrir as colunas existentes no Neon.
    """
    headers = {
        'Authorization': f'Bearer {jwt}',
        'Accept': 'application/json',
    }

    try:
        resposta = requests.get(data_api_url, headers=headers, timeout=30)
    except requests.exceptions.RequestException:
        return None

    if resposta.status_code != 200:
        return None

    try:
        spec = resposta.json()
    except ValueError:
        return None

    if not isinstance(spec, dict):
        return None

    # Swagger 2.0
    definitions = spec.get('definitions')
    if isinstance(definitions, dict) and tabela in definitions:
        props = definitions[tabela].get('properties')
        if isinstance(props, dict):
            return list(props.keys())

    # OpenAPI 3
    components = spec.get('components')
    if isinstance(components, dict):
        schemas = components.get('schemas')
        if isinstance(schemas, dict) and tabela in schemas:
            props = schemas[tabela].get('properties')
            if isinstance(props, dict):
                return list(props.keys())

    # Tenta resolver via $ref em paths.
    paths = spec.get('paths')
    if isinstance(paths, dict):
        for chave, valor in paths.items():
            if not isinstance(valor, dict):
                continue
            if tabela not in chave:
                continue
            get_info = valor.get('get')
            if not isinstance(get_info, dict):
                continue
            responses = get_info.get('responses', {})
            resp200 = responses.get('200', {})
            schema = resp200.get('schema', {})
            if isinstance(schema, dict):
                ref = schema.get('$ref') or schema.get('items', {}).get('$ref')
                if isinstance(ref, str) and ref.startswith('#/'):
                    partes = ref.lstrip('#/').split('/')
                    atual = spec
                    for parte in partes:
                        if isinstance(atual, dict) and parte in atual:
                            atual = atual[parte]
                        else:
                            atual = None
                            break
                    if isinstance(atual, dict) and 'properties' in atual:
                        return list(atual['properties'].keys())

    return None


def obter_colunas_neon(
    data_api_url: str,
    tabela: str,
    jwt: str,
) -> list[str] | None:
    """
    Descobre as colunas existentes no Neon para a tabela.

    Estratégia:
        1. GET {tabela}?select=*&limit=1
           - Se vier ao menos 1 linha, usa as chaves do JSON.
        2. Se a tabela estiver vazia, tenta o OpenAPI do PostgREST.
        3. Retorna None se não for possível descobrir.
    """
    headers = {
        'Authorization': f'Bearer {jwt}',
        'Accept': 'application/json',
    }
    url = f'{data_api_url}/{tabela}'

    try:
        resposta = requests.get(
            url,
            headers=headers,
            params={'select': '*', 'limit': 1},
            timeout=30,
        )
    except requests.exceptions.RequestException as exc:
        logger.warning('  Falha ao introspectar %s: %s', tabela, exc)
        return None

    if resposta.status_code == 401:
        raise AuthExpiredError('JWT expirado ao introspectar %s.' % tabela)
    if resposta.status_code != 200:
        logger.warning(
            '  Introspecção de %s retornou HTTP %d.', tabela, resposta.status_code
        )
        return None

    try:
        dados = resposta.json()
    except ValueError:
        dados = None

    if isinstance(dados, list) and dados and isinstance(dados[0], dict):
        return list(dados[0].keys())

    # Tabela vazia (ou resposta inesperada): tenta OpenAPI.
    colunas = _colunas_via_openapi(data_api_url, tabela, jwt)
    if colunas:
        logger.info(
            '  Tabela %s vazia no Neon; colunas obtidas via OpenAPI: %s',
            tabela, colunas,
        )
    return colunas


# ==================== AUTENTICAÇÃO NEON ====================
def _extrair_cookies_sessao(resposta: requests.Response) -> dict[str, str]:
    try:
        cookies = resposta.cookies.get_dict()
    except Exception:
        return {}
    if not cookies:
        return {}
    cookies_sessao = {
        nome: valor
        for nome, valor in cookies.items()
        if 'session' in nome.lower()
    }
    return cookies_sessao or cookies


def fazer_login(email: str, senha: str, auth_url: str) -> str:
    """
    Login em duas etapas (Better Auth) e retorna o JWT.
    """
    url_login = f'{auth_url}/sign-in/email'

    try:
        resposta = requests.post(
            url_login,
            json={'email': email, 'password': senha},
            timeout=30,
        )
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f'Falha de rede no login: {exc}') from exc

    if resposta.status_code in (400, 401, 403):
        raise RuntimeError('Credenciais de admin inválidas (HTTP %d).' % resposta.status_code)
    if resposta.status_code != 200:
        raise RuntimeError('Login retornou HTTP %d.' % resposta.status_code)

    # Alguns ambientes já retornam o JWT no login direto.
    jwt = resposta.headers.get('Set-Auth-Jwt')
    if jwt:
        return jwt

    cookies_sessao = _extrair_cookies_sessao(resposta)
    if not cookies_sessao:
        raise RuntimeError(
            'Login aceito, mas o cookie de sessão (better-auth.session_token) '
            'não foi retornado.'
        )

    try:
        resposta_sessao = requests.get(
            f'{auth_url}/get-session',
            cookies=cookies_sessao,
            headers={'Accept': 'application/json'},
            timeout=30,
        )
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f'Falha de rede ao validar a sessão: {exc}') from exc

    if resposta_sessao.status_code != 200:
        raise RuntimeError(
            'get-session retornou HTTP %d.' % resposta_sessao.status_code
        )

    jwt = resposta_sessao.headers.get('Set-Auth-Jwt')
    if not jwt:
        raise RuntimeError(
            'Sessão válida, mas o cabeçalho Set-Auth-Jwt não foi retornado. '
            'Verifique se o plugin JWT está habilitado na Neon Auth.'
        )
    return jwt


# ==================== ENVIO VIA DATA API ====================
def enviar_lote(
    data_api_url: str,
    tabela: str,
    lote: list[dict[str, Any]],
    jwt: str,
    tentativas: int = 3,
) -> tuple[bool, str]:
    """
    Envia um lote. Retorna (sucesso, erro).
    erro == 'AUTH_EXPIRED' indica que o JWT expirou.
    """
    url = f'{data_api_url}/{tabela}'
    headers = {
        'Authorization': f'Bearer {jwt}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=ignore-duplicates,return=minimal',
    }

    for tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.post(
                url,
                headers=headers,
                json=lote,
                timeout=120,
            )
        except requests.exceptions.RequestException as exc:
            if tentativa < tentativas:
                time.sleep(2 * tentativa)
                continue
            return False, f'Falha de rede: {exc}'

        if resposta.status_code in (200, 201, 204):
            return True, ''

        if resposta.status_code == 401:
            return False, 'AUTH_EXPIRED'

        # Retenta erros transitórios do servidor.
        if 500 <= resposta.status_code < 600 and tentativa < tentativas:
            time.sleep(2 * tentativa)
            continue

        detalhe = (resposta.text or '')[:300]
        return False, f'HTTP {resposta.status_code}: {detalhe}'

    return False, 'Falha de rede após retentativas.'


# ==================== MAIN ====================
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Carrega o SQLite local para o Neon via Data API (HTTP).'
    )
    parser.add_argument(
        '--sqlite',
        default=os.environ.get('SQLITE_PATH', str(SQLITE_PADRAO)),
        help=f'Caminho do tickets.db (default: {SQLITE_PADRAO}).',
    )
    parser.add_argument(
        '--tables',
        default=None,
        help='Lista separada por vírgula. Default: todas as tabelas.',
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=int(os.environ.get('BATCH_SIZE', 500)),
        help='Tamanho do lote (default: 500).',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Lê e converte os dados, mas não envia nada.',
    )
    parser.add_argument(
        '--anonimizar',
        action='store_true',
        help='Aplica anonimização LGPD antes do envio.',
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

    auth_url = _obter_config('NEON_AUTH_URL')
    data_api_url = _obter_config('NEON_DATA_API_URL')
    admin_email = _obter_config('NEON_ADMIN_EMAIL')
    admin_password = _obter_config('NEON_ADMIN_PASSWORD')

    faltando = []
    if not auth_url:
        faltando.append('NEON_AUTH_URL')
    if not data_api_url:
        faltando.append('NEON_DATA_API_URL')
    if not admin_email:
        faltando.append('NEON_ADMIN_EMAIL')
    if not admin_password:
        faltando.append('NEON_ADMIN_PASSWORD')

    if faltando:
        logger.error(
            'Variáveis de ambiente ausentes: %s', ', '.join(faltando)
        )
        logger.error(
            'Defina-as no .env ou no ambiente antes de executar o script.'
        )
        return 1

    auth_url = auth_url.rstrip('/')
    data_api_url = data_api_url.rstrip('/')

    sqlite_path = Path(args.sqlite).expanduser().resolve()
    if not sqlite_path.exists():
        logger.error('SQLite não encontrado: %s', sqlite_path)
        return 1

    if args.batch_size < 1:
        logger.error('--batch-size deve ser >= 1.')
        return 1

    # Login inicial.
    try:
        jwt = fazer_login(admin_email, admin_password, auth_url)
    except RuntimeError as exc:
        logger.error('Falha no login: %s', exc)
        return 1
    logger.info('Login OK. JWT obtido.')

    conn = sqlite3.connect(sqlite_path)
    conn.execute('PRAGMA query_only = ON')

    try:
        tabelas_sqlite = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            if r[0] not in TABELAS_IGNORADAS
        ]

        if args.tables:
            tabelas = [
                t.strip() for t in args.tables.split(',') if t.strip()
            ]
        else:
            tabelas = [t for t in ORDEM_TABELAS if t in tabelas_sqlite]
            tabelas += [t for t in tabelas_sqlite if t not in tabelas]

        tabelas = [t for t in tabelas if t in tabelas_sqlite]
        if not tabelas:
            logger.error('Nenhuma tabela válida para carregar.')
            return 1

        logger.info('Tabelas a carregar: %s', tabelas)
        logger.info('Lote: %d registros', args.batch_size)
        logger.info('Dry-run: %s', args.dry_run)

        total_enviado = 0

        for tabela in tabelas:
            logger.info('=' * 70)
            logger.info('TABELA: %s', tabela)

            df = pd.read_sql_query(
                f'SELECT * FROM "{tabela}"', conn
            )
            logger.info('  %d registros lidos do SQLite', len(df))

            if df.empty:
                logger.info('  Tabela vazia; pulando.')
                continue

            # Introspecção dinâmica: mantém apenas colunas que existem no Neon.
            try:
                colunas_neon = obter_colunas_neon(data_api_url, tabela, jwt)
            except AuthExpiredError:
                logger.warning(
                    '  JWT expirado ao introspectar %s; fazendo login novamente.',
                    tabela,
                )
                try:
                    jwt = fazer_login(admin_email, admin_password, auth_url)
                except RuntimeError as exc:
                    logger.error('  Re-login falhou: %s', exc)
                    return 1
                colunas_neon = obter_colunas_neon(data_api_url, tabela, jwt)

            if colunas_neon:
                extras = [c for c in df.columns if c not in colunas_neon]
                if extras:
                    logger.warning(
                        '  Colunas do SQLite ignoradas (não existem no Neon): %s',
                        extras,
                    )
                faltando = [c for c in colunas_neon if c not in df.columns]
                if faltando:
                    logger.warning(
                        '  Colunas do Neon ausentes no SQLite (serão NULL/default): %s',
                        faltando,
                    )
                colunas_comuns = [c for c in df.columns if c in colunas_neon]
                if not colunas_comuns:
                    logger.warning(
                        '  Nenhuma coluna em comum entre SQLite e Neon; pulando.'
                    )
                    continue
                df = df[colunas_comuns]
            else:
                logger.warning(
                    '  Não foi possível introspectar %s; enviando todas as '
                    'colunas do SQLite.', tabela,
                )

            if args.anonimizar:
                try:
                    from utils_anonimizacao import (
                        CAMPOS_POR_TABELA,
                        anonimizar_texto,
                    )
                except ImportError as exc:
                    logger.error(
                        'Não foi possível importar src/utils_anonimizacao.py: %s',
                        exc,
                    )
                    return 1

                campos = CAMPOS_POR_TABELA.get(tabela, [])
                for campo in campos:
                    if campo not in df.columns:
                        continue
                    logger.info('  Anonimizando %s.%s', tabela, campo)
                    df[campo] = df[campo].map(
                        lambda valor: (
                            valor if _is_null(valor) else anonimizar_texto(valor)
                        )
                    )

            registros = _converter_dataframe(df)
            total = len(registros)
            lotes = (total + args.batch_size - 1) // args.batch_size
            logger.info('  %d lotes de até %d registros', lotes, args.batch_size)

            if args.dry_run:
                logger.info('  [dry-run] nada enviado.')
                continue

            for indice, inicio in enumerate(
                range(0, total, args.batch_size), start=1
            ):
                lote = registros[inicio:inicio + args.batch_size]
                ok, erro = enviar_lote(data_api_url, tabela, lote, jwt)

                if erro == 'AUTH_EXPIRED':
                    logger.warning(
                        '  JWT expirado no lote %d/%d; fazendo login novamente.',
                        indice, lotes,
                    )
                    try:
                        jwt = fazer_login(admin_email, admin_password, auth_url)
                    except RuntimeError as exc:
                        logger.error('  Re-login falhou: %s', exc)
                        return 1
                    ok, erro = enviar_lote(data_api_url, tabela, lote, jwt)

                if not ok:
                    logger.error(
                        '  Falha no lote %d/%d: %s', indice, lotes, erro
                    )
                    return 1

                total_enviado += len(lote)
                logger.info(
                    '  Lote %d/%d OK (%d registros). Total enviado: %d',
                    indice, lotes, len(lote), total_enviado,
                )

        logger.info('=' * 70)
        if args.dry_run:
            logger.info('DRY-RUN concluído. Nenhum dado foi enviado.')
        else:
            logger.info('CONCLUÍDO: %d registros enviados.', total_enviado)
        logger.info('=' * 70)
        return 0

    except RuntimeError as exc:
        logger.error('ERRO: %s', exc)
        return 1
    except KeyboardInterrupt:
        logger.warning('Interrompido pelo usuário.')
        return 130
    except Exception:
        logger.exception('Erro inesperado durante a carga.')
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
