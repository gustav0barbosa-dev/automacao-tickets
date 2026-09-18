# ============================================================
# analisar_sla_criticidade.py
# ============================================================
"""
Analisa o cumprimento do SLA de acordo com a criticidade do ticket.

Regra:
    Urgente      → 3 dias úteis
    Alta         → 5 dias úteis
    Média 1, 2   → 10 dias úteis
    Baixa 1, 2   → 15 dias úteis

Adiciona 3 colunas em tickets:
    - previsao_esperada (data calculada)
    - dias_uteis_resolucao (dias úteis até resolver)
    - sla_criticidade_ok (1=cumprido, 0=estourado, NULL=sem criticidade)
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

# Adiciona src/ ao path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))

from utils_sla import (
    prazo_por_criticidade, previsao_esperada,
    contar_dias_uteis, adicionar_dias_uteis,
)


BANCO = RAIZ / 'dados' / 'tickets.db'


def analisar(conn):
    """Analisa SLA por criticidade e atualiza o banco."""

    # Carrega tickets abertos e resolvidos
    df = pd.read_sql('''
        SELECT id, prioridade, criado_data, data_resolvido, status
        FROM tickets
        WHERE prioridade IS NOT NULL
    ''', conn)

    print(f'📊 {len(df)} tickets para analisar')

    # Converte datas
    df['criado_data'] = pd.to_datetime(df['criado_data'], errors='coerce')
    df['data_resolvido'] = pd.to_datetime(df['data_resolvido'], errors='coerce')

    resultados = []
    com_prazo = 0
    sem_prazo = 0

    for _, row in df.iterrows():
        tid = row['id']
        prio = row['prioridade']
        criado = row['criado_data']
        resolvido = row['data_resolvido']

        # Calcula previsão esperada
        prazo_dias = prazo_por_criticidade(prio)

        if prazo_dias is None or pd.isna(criado):
            sem_prazo += 1
            resultados.append({
                'id': tid,
                'previsao_esperada': None,
                'dias_uteis_resolucao': None,
                'sla_criticidade_ok': None,
            })
            continue

        com_prazo += 1

        # Data de previsão calculada
        prev_esp = adicionar_dias_uteis(criado, prazo_dias)

        # Dias úteis até resolução
        dias_uteis = None
        sla_ok = None

        if pd.notna(resolvido):
            dias_uteis = contar_dias_uteis(criado, resolvido)
            sla_ok = 1 if dias_uteis <= prazo_dias else 0

        resultados.append({
            'id': tid,
            'previsao_esperada': prev_esp.strftime('%Y-%m-%d %H:%M:%S') if prev_esp is not None else None,
            'dias_uteis_resolucao': dias_uteis,
            'sla_criticidade_ok': sla_ok,
        })

    # Atualiza banco
    print(f'💾 Atualizando {len(resultados)} tickets...')
    conn.executemany('''
        UPDATE tickets
        SET previsao_esperada = ?,
            dias_uteis_resolucao = ?,
            sla_criticidade_ok = ?
        WHERE id = ?
    ''', [
        (r['previsao_esperada'], r['dias_uteis_resolucao'],
         r['sla_criticidade_ok'], r['id'])
        for r in resultados
    ])
    conn.commit()

    # Resumo
    print()
    print('=' * 60)
    print('RESUMO')
    print('=' * 60)
    print(f'   Com prazo definido : {com_prazo}')
    print(f'   Sem prazo          : {sem_prazo}')

    # Por criticidade
    df_res = pd.DataFrame(resultados)
    df_res = df_res.merge(
        df[['id', 'prioridade', 'status']], on='id', how='left'
    )

    print()
    print('📊 Cumprimento por criticidade (só resolvidos):')
    df_cumpr = df_res[df_res['sla_criticidade_ok'].notna()]

    if not df_cumpr.empty:
        for prio in sorted(df_cumpr['prioridade'].dropna().unique()):
            sub = df_cumpr[df_cumpr['prioridade'] == prio]
            total = len(sub)
            ok = (sub['sla_criticidade_ok'] == 1).sum()
            perc = (ok / total * 100) if total > 0 else 0
            print(f'   {prio:<12} {total:>4} tickets · {ok:>4} cumpridos · {perc:>5.1f}%')
    else:
        print('   (sem tickets resolvidos com prazo definido)')

    return df_res


def main():
    print('=' * 60)
    print('ANÁLISE DE SLA POR CRITICIDADE')
    print('=' * 60)
    print(f'📁 Banco: {BANCO}')

    if not BANCO.exists():
        print('❌ Banco não encontrado')
        return 1

    conn = sqlite3.connect(BANCO)

    # Verifica se as colunas existem
    cols = [c[1] for c in conn.execute('PRAGMA table_info(tickets)').fetchall()]

    if 'previsao_esperada' not in cols:
        print('⚠️  Adicionando colunas necessárias...')
        conn.execute('ALTER TABLE tickets ADD COLUMN previsao_esperada DATETIME')
        conn.execute('ALTER TABLE tickets ADD COLUMN dias_uteis_resolucao INTEGER')
        conn.execute('ALTER TABLE tickets ADD COLUMN sla_criticidade_ok INTEGER')
        conn.commit()

    analisar(conn)
    conn.close()

    print()
    print('✅ Análise concluída!')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())