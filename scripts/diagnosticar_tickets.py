# ============================================================
# diagnosticar_tickets.py (v2 — corrigido)
# ============================================================
"""
Aplica a matriz de verdade (12 cenários) para classificar cada
ticket cruzando com a tabela `analistas` para saber se
responsável e alterador são SPPREV ou Atlantic.
"""

import sqlite3
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'


def main():
    conn = sqlite3.connect(BANCO)

    # ---------- Mapa nome → empresa ----------
    mapa_empresa = dict(conn.execute('''
        SELECT nome, COALESCE(empresa_tipo, 'Externo')
        FROM analistas
    ''').fetchall())

    print(f'📊 {len(mapa_empresa)} analistas no mapa')

    # ---------- Busca dados ----------
    df = pd.read_sql('''
        SELECT id, solicitante, responsavel_atual, status
        FROM tickets
    ''', conn)

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

    # ---------- Classificação ----------
    def classificar(row):
        resp = row['responsavel_atual']
        alt = row['alterado_por']
        status = row['status']

        # Busca empresa no mapa; default Externo
        resp_emp = mapa_empresa.get(resp, 'Externo') if pd.notna(resp) else 'Externo'
        alt_emp = mapa_empresa.get(alt, 'Externo') if pd.notna(alt) else 'Externo'

        # Normaliza: SPPREV / Atlantic / Outro / Externo
        def tipo(e):
            if e == 'SPPREV':
                return 'SPPREV'
            if e == 'Atlantic':
                return 'Atlantic'
            return 'OUTRO'

        resp_t = tipo(resp_emp)
        alt_t = tipo(alt_emp)

        acao_interna = (resp == alt) if pd.notna(resp) and pd.notna(alt) else False
        pendente_usuario = (status == 'Aguardando confirmação do usuário')

        # ---------- Matriz de verdade ----------
        # CEN-01..06: responsável SPPREV
        # CEN-07..12: responsável Atlantic
        if resp_t == 'SPPREV':
            if pendente_usuario and alt_t == 'SPPREV':
                diag = 'CEN-01'
            elif pendente_usuario and alt_t == 'Atlantic':
                diag = 'CEN-02'
            elif status == 'Em atendimento' and alt_t == 'SPPREV':
                diag = 'CEN-03'
            elif status == 'Em atendimento' and alt_t == 'Atlantic':
                diag = 'CEN-04'
            elif status == 'Resolvido' and alt_t == 'SPPREV':
                diag = 'CEN-05'
            elif status == 'Resolvido' and alt_t == 'Atlantic':
                diag = 'CEN-06'
            else:
                diag = 'OUTRO'
        elif resp_t == 'Atlantic':
            if pendente_usuario and alt_t == 'SPPREV':
                diag = 'CEN-07'
            elif pendente_usuario and alt_t == 'Atlantic':
                diag = 'CEN-08'
            elif status == 'Em atendimento' and alt_t == 'SPPREV':
                diag = 'CEN-09'
            elif status == 'Em atendimento' and alt_t == 'Atlantic':
                diag = 'CEN-10'
            elif status == 'Resolvido' and alt_t == 'SPPREV':
                diag = 'CEN-11'
            elif status == 'Resolvido' and alt_t == 'Atlantic':
                diag = 'CEN-12'
            else:
                diag = 'OUTRO'
        else:
            diag = 'OUTRO'

        return acao_interna, pendente_usuario, diag

    resultados = []
    for _, row in df.iterrows():
        acao, pend, diag = classificar(row)
        resultados.append({
            'id': row['id'],
            'acao_interna': int(acao),
            'pendente_usuario': int(pend),
            'diagnostico': diag,
        })

    df_res = pd.DataFrame(resultados)

    # ---------- Atualiza em lote ----------
    print('💾 Atualizando banco...')
    conn.executemany('''
        UPDATE tickets
        SET acao_interna = ?, pendente_usuario = ?, diagnostico = ?
        WHERE id = ?
    ''', [
        (r['acao_interna'], r['pendente_usuario'], r['diagnostico'], r['id'])
        for _, r in df_res.iterrows()
    ])
    conn.commit()

    # ---------- Resumo ----------
    print()
    print('=' * 60)
    print('DISTRIBUIÇÃO DOS CENÁRIOS')
    print('=' * 60)
    for diag, qtd in df_res['diagnostico'].value_counts().sort_index().items():
        print(f'   {diag:<10} {qtd:>6}')

    print()
    print('=' * 60)
    print('RESUMO')
    print('=' * 60)
    total = len(df_res)
    internos = df_res['acao_interna'].sum()
    pendentes = df_res['pendente_usuario'].sum()
    print(f'   Total processado            : {total}')
    print(f'   Com ação interna (resp=mex) : {internos} ({internos/total*100:.1f}%)')
    print(f'   Pendentes com usuário       : {pendentes} ({pendentes/total*100:.1f}%)')

    conn.close()


if __name__ == '__main__':
    main()