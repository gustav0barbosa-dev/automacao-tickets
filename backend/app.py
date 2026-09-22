# ============================================================
# app.py - Backend de Upload para Neon PostgreSQL
# ============================================================
# Recebe CSVs via HTTP POST e insere no banco Neon.
# Roda no Railway (fora da rede SPPREV, sem bloqueios).
# ============================================================

import os
import io
import psycopg2
import pandas as pd
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Lê a URL do PostgreSQL das variáveis de ambiente
DATABASE_URL = os.environ.get('DATABASE_URL')

# Tamanho máximo do upload (100 MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024


def conectar_banco():
    """Conecta ao PostgreSQL do Neon."""
    if not DATABASE_URL:
        raise Exception('DATABASE_URL não configurada')
    
    # Remove parâmetros problemáticos do Neon
    url = DATABASE_URL.replace('&channel_binding=require', '')
    
    return psycopg2.connect(url)


@app.route('/')
def index():
    """Endpoint de saúde."""
    return jsonify({
        'status': 'ok',
        'servico': 'Help360 Upload Backend',
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/health')
def health():
    """Health check para o Railway."""
    try:
        conn = conectar_banco()
        conn.close()
        return jsonify({'status': 'healthy', 'db': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload():
    """
    Recebe um CSV via multipart/form-data e insere na tabela especificada.
    """
    try:
        # 1. Validações
        if 'file' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['file']
        tabela = request.form.get('tabela')

        if not tabela:
            return jsonify({'erro': 'Parâmetro "tabela" é obrigatório'}), 400

        if arquivo.filename == '':
            return jsonify({'erro': 'Nome do arquivo vazio'}), 400

        # 2. Lê o CSV
        conteudo = arquivo.read()
        df = pd.read_csv(io.BytesIO(conteudo))
        total_linhas = len(df)

        if total_linhas == 0:
            return jsonify({'erro': 'CSV vazio'}), 400

        # 3. Converte datas
        for col in df.columns:
            if 'data' in col.lower() or 'previsao' in col.lower():
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # 4. Converte colunas inteiras (evita "0.0" em INTEGER)
        colunas_int = [
            'id', 'ticket_id', 'enriquecido', 'respondido', 'acao_interna',
            'pendente_usuario', 'backlog', 'dias_uteis_resolucao',
            'sla_criticidade_ok', 'meta_diaria', 'ativo',
            'primeira_acao_responsavel', 'tickets_total', 'tickets_novos',
            'tickets_atualizados', 'tickets_mudaram', 'tickets_enriquecidos',
        ]
        for col in df.columns:
            if col in colunas_int:
                # Converte para Int64 (aceita NULL) e depois para object
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

        # 5. Substitui NaN por None
        df = df.where(pd.notna(df), None)

        # 6. Insere no banco
        conn = conectar_banco()
        cursor = conn.cursor()

        colunas = ','.join(df.columns)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False, header=False, na_rep='')
        buffer.seek(0)

        sql = f"COPY {tabela} ({colunas}) FROM STDIN WITH (FORMAT csv, HEADER false, NULL '')"
        cursor.copy_expert(sql, buffer)

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'status': 'ok',
            'tabela': tabela,
            'linhas_inseridas': total_linhas,
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'erro': str(e),
            'tipo': type(e).__name__,
        }), 500


@app.route('/status')
def status():
    """Retorna contagem de registros por tabela."""
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        tabelas = ['tickets', 'movimentacoes', 'mensagens', 'analistas', 'snapshots']
        resultado = {}
        
        for t in tabelas:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {t}')
                resultado[t] = cursor.fetchone()[0]
            except Exception:
                resultado[t] = 'tabela não existe'
        
        cursor.close()
        conn.close()
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


if __name__ == '__main__':
    # Lê a PORT que o Railway injeta (padrão 5000 se não existir)
    port = int(os.environ.get('PORT', 5000))
    # IMPORTANTE: escutar em 0.0.0.0 para aceitar conexões externas
    app.run(host='0.0.0.0', port=port)