# ============================================================
# tests/conftest.py — Fixtures compartilhadas
# ============================================================

import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

# Adiciona src/ e dashboard/ ao path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / 'scripts'))


# ==================== BANCO TEMPORÁRIO ====================
@pytest.fixture
def banco_temporario(tmp_path):
    """
    Cria um banco SQLite temporário com o schema mínimo
    para testes.
    """
    caminho = tmp_path / 'test.db'
    conn = sqlite3.connect(caminho)

    # Schema mínimo
    conn.executescript('''
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY,
            titulo TEXT,
            categoria TEXT,
            status TEXT,
            responsavel_atual TEXT,
            solicitante TEXT,
            criado_data DATETIME,
            alterado_data DATETIME,
            previsao DATETIME,
            data_resolvido DATETIME,
            enriquecido INTEGER DEFAULT 0,
            backlog INTEGER DEFAULT 0,
            respondido INTEGER DEFAULT 0,
            responsavel_empresa TEXT,
            diagnostico TEXT,
            acao_interna INTEGER,
            pendente_usuario INTEGER
        );

        CREATE TABLE analistas (
            nome TEXT PRIMARY KEY,
            email TEXT,
            empresa_tipo TEXT
        );

        CREATE TABLE movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            data_movimentacao DATETIME,
            autor TEXT,
            tipo TEXT,
            para_status TEXT
        );

        CREATE TABLE mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            data_hora DATETIME,
            autor TEXT,
            conteudo TEXT
        );
    ''')
    conn.commit()

    yield conn

    conn.close()


# ==================== DATAFRAMES DE TESTE ====================
@pytest.fixture
def df_tickets_basico():
    """DataFrame com tickets de teste."""
    return pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'titulo': ['Ticket A', 'Ticket B', 'Ticket C', 'Ticket D', 'Ticket E'],
        'status': ['Em atendimento', 'Resolvido', 'Aguardando confirmação do usuário',
                   'Fechado', 'Em atendimento'],
        'responsavel_atual': ['João SPPREV', 'Maria Atlantic', 'Pedro SPPREV',
                               'Ana Atlantic', 'João SPPREV'],
        'solicitante': ['User1', 'User2', 'User3', 'User4', 'User5'],
        'criado_data': pd.to_datetime(['2026-09-01', '2026-09-02', '2026-09-03',
                                         '2026-09-04', '2026-09-05']),
        'alterado_data': pd.to_datetime(['2026-09-10', '2026-09-08', '2026-09-09',
                                           '2026-09-06', '2026-09-12']),
        'previsao': pd.to_datetime(['2026-09-15', '2026-09-10', '2026-09-20',
                                      '2026-09-10', '2026-09-18']),
        'data_resolvido': pd.to_datetime([None, '2026-09-08', None,
                                            '2026-09-05', None]),
        'backlog': [0, 0, 1, 0, 0],
        'respondido': [0, 1, 0, 1, 0],
        'responsavel_empresa': ['SPPREV', 'Atlantic', 'SPPREV', 'Atlantic', 'SPPREV'],
        'acao_interna': [1, 1, 1, 1, 0],
        'pendente_usuario': [0, 0, 1, 0, 0],
        'diagnostico': ['CEN-03', 'CEN-12', 'CEN-01', 'OUTRO', 'CEN-04'],
    })


@pytest.fixture
def df_analistas():
    """DataFrame com analistas de teste."""
    return pd.DataFrame({
        'Usuário': ['João SPPREV', 'Maria Atlantic', 'Pedro SPPREV'],
        'email': ['joao@sp.gov.br', 'maria@atlanticsolutions.com.br', 'pedro@sp.gov.br'],
        'Empresa': ['SPPREV', 'Atlantic', 'SPPREV'],
    })