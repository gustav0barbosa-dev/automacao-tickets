# ============================================================
# tests/test_integracao.py
# ============================================================

import sqlite3
import pandas as pd
import pytest


def test_popular_analistas(banco_temporario):
    """Insere analistas e verifica."""
    conn = banco_temporario
    conn.execute("INSERT INTO analistas VALUES ('João', 'joao@sp.gov.br', 'SPPREV')")
    conn.execute("INSERT INTO analistas VALUES ('Maria', 'maria@atlanticsolutions.com.br', 'Atlantic')")
    conn.commit()

    total = conn.execute('SELECT COUNT(*) FROM analistas').fetchone()[0]
    assert total == 2

    spprev = conn.execute(
        "SELECT COUNT(*) FROM analistas WHERE empresa_tipo = 'SPPREV'"
    ).fetchone()[0]
    assert spprev == 1


def test_inserir_tickets(banco_temporario):
    """Insere tickets e verifica."""
    conn = banco_temporario
    conn.execute('''
        INSERT INTO tickets (id, titulo, status, responsavel_atual,
                              responsavel_empresa, backlog, respondido)
        VALUES (1, 'Ticket A', 'Em atendimento', 'João',
                'SPPREV', 0, 0)
    ''')
    conn.execute('''
        INSERT INTO tickets (id, titulo, status, responsavel_atual,
                              responsavel_empresa, backlog, respondido)
        VALUES (2, 'Ticket B', 'Aguardando confirmação do usuário', 'Maria',
                'Atlantic', 1, 1)
    ''')
    conn.commit()

    total = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
    assert total == 2

    spprev = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE responsavel_empresa = 'SPPREV'"
    ).fetchone()[0]
    assert spprev == 1

    em_backlog = conn.execute(
        'SELECT COUNT(*) FROM tickets WHERE backlog = 1'
    ).fetchone()[0]
    assert em_backlog == 1


def test_tickets_travados_spprev(banco_temporario):
    """Verifica a query de tickets travados."""
    conn = banco_temporario

    # Ticket travado (SPPREV, ação interna, sem backlog, > 3 dias)
    conn.execute('''
        INSERT INTO tickets (id, titulo, status, responsavel_atual,
                              criado_data, backlog, acao_interna,
                              responsavel_empresa, diagnostico)
        VALUES (1, 'Travado', 'Em atendimento', 'João',
                '2026-09-01', 0, 1, 'SPPREV', 'CEN-03')
    ''')

    # Atlantic (não gera alerta)
    conn.execute('''
        INSERT INTO tickets (id, titulo, status, responsavel_atual,
                              criado_data, backlog, acao_interna,
                              responsavel_empresa, diagnostico)
        VALUES (2, 'Atlantic OK', 'Em atendimento', 'Maria',
                '2026-09-01', 0, 1, 'Atlantic', 'CEN-10')
    ''')

    # Em backlog (não gera alerta)
    conn.execute('''
        INSERT INTO tickets (id, titulo, status, responsavel_atual,
                              criado_data, backlog, acao_interna,
                              responsavel_empresa, diagnostico)
        VALUES (3, 'Backlog', 'Em atendimento', 'Pedro',
                '2026-09-01', 1, 1, 'SPPREV', 'CEN-03')
    ''')

    conn.commit()

    # Query de travados
    query = '''
        SELECT COUNT(*) FROM tickets
        WHERE status = 'Em atendimento'
          AND responsavel_empresa = 'SPPREV'
          AND acao_interna = 1
          AND backlog = 0
    '''
    travados = conn.execute(query).fetchone()[0]
    assert travados == 1  # Só o ticket 1