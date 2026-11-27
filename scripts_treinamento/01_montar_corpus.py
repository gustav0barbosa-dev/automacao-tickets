# scripts_treinamento/01_montar_corpus.py
"""
Fase 1 — Montagem do corpus de texto por ticket.

Lê os tickets existentes no banco (SQLite local ou PostgreSQL via DATABASE_URL)
e constrói duas visões de texto por ticket:

  - VISÃO RETROSPECTIVA: título + descrição + todas as mensagens +
    solução + comentários das movimentações.
    Usado para mapear o histórico e gerar relatórios mensais (maior acurácia).

  - VISÃO TRIAGEM: só título + descrição + 1ª mensagem do solicitante.
    Usado para reclassificar no momento da abertura (menor acurácia, mas
    utilizável em tempo real).

Salva:
  - scripts_treinamento/artefatos/corpus_retrospectivo.parquet|csv
  - scripts_treinamento/artefatos/corpus_triagem.parquet|csv
  - scripts_treinamento/artefatos/relatorio_cobertura.txt

Não quebra nada do pipeline (src/, pipeline_completo.py) nem do dashboard.
Mudança aditiva.
"""

import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Força UTF-8 no stdout para evitar erro em terminais Windows (cp1252)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
from sqlalchemy import create_engine, text

RAIZ = Path(__file__).resolve().parent.parent
BANCO_SQLITE = RAIZ / 'dados' / 'tickets.db'
ARTEFATOS = RAIZ / 'scripts_treinamento' / 'artefatos'

# ==================== CONEXÃO ====================


def _obter_engine():
    """Tenta conectar ao banco em ordem de prioridade:
       1. Variável de ambiente DATABASE_URL (Railway/Neon/Postgres)
       2. SQLite local (dados/tickets.db) — fallback dev/testes
    Retorna (engine, modo) onde modo em {'postgres', 'sqlite'}.
    """
    import os
    url = os.environ.get('DATABASE_URL')
    if url:
        url = url.replace('&channel_binding=require', '')
        url = url.replace('?channel_binding=require&', '?')
        url = url.replace('?channel_binding=require', '')
        engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={'connect_timeout': 30, 'sslmode': 'require'},
        )
        return engine, 'postgres'

    if BANCO_SQLITE.exists():
        engine = create_engine(
            f'sqlite:///{BANCO_SQLITE}',
            connect_args={'check_same_thread': False},
        )
        return engine, 'sqlite'

    raise FileNotFoundError(
        f'Banco não encontrado: defina DATABASE_URL ou crie {BANCO_SQLITE}'
    )


# ==================== CARREGAMENTO ====================


def carregar_tickets(engine, modo):
    """Carrega a tabela tickets com as colunas úteis ao corpus."""
    cols = '''
        id, titulo, descricao, categoria, subcategoria, status,
        prioridade, solicitante, area, sistema, solucao,
        classificacao, diagnostico, criado_data, data_resolvido,
        horas_resolucao, enriquecido
    '''
    query = text(f'SELECT {cols} FROM tickets')
    df = pd.read_sql(query, engine)
    if not df.empty:
        df['id'] = pd.to_numeric(df['id'], errors='coerce').astype('Int64')
        for c in ['criado_data', 'data_resolvido']:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce')
    return df


def carregar_mensagens(engine, modo, ticket_ids):
    """Carrega mensagens (tipo='comentario') dos tickets informados."""
    if not ticket_ids:
        return pd.DataFrame()
    ids_str = ', '.join(str(int(i)) for i in ticket_ids)
    query = text(f'''
        SELECT ticket_id, conteudo, autor, tipo, data_hora
        FROM mensagens
        WHERE ticket_id IN ({ids_str})
        ORDER BY ticket_id, data_hora ASC
    ''')
    return pd.read_sql(query, engine)


def carregar_movimentacoes(engine, modo, ticket_ids):
    """Carrega comentários das movimentações dos tickets informados."""
    if not ticket_ids:
        return pd.DataFrame()
    ids_str = ', '.join(str(int(i)) for i in ticket_ids)
    query = text(f'''
        SELECT ticket_id, comentario, autor, data_movimentacao
        FROM movimentacoes
        WHERE ticket_id IN ({ids_str})
          AND comentario IS NOT NULL
        ORDER BY ticket_id, data_movimentacao ASC
    ''')
    return pd.read_sql(query, engine)


# ==================== MONTAGEM DO TEXTO ====================


def limpar_placeholders(texto):
    """Remove placeholders de anonimização que não agregam semântica."""
    if not isinstance(texto, str):
        return ''
    t = texto
    for ph in ['<NOME>', '<TELEFONE>', '<ARQUIVO>', '00000000000',
               '00000000000000', 'email@exemplo.com', '0000000000']:
        t = t.replace(ph, ' ')
    # Colapsa espaços múltiplos
    t = ' '.join(t.split())
    return t


def primeira_mensagem_solicitante(df_msgs):
    """Pega a 1ª mensagem de cada ticket (modo triagem)."""
    if df_msgs.empty:
        return pd.DataFrame(columns=['ticket_id', 'primeira_msg'])
    g = df_msgs.groupby('ticket_id').first().reset_index()
    return g[['ticket_id', 'conteudo']].rename(
        columns={'conteudo': 'primeira_msg'}
    )


def montar_corpus(df_tickets, df_msgs, df_movs, modo):
    """Monta o texto enriquecido por ticket conforme o modo."""
    df = df_tickets.copy()

    # Agrega mensagens por ticket
    if not df_msgs.empty:
        msgs_agg = (
            df_msgs.groupby('ticket_id')['conteudo']
            .apply(lambda s: ' | '.join(str(x) for x in s if pd.notna(x)))
            .reset_index()
            .rename(columns={'conteudo': 'texto_msgs'})
        )
        df = df.merge(msgs_agg, left_on='id', right_on='ticket_id', how='left')
        df['texto_msgs'] = df['texto_msgs'].fillna('')

        # 1ª mensagem para triagem
        primeira = primeira_mensagem_solicitante(df_msgs)
        df = df.merge(primeira, on='ticket_id', how='left')
        df['primeira_msg'] = df['primeira_msg'].fillna('')
    else:
        df['texto_msgs'] = ''
        df['primeira_msg'] = ''

    # Agrega comentários de movimentações por ticket
    if not df_movs.empty:
        movs_agg = (
            df_movs.groupby('ticket_id')['comentario']
            .apply(lambda s: ' | '.join(str(x) for x in s if pd.notna(x)))
            .reset_index()
            .rename(columns={'comentario': 'texto_movs'})
        )
        df = df.merge(movs_agg, left_on='id', right_on='ticket_id', how='left')
        df['texto_movs'] = df['texto_movs'].fillna('')
    else:
        df['texto_movs'] = ''

    # Preenche colunas de texto que podem ser nulas
    for c in ['titulo', 'descricao', 'solucao']:
        if c not in df.columns:
            df[c] = ''
        df[c] = df[c].fillna('').astype(str)

    # ===== VISÃO RETROSPECTIVA =====
    df['texto_retrospectivo'] = df.apply(
        lambda r: (
            f"{limpar_placeholders(r['titulo'])}. "
            f"{limpar_placeholders(r['descricao'])} "
            f"{limpar_placeholders(r['texto_msgs'])} "
            f"{limpar_placeholders(r['texto_movs'])} "
            f"{limpar_placeholders(r['solucao'])}"
        ).strip(),
        axis=1,
    )

    # ===== VISÃO TRIAGEM =====
    df['texto_triagem'] = df.apply(
        lambda r: (
            f"{limpar_placeholders(r['titulo'])}. "
            f"{limpar_placeholders(r['descricao'])} "
            f"{limpar_placeholders(r['primeira_msg'])}"
        ).strip(),
        axis=1,
    )

    return df


# ==================== AUDITORIA DE COBERTURA ====================


def texto_util(texto):
    """Considera texto útil se tiver mais de 10 caracteres após limpeza."""
    return isinstance(texto, str) and len(limpar_placeholders(texto)) > 10


def gerar_relatorio_cobertura(df, modo_coluna):
    """Gera métricas de cobertura de texto por categoria."""
    total = len(df)
    com_texto = df[modo_coluna].apply(texto_util).sum()
    print(f'\n{"=" * 70}')
    print(f'AUDITORIA DE COBERTURA — MODO {modo_coluna.upper()}')
    print(f'{"=" * 70}')
    print(f'Total de tickets: {total}')
    print(f'Com texto útil ({modo_coluna} > 10 chars): {com_texto} '
          f'({com_texto / total * 100:.1f}%)')
    print(f'Sem texto suficiente: {total - com_texto} '
          f'({(total - com_texto) / total * 100:.1f}%)')

    print('\nCobertura por categoria (top 15):')
    cat_texto = (
        df.assign(tem_texto=df[modo_coluna].apply(texto_util))
        .groupby('categoria')['tem_texto']
        .agg(['count', 'sum', 'mean'])
        .rename(columns={'count': 'total', 'sum': 'com_texto',
                         'mean': 'cobertura'})
        .sort_values('total', ascending=False)
        .head(15)
    )
    cat_texto['cobertura'] = (cat_texto['cobertura'] * 100).round(1)
    print(cat_texto.to_string())

    # Tamanho médio do texto útil
    tam_medio = (
        df.loc[df[modo_coluna].apply(texto_util), modo_coluna]
        .apply(lambda x: len(limpar_placeholders(x)))
        .mean()
    )
    print(f'\nTamanho médio do texto útil: {tam_medio:.0f} caracteres')

    # Tickets por mês (últimos 12 meses)
    if 'criado_data' in df.columns and df['criado_data'].notna().any():
        df_mes = df.dropna(subset=['criado_data']).copy()
        df_mes['mes'] = df_mes['criado_data'].dt.to_period('M')
        por_mes = df_mes.groupby('mes').size().sort_index().tail(12)
        print('\nTickets por mês (últimos 12):')
        for mes, qtd in por_mes.items():
            print(f'   {mes}: {qtd}')

    print(f'\n{"=" * 70}\n')
    return {
        'total': int(total),
        'com_texto': int(com_texto),
        'cobertura_pct': round(com_texto / total * 100, 2) if total else 0.0,
        'tamanho_medio': round(float(tam_medio), 2) if tam_medio else 0.0,
    }


# ==================== MAIN ====================


def main(modo='ambos'):
    engine, modo_banco = _obter_engine()
    print(f'📂 Conectado ao banco: {modo_banco}')

    df_tickets = carregar_tickets(engine, modo_banco)
    print(f'📊 Tickets carregados: {len(df_tickets)}')

    ticket_ids = df_tickets['id'].dropna().astype(int).tolist() if not df_tickets.empty else []
    df_msgs = carregar_mensagens(engine, modo_banco, ticket_ids)
    df_movs = carregar_movimentacoes(engine, modo_banco, ticket_ids)
    print(f'📨 Mensagens carregadas: {len(df_msgs)}')
    print(f'📝 Movimentações com comentário: {len(df_movs)}')

    ARTEFATOS.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    relatorios = {}

    if modo in ('retrospectivo', 'ambos'):
        df_retro = montar_corpus(df_tickets, df_msgs, df_movs, 'retrospectivo')
        caminho = ARTEFATOS / f'corpus_retrospectivo_{timestamp}.parquet'
        try:
            df_retro.to_parquet(caminho, index=False)
            print(f'💾 Corpus retrospectivo salvo: {caminho}')
        except Exception:
            caminho_csv = caminho.with_suffix('.csv')
            df_retro.to_csv(caminho_csv, index=False, encoding='utf-8')
            print(f'💾 Corpus retrospectivo salvo (CSV): {caminho_csv}')
            caminho = caminho_csv
        relatorios['retrospectivo'] = gerar_relatorio_cobertura(
            df_retro, 'texto_retrospectivo'
        )

    if modo in ('triagem', 'ambos'):
        df_triagem = montar_corpus(df_tickets, df_msgs, df_movs, 'triagem')
        caminho = ARTEFATOS / f'corpus_triagem_{timestamp}.parquet'
        try:
            df_triagem.to_parquet(caminho, index=False)
            print(f'💾 Corpus triagem salvo: {caminho}')
        except Exception:
            caminho_csv = caminho.with_suffix('.csv')
            df_triagem.to_csv(caminho_csv, index=False, encoding='utf-8')
            print(f'💾 Corpus triagem salvo (CSV): {caminho_csv}')
            caminho = caminho_csv
        relatorios['triagem'] = gerar_relatorio_cobertura(
            df_triagem, 'texto_triagem'
        )

    # Relatório consolidado
    relatorio_path = ARTEFATOS / f'relatorio_cobertura_{timestamp}.txt'
    with open(relatorio_path, 'w', encoding='utf-8') as f:
        f.write(f'Relatório de cobertura — {datetime.now().isoformat()}\n')
        for m, r in relatorios.items():
            f.write(f'\nModo {m}: {r}\n')
    print(f'📄 Relatório salvo: {relatorio_path}')
    print('\n✅ Fase 1 concluída.')


if __name__ == '__main__':
    import sys
    modo = sys.argv[1] if len(sys.argv) > 1 else 'ambos'
    if modo not in ('retrospectivo', 'triagem', 'ambos'):
        print('Uso: python 01_montar_corpus.py [retrospectivo|triagem|ambos]')
        sys.exit(1)
    main(modo)
