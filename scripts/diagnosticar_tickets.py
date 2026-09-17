# ============================================================
# diagnosticar_tickets.py
# ============================================================
"""
Aplica a matriz de verdade para classificar cada ticket em
um dos 12 cenários e define flags de ação.
"""

import sqlite3
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'


def classificar_cenario(solicitante, responsavel, alterado_por, status):
    """
    Retorna:
        - acao_interna (bool): True se Responsável == Alterado por
        - pendente_usuario (bool): True se status == Aguardando confirmação
        - diagnostico (str): código do cenário (CEN-01 a CEN-12)
    """
    acao_interna = (responsavel == alterado_por) if pd.notna(responsavel) and pd.notna(alterado_por) else False
    pendente_usuario = (status == 'Aguardando confirmação do usuário')

    # Mapeamento dos 12 cenários da sua planilha
    resp_spprev = (responsavel == 'Spprev')  # ajuste conforme seus dados
    resp_atlantic = (responsavel != 'Spprev')
    alter_spprev = (alterado_por == 'Spprev')
    alter_atlantic = (alterado_por != 'Spprev')

    if resp_spprev and alter_spprev and pendente_usuario:
        diag = 'CEN-01'
    elif resp_spprev and alter_atlantic and pendente_usuario:
        diag = 'CEN-02'
    elif resp_spprev and alter_spprev and status == 'Em atendimento':
        diag = 'CEN-03'
    elif resp_spprev and alter_atlantic and status == 'Em atendimento':
        diag = 'CEN-04'
    elif resp_spprev and alter_spprev and status == 'Resolvido':
        diag = 'CEN-05'
    elif resp_spprev and alter_atlantic and status == 'Resolvido':
        diag = 'CEN-06'
    elif resp_atlantic and alter_spprev and pendente_usuario:
        diag = 'CEN-07'
    elif resp_atlantic and alter_atlantic and pendente_usuario:
        diag = 'CEN-08'
    elif resp_atlantic and alter_spprev and status == 'Em atendimento':
        diag = 'CEN-09'
    elif resp_atlantic and alter_atlantic and status == 'Em atendimento':
        diag = 'CEN-10'
    elif resp_atlantic and alter_spprev and status == 'Resolvido':
        diag = 'CEN-11'
    elif resp_atlantic and alter_atlantic and status == 'Resolvido':
        diag = 'CEN-12'
    else:
        diag = 'OUTRO'

    return acao_interna, pendente_usuario, diag


def main():
    conn = sqlite3.connect(BANCO)

    # Pega responsável, status
    df = pd.read_sql('''
        SELECT id, solicitante, responsavel_atual, status
        FROM tickets
    ''', conn)

    # Pega "alterado por" da última movimentação
    df_movs = pd.read_sql('''
        SELECT ticket_id, autor, data_movimentacao
        FROM movimentacoes
        WHERE data_movimentacao IS NOT NULL
        ORDER BY ticket_id, data_movimentacao DESC
    ''', conn)

    df_movs_ultimo = df_movs.drop_duplicates('ticket_id', keep='first')

    df = df.merge(
        df_movs_ultimo[['ticket_id', 'autor']],
        left_on='id', right_on='ticket_id', how='left'
    )
    df = df.rename(columns={'autor': 'alterado_por'})
    df = df.drop(columns=['ticket_id'])

    print(f'📊 Processando {len(df)} tickets...')

    # Aplica classificação
    resultados = []
    for _, row in df.iterrows():
        acao_int, pend_user, diag = classificar_cenario(
            row['solicitante'],
            row['responsavel_atual'],
            row['alterado_por'],
            row['status'],
        )
        resultados.append({
            'id': row['id'],
            'acao_interna': int(acao_int),
            'pendente_usuario': int(pend_user),
            'diagnostico': diag,
        })

    df_res = pd.DataFrame(resultados)

    # Atualiza em lote
    for _, row in df_res.iterrows():
        conn.execute('''
            UPDATE tickets
            SET acao_interna = ?, pendente_usuario = ?, diagnostico = ?
            WHERE id = ?
        ''', (row['acao_interna'], row['pendente_usuario'], row['diagnostico'], row['id']))

    conn.commit()

    # Resumo
    print()
    print('📊 Distribuição dos cenários:')
    for diag, qtd in df_res['diagnostico'].value_counts().items():
        print(f'   {diag}: {qtd}')

    conn.close()


if __name__ == '__main__':
    main()