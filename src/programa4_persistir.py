# ============================================================
# programa4_persistir.py
# ============================================================
"""
Programa 4 — Persistência no SQLite.

Lê o arquivo 'tickets.xlsx' (base completa de 5 anos, baixada pelo
Programa1) e persiste no banco de dados SQLite.

- Cria o banco e as tabelas se não existirem (executa schema.sql)
- Faz backup do banco antes de cada escrita
- FILTRA tickets da Atlantic Solutions (empresa excluída)
- Faz UPSERT (insert ou update) dos tickets por ID
- Registra um snapshot da execução
- Não gera arquivos intermediários (só escrita no banco)
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from utils_anonimizacao import anonimizar_texto

import pandas as pd


# ==================== CAMINHOS ====================
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ_PROJETO / 'dados'
PASTA_LOGS = PASTA_DADOS / 'logs'
PASTA_BACKUP = PASTA_DADOS / 'backup'
CAMINHO_BANCO = PASTA_DADOS / 'tickets.db'
CAMINHO_SCHEMA = PASTA_DADOS / 'schema.sql'
PASTA_DOWNLOADS = Path(os.path.expanduser('~')) / 'Downloads'
CAMINHO_TICKETS = PASTA_DOWNLOADS / 'tickets.xlsx'


# ==================== EMPRESAS EXCLUÍDAS ====================
EMPRESAS_EXCLUIDAS = ['Atlantic Solutions', 'Atlantic', 'ATLANTIC']


# ==================== LOG ====================
def log(mensagem):
    """Imprime com timestamp e salva em log."""
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linha = f'[{agora}] {mensagem}'
    print(linha)

    PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    arquivo_log = PASTA_LOGS / f'programa4_{datetime.now():%Y-%m-%d}.log'
    with open(arquivo_log, 'a', encoding='utf-8') as f:
        f.write(linha + '\n')


# ==================== CONEXÃO ====================
def conectar() -> sqlite3.Connection:
    """Conecta ao banco SQLite (cria se não existir)."""
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def executar_schema(conn):
    """Executa o schema.sql para garantir que as tabelas existam."""
    if not CAMINHO_SCHEMA.exists():
        log(f'❌ Schema não encontrado: {CAMINHO_SCHEMA}')
        raise FileNotFoundError(f'schema.sql não encontrado em {CAMINHO_SCHEMA}')

    with open(CAMINHO_SCHEMA, 'r', encoding='utf-8') as f:
        sql = f.read()

    conn.executescript(sql)
    conn.commit()


# ==================== BACKUP ====================
def fazer_backup():
    """Copia o banco atual para dados/backup/ antes de alterá-lo."""
    if not CAMINHO_BANCO.exists():
        return None

    PASTA_BACKUP.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = PASTA_BACKUP / f'tickets_{timestamp}.db'
    shutil.copy2(CAMINHO_BANCO, destino)
    log(f'💾 Backup: {destino.name}')
    return destino


# ==================== LEITURA ====================
def carregar_tickets() -> pd.DataFrame:
    """Carrega 'tickets.xlsx' da pasta Downloads."""
    if not CAMINHO_TICKETS.exists():
        raise FileNotFoundError(
            f'Arquivo não encontrado: {CAMINHO_TICKETS}\n'
            f'   Execute o Programa1 primeiro.'
        )

    log(f'📂 Lendo: {CAMINHO_TICKETS}')
    df = pd.read_excel(CAMINHO_TICKETS)
    log(f'   Total: {len(df)} linhas, {len(df.columns)} colunas')

    # Normaliza colunas esperadas
    df.columns = [str(c).strip() for c in df.columns]

    return df


# ==================== FILTRO DE EMPRESAS ====================
def filtrar_empresas_excluidas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove tickets de empresas excluídas (Atlantic Solutions).

    Estratégia:
        1. Tenta filtrar pela coluna 'empresa' (case-insensitive)
        2. Se não existir, tenta pela coluna 'Empresa'
        3. Se não existir, pula o filtro com aviso
    """
    # Procura a coluna de empresa (case-insensitive)
    coluna_empresa = None
    for col in df.columns:
        if col.lower() == 'empresa':
            coluna_empresa = col
            break

    if coluna_empresa is None:
        log('⚠️  Coluna "empresa" não encontrada — filtro da Atlantic pulado')
        log(f'   Colunas disponíveis: {df.columns.tolist()}')
        return df

    # Conta quantos serão removidos
    mask = df[coluna_empresa].isin(EMPRESAS_EXCLUIDAS)
    n_removidos = int(mask.sum())

    if n_removidos > 0:
        log(f'🚫 Removendo {n_removidos} tickets da Atlantic Solutions...')
        # Log dos IDs removidos (útil pra auditoria)
        ids_removidos = df.loc[mask, 'ID'].tolist() if 'ID' in df.columns else []
        if ids_removidos:
            log(f'   IDs removidos: {ids_removidos[:10]}{"..." if len(ids_removidos) > 10 else ""}')
        df = df[~mask].copy()
    else:
        log('✅ Nenhum ticket da Atlantic Solutions encontrado')

    return df


# ==================== TRANSFORMAÇÃO ====================
def preparar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza tipos e nomes de colunas para o banco."""
    colunas_esperadas = {
        'ID':                    'id',
        'Título':                'titulo',
        'Titulo':                'titulo',
        'Descrição':             'descricao',
        'Descricao':             'descricao',
        'Categoria':             'categoria',
        'Subcategoria':          'subcategoria',
        'Status':                'status',
        'Prioridade':            'prioridade',
        'Responsável':           'responsavel_atual',
        'Responsavel':           'responsavel_atual',
        'Solicitante':           'solicitante',
        'Criado Data':           'criado_data',
        'Alterado Data':         'alterado_data',
        'Previsão':              'previsao',
        'Previsao':              'previsao',
        'Data do Resolvido':     'data_resolvido',
        'Data do 1°resolvido':   'data_1_resolvido',
    }

    # Renomeia
    df = df.rename(columns=colunas_esperadas)

    # Só mantém colunas que existem no banco
    colunas_banco = [
        'id', 'titulo', 'descricao', 'categoria', 'subcategoria',
        'status', 'prioridade', 'responsavel_atual', 'solicitante',
        'criado_data', 'alterado_data', 'previsao',
        'data_resolvido', 'data_1_resolvido',
    ]
    for col in colunas_banco:
        if col not in df.columns:
            df[col] = None

    df = df[colunas_banco].copy()

    # Normaliza ID para inteiro
    df['id'] = pd.to_numeric(df['id'], errors='coerce').astype('Int64')

    # Datas → ISO string (SQLite prefere string)
    colunas_data = [
        'criado_data', 'alterado_data', 'previsao',
        'data_resolvido', 'data_1_resolvido',
    ]
    for col in colunas_data:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
        df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Snapshot = hoje
    df['snapshot_data'] = datetime.now().strftime('%Y-%m-%d')

    # Enriquecido = 0 (Fase 2 vai atualizar)
    df['enriquecido'] = 0

    # Remove linhas sem ID
    df = df.dropna(subset=['id'])

    return df


# ==================== PERSISTÊNCIA ====================
def persistir_tickets(conn, df: pd.DataFrame) -> dict:
    """
    Faz UPSERT dos tickets no banco.
    Retorna estatísticas: {novos, atualizados, total}
    """
    cursor = conn.cursor()

    # Descobre quais IDs já existem
    cursor.execute('SELECT id FROM tickets')
    ids_existentes = {row[0] for row in cursor.fetchall()}

    novos = 0
    atualizados = 0

    sql = """
    INSERT INTO tickets (
        id, titulo, descricao, categoria, subcategoria,
        status, prioridade, responsavel_atual, solicitante,
        criado_data, alterado_data, previsao,
        data_resolvido, data_1_resolvido,
        snapshot_data, enriquecido, atualizado_em
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(id) DO UPDATE SET
        titulo              = excluded.titulo,
        descricao           = excluded.descricao,
        categoria           = excluded.categoria,
        subcategoria        = excluded.subcategoria,
        status              = excluded.status,
        prioridade          = excluded.prioridade,
        responsavel_atual   = excluded.responsavel_atual,
        solicitante         = excluded.solicitante,
        criado_data         = excluded.criado_data,
        alterado_data       = excluded.alterado_data,
        previsao            = excluded.previsao,
        data_resolvido      = excluded.data_resolvido,
        data_1_resolvido    = excluded.data_1_resolvido,
        snapshot_data       = excluded.snapshot_data,
        atualizado_em       = CURRENT_TIMESTAMP
    """

    # ==================== ANONIMIZAÇÃO LGPD ====================
    # Só anonimiza campos de TEXTO LIVRE (contêm dados de beneficiários).
    # NÃO anonimiza 'solicitante' nem 'responsavel_atual' (analistas internos).
    CAMPOS_ANONIMIZAR = ['titulo', 'descricao', 'solucao', 'diagnostico']

    for campo in CAMPOS_ANONIMIZAR:
        if campo in df.columns:
            df[campo] = df[campo].apply(
                lambda x: anonimizar_texto(x) if pd.notna(x) else x
            )

    for _, row in df.iterrows():
        valores = (
            int(row['id']) if pd.notna(row['id']) else None,
            row['titulo'],
            row['descricao'],
            row['categoria'],
            row['subcategoria'],
            row['status'],
            row['prioridade'],
            row['responsavel_atual'],
            row['solicitante'],
            row['criado_data'],
            row['alterado_data'],
            row['previsao'],
            row['data_resolvido'],
            row['data_1_resolvido'],
            row['snapshot_data'],
            int(row['enriquecido']),
        )
        cursor.execute(sql, valores)

        if row['id'] in ids_existentes:
            atualizados += 1
        else:
            novos += 1

    conn.commit()

    return {
        'novos': novos,
        'atualizados': atualizados,
        'total': len(df),
    }


def registrar_snapshot(conn, stats: dict, tempo_execucao: float):
    """Registra a execução na tabela snapshots."""
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM tickets')
    total = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO snapshots (
            data_execucao, tickets_total, tickets_novos,
            tickets_atualizados, tempo_execucao_seg, origem
        ) VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
    """, (
        total,
        stats['novos'],
        stats['atualizados'],
        round(tempo_execucao, 2),
        'programa4_persistir',
    ))
    conn.commit()


# ==================== MAIN ====================
def main():
    inicio = datetime.now()

    print('=' * 60)
    print('PROGRAMA 4 — PERSISTÊNCIA EM SQLITE')
    print('=' * 60)
    print(f'📁 Banco  : {CAMINHO_BANCO}')
    print(f'📁 Schema : {CAMINHO_SCHEMA}')
    print(f'📂 Origem : {CAMINHO_TICKETS}')
    print()

    try:
        # 1. Backup (se o banco já existir)
        fazer_backup()

        # 2. Conectar + schema
        log('🔌 Conectando ao banco...')
        conn = conectar()
        log('📋 Aplicando schema...')
        executar_schema(conn)

        # 3. Ler tickets.xlsx
        df = carregar_tickets()

        # 4. FILTRAR empresas excluídas (Atlantic) ← NOVO
        log('🚫 Filtrando empresas excluídas...')
        df = filtrar_empresas_excluidas(df)
        log(f'   Total após filtro: {len(df)} linhas')

        # 5. Preparar dados
        log('🔄 Preparando dados...')
        df = preparar_dataframe(df)
        log(f'   Linhas válidas: {len(df)}')

        # 6. Persistir
        log('💾 Persistindo no banco...')
        stats = persistir_tickets(conn, df)
        log(f'   ✅ Novos      : {stats["novos"]}')
        log(f'   ✅ Atualizados: {stats["atualizados"]}')
        log(f'   ✅ Total      : {stats["total"]}')

        # 7. Snapshot
        tempo = (datetime.now() - inicio).total_seconds()
        registrar_snapshot(conn, stats, tempo)
        log(f'📸 Snapshot registrado ({tempo:.1f}s)')

        # 8. Fecha
        conn.close()

        print()
        print('=' * 60)
        print('✅ PERSISTÊNCIA CONCLUÍDA')
        print('=' * 60)
        print(f'📊 Banco    : {CAMINHO_BANCO}')
        print(f'   Tamanho  : {CAMINHO_BANCO.stat().st_size / 1024:.1f} KB')
        print(f'   Tickets  : {stats["total"]}')
        print(f'   Novos    : {stats["novos"]}')
        print(f'   Atualiz. : {stats["atualizados"]}')
        print()

        return True

    except FileNotFoundError as e:
        log(f'❌ {e}')
        return False
    except Exception as e:
        log(f'❌ Erro inesperado: {e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    sucesso = main()
    sys.exit(0 if sucesso else 1)