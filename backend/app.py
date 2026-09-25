# ============================================================
# backend/app.py — Backend de Upload para Neon PostgreSQL (v2)
# ============================================================
# Recebe CSVs via HTTP POST e insere no banco Neon.
# Roda no Railway (fora da rede SPPREV, sem bloqueios).
#
# SEGURANÇA:
#   - Exige header X-API-Key (configurada em env var API_KEY)
#   - Whitelist de tabelas e colunas
#   - Erros genéricos ao cliente (sem stacktrace)
#   - Log estruturado do erro real (server-side)
# ============================================================

import io
import logging
import os
from datetime import datetime
from functools import wraps

import pandas as pd
import psycopg2
from flask import Flask, jsonify, request

# ==================== CONFIG ====================
app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')
API_KEY = os.environ.get('API_KEY')  # ← CONFIGURAR NO RAILWAY
MAX_UPLOAD_MB = 100

app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

# Logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


# ==================== WHITELIST DE TABELAS ====================
# Só permite inserir/consultar estas tabelas
TABELAS_PERMITIDAS = {
    'tickets': {
        'id', 'titulo', 'descricao', 'categoria', 'subcategoria',
        'status', 'prioridade', 'responsavel_atual', 'solicitante',
        'criado_data', 'alterado_data', 'previsao',
        'data_resolvido', 'data_1_resolvido',
        'snapshot_data', 'enriquecido', 'criado_em', 'atualizado_em',
        'area', 'empresa', 'solucao', 'sistema', 'responsavel_empresa',
        'respondido', 'diagnostico', 'acao_interna', 'pendente_usuario',
        'backlog', 'classificacao', 'previsao_esperada',
        'dias_uteis_resolucao', 'sla_criticidade_ok', 'horas_resolucao',
        'peso_criticidade',
    },
    'movimentacoes': {
        'id', 'ticket_id', 'data_movimentacao', 'autor', 'tipo',
        'de_status', 'para_status', 'comentario', 'criado_em',
    },
    'mensagens': {
        'id', 'ticket_id', 'data_hora', 'autor', 'tipo',
        'area_origem', 'area_destino', 'analista_destino',
        'conteudo', 'primeira_acao_responsavel', 'criado_em',
    },
    'analistas': {
        'nome', 'email', 'area_principal', 'perfil', 'equipe',
        'meta_diaria', 'meta_sla', 'ativo', 'atualizado_em', 'empresa_tipo',
    },
    'snapshots': {
        'data_execucao', 'tickets_total', 'tickets_novos',
        'tickets_atualizados', 'tempo_execucao_seg', 'origem',
    },
    'areas': {
        'nome', 'sigla', 'responsavel',
    },
}

# Colunas que devem ser convertidas para INTEGER
COLUNAS_INT = {
    'id', 'ticket_id', 'enriquecido', 'respondido', 'acao_interna',
    'pendente_usuario', 'backlog', 'dias_uteis_resolucao',
    'sla_criticidade_ok', 'meta_diaria', 'ativo',
    'primeira_acao_responsavel', 'tickets_total', 'tickets_novos',
    'tickets_atualizados', 'tickets_mudaram', 'tickets_enriquecidos',
    'peso_criticidade',
}


# ==================== AUTENTICAÇÃO ====================
def requer_api_key(f):
    """Decorator que exige X-API-Key válido."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not API_KEY:
            logger.error('API_KEY não configurada no servidor!')
            return jsonify({'erro': 'Servidor não configurado'}), 500

        chave_recebida = request.headers.get('X-API-Key', '')
        if chave_recebida != API_KEY:
            logger.warning(
                f'Tentativa de acesso não autorizado de {request.remote_addr}'
            )
            return jsonify({'erro': 'Não autorizado'}), 401

        return f(*args, **kwargs)
    return wrapper


# ==================== BANCO ====================
def conectar_banco():
    """Conecta ao PostgreSQL do Neon."""
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL não configurada')

    url = DATABASE_URL.replace('&channel_binding=require', '')
    return psycopg2.connect(url)


# ==================== ENDPOINTS PÚBLICOS ====================
@app.route('/')
def index():
    """Health check simples (sem auth)."""
    return jsonify({
        'status': 'ok',
        'servico': 'Help360 Upload Backend',
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/health')
def health():
    """Health check com verificação do banco (sem auth)."""
    try:
        conn = conectar_banco()
        conn.close()
        return jsonify({'status': 'healthy', 'db': 'connected'})
    except Exception as e:
        logger.error(f'Health check falhou: {e}')
        return jsonify({'status': 'unhealthy'}), 500


# ==================== ENDPOINTS AUTENTICADOS ====================
@app.route('/upload', methods=['POST'])
@requer_api_key
def upload():
    """
    Recebe um CSV via multipart/form-data e insere na tabela especificada.

    Requer:
        - Header: X-API-Key: <chave>
        - Form: file (CSV), tabela (nome da tabela)
    """
    try:
        # 1. Valida arquivo
        if 'file' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['file']
        if not arquivo.filename:
            return jsonify({'erro': 'Nome do arquivo vazio'}), 400

        # 2. Valida tabela (whitelist)
        tabela = request.form.get('tabela', '').strip().lower()
        if not tabela:
            return jsonify({'erro': 'Parâmetro "tabela" é obrigatório'}), 400

        if tabela not in TABELAS_PERMITIDAS:
            logger.warning(f'Tentativa de acesso a tabela não permitida: {tabela}')
            return jsonify({'erro': 'Tabela não permitida'}), 400

        colunas_permitidas = TABELAS_PERMITIDAS[tabela]

        # 3. Lê CSV
        conteudo = arquivo.read()
        try:
            df = pd.read_csv(io.BytesIO(conteudo))
        except Exception:
            return jsonify({'erro': 'CSV inválido'}), 400

        total_linhas = len(df)
        if total_linhas == 0:
            return jsonify({'erro': 'CSV vazio'}), 400

        # 4. Valida colunas (whitelist)
        colunas_csv = set(df.columns)
        colunas_invalidas = colunas_csv - colunas_permitidas
        if colunas_invalidas:
            logger.warning(f'Colunas inválidas em {tabela}: {colunas_invalidas}')
            return jsonify({
                'erro': 'Colunas inválidas no CSV',
                'colunas_invalidas': sorted(colunas_invalidas),
            }), 400

        # 5. Converte tipos
        for col in df.columns:
            if 'data' in col.lower() or 'previsao' in col.lower():
                df[col] = pd.to_datetime(df[col], errors='coerce')
            if col in COLUNAS_INT:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

        df = df.where(pd.notna(df), None)

        # 6. Insere no banco
        conn = conectar_banco()
        cursor = conn.cursor()

        # Colunas ordenadas (evita problema se o CSV vier fora de ordem)
        colunas_ord = [c for c in df.columns if c in colunas_permitidas]
        df = df[colunas_ord]

        colunas_sql = ','.join(colunas_ord)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False, header=False, na_rep='')
        buffer.seek(0)

        # Aqui é seguro: tabela e colunas já passaram pela whitelist
        sql = (
            f"COPY {tabela} ({colunas_sql}) "
            f"FROM STDIN WITH (FORMAT csv, HEADER false, NULL '')"
        )
        cursor.copy_expert(sql, buffer)

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f'Upload OK: {tabela} ({total_linhas} linhas)')

        return jsonify({
            'status': 'ok',
            'tabela': tabela,
            'linhas_inseridas': total_linhas,
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        # Loga o erro real (server-side) mas NÃO vaza pro cliente
        logger.exception(f'Erro no upload: {type(e).__name__}')
        return jsonify({
            'erro': 'Erro interno ao processar upload',
            'timestamp': datetime.now().isoformat(),
        }), 500


@app.route('/status')
@requer_api_key
def status():
    """Retorna contagem de registros por tabela (autenticado)."""
    try:
        conn = conectar_banco()
        cursor = conn.cursor()

        resultado = {}
        for t in TABELAS_PERMITIDAS:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {t}')
                resultado[t] = cursor.fetchone()[0]
            except Exception:
                resultado[t] = 'tabela não existe'

        cursor.close()
        conn.close()
        return jsonify(resultado)

    except Exception as e:
        logger.exception('Erro no /status')
        return jsonify({'erro': 'Erro interno'}), 500

# ==================== ENDPOINT /atualizar ====================
@app.route('/atualizar', methods=['POST'])
@requer_api_key
def atualizar():
    """
    Recebe o tickets.db.gz, descompacta, roda migração pro Postgres.

    Requer:
        - Header: X-API-Key
        - Body: multipart/form-data com 'file'
    """
    import gzip
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    if 'file' not in request.files:
        return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

    arquivo = request.files['file']
    if not arquivo.filename:
        return jsonify({'erro': 'Nome do arquivo vazio'}), 400

    logger.info(f'Recebendo upload: {arquivo.filename}')

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        gz_path = tmpdir / 'tickets.db.gz'
        db_path = tmpdir / 'tickets.db'

        # 1. Salva o .gz
        arquivo.save(str(gz_path))
        logger.info(f'  .gz: {gz_path.stat().st_size / 1e6:.1f} MB')

        # 2. Descompacta
        try:
            with gzip.open(gz_path, 'rb') as f_in:
                with open(db_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            logger.info(f'  .db: {db_path.stat().st_size / 1e6:.1f} MB')
        except Exception:
            logger.exception('Erro ao descompactar')
            return jsonify({'erro': 'Falha ao descompactar'}), 500

        # 3. Copia pro local esperado
        dados_dir = Path('/app/dados')
        dados_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_path, dados_dir / 'tickets.db')

        # 4. Roda migração
        script = Path('/app/migrar_sqlite_para_postgres.py')
        if not script.exists():
            logger.error(f'Script não encontrado: {script}')
            return jsonify({'erro': 'Script de migração não encontrado'}), 500

        try:
            resultado = subprocess.run(
                ['python', str(script)],
                cwd='/app',
                capture_output=True,
                text=True,
                timeout=600,  # 10 min
                env={**os.environ, 'SKIP_CONFIRM': '1'},
            )

            if resultado.returncode != 0:
                logger.error(f'Migração falhou: {resultado.stderr}')
                return jsonify({
                    'erro': 'Falha na migração',
                    'returncode': resultado.returncode,
                    'log': (resultado.stdout or '')[-2000:],
                    'stderr': (resultado.stderr or '')[-1000:],
                }), 500

            logger.info('Migração concluída com sucesso')
            return jsonify({
                'status': 'ok',
                'mensagem': 'Banco atualizado com sucesso',
                'log': (resultado.stdout or '')[-2000:],
                'timestamp': datetime.now().isoformat(),
            })

        except subprocess.TimeoutExpired:
            return jsonify({'erro': 'Timeout (>10 min)'}), 500
        except Exception:
            logger.exception('Erro inesperado na migração')
            return jsonify({'erro': 'Erro interno'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)