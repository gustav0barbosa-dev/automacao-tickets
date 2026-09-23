# ============================================================
# analisar_sla_criticidade.py — v2 (novo SLA em horas úteis)
# ============================================================
# Novo SLA:
#   Urgente = 3h úteis
#   Alta    = 24h úteis
#   Média   = 48h / 72h úteis
#   Baixa   = 120h / 168h úteis
#
# Expediente: 08h-17h (seg-sex)
# SLA termina em: data_resolvido
# ============================================================

import sqlite3
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))

from utils_sla import (
    prazo_por_criticidade, peso_por_criticidade,
    previsao_esperada, contar_horas_uteis,
)

BANCO = RAIZ / 'dados' / 'tickets.db'


def analisar(conn):
    df = pd.read_sql('''
        SELECT id, prioridade, criado_data, data_resolvido, status
        FROM tickets
        WHERE prioridade IS NOT NULL
    ''', conn)

    print(f'📊 {len(df)} tickets para analisar')

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

        prazo_horas = prazo_por_criticidade(prio)

        if prazo_horas is None or pd.isna(criado):
            sem_prazo += 1
            resultados.append({
                'id': tid,
                'previsao_esperada': None,
                'horas_resolucao': None,
                'peso_criticidade': peso_por_criticidade(prio),
                'sla_criticidade_ok': None,
            })
            continue

        com_prazo += 1
        prev_esp = previsao_esperada(criado, prio)
        horas = None
        sla_ok = None

        if pd.notna(resolvido):
            horas = contar_horas_uteis(criado, resolvido)
            if horas is not None:
                sla_ok = 1 if horas <= prazo_horas else 0

        resultados.append({
            'id': tid,
            'previsao_esperada': prev_esp.strftime('%Y-%m-%d %H:%M:%S') if prev_esp is not None else None,
            'horas_resolucao': round(horas, 2) if horas is not None else None,
            'peso_criticidade': peso_por_criticidade(prio),
            'sla_criticidade_ok': sla_ok,
        })

    # Atualiza banco
    print(f'💾 Atualizando {len(resultados)} tickets...')
    conn.executemany('''
        UPDATE tickets
        SET previsao_esperada = ?,
            horas_resolucao = ?,
            peso_criticidade = ?,
            sla_criticidade_ok = ?
        WHERE id = ?
    ''', [
        (r['previsao_esperada'], r['horas_resolucao'],
         r['peso_criticidade'], r['sla_criticidade_ok'], r['id'])
        for r in resultados
    ])
    conn.commit()

    # Resumo
    df_res = pd.DataFrame(resultados).merge(
        df[['id', 'prioridade', 'status']], on='id'
    )

    print()
    print('=' * 60)
    print('RESUMO')
    print('=' * 60)
    print(f'   Com prazo definido : {com_prazo}')
    print(f'   Sem prazo          : {sem_prazo}')

    print()
    print('📊 Cumprimento por criticidade (só resolvidos):')
    df_c = df_res[df_res['sla_criticidade_ok'].notna()]
    if not df_c.empty:
        for prio in sorted(df_c['prioridade'].dropna().unique()):
            sub = df_c[df_c['prioridade'] == prio]
            total = len(sub)
            ok = int((sub['sla_criticidade_ok'] == 1).sum())
            perc = (ok / total * 100) if total else 0
            print(f'   {prio:<12} {total:>4} · {ok:>4} cumpridos · {perc:>5.1f}%')

    print()
    print('📊 Média de horas úteis por criticidade (só resolvidos):')
    if not df_c.empty:
        media = df_c.groupby('prioridade')['horas_resolucao'].mean().round(1)
        for prio, m in media.items():
            print(f'   {prio:<12} {m:>7.1f}h')

    return df_res


def main():
    print('=' * 60)
    print('ANÁLISE DE SLA POR CRITICIDADE (v2 — horas úteis)')
    print('=' * 60)
    print(f'📁 Banco: {BANCO}')
    print(f'⏰ Expediente: 08h-17h (seg-sex)')
    print()

    if not BANCO.exists():
        print('❌ Banco não encontrado')
        return 1

    conn = sqlite3.connect(BANCO)
    cols = [c[1] for c in conn.execute('PRAGMA table_info(tickets)').fetchall()]

    # Adiciona colunas necessárias
    if 'horas_resolucao' not in cols:
        print('⚠️  Adicionando coluna horas_resolucao...')
        conn.execute('ALTER TABLE tickets ADD COLUMN horas_resolucao REAL')

    if 'peso_criticidade' not in cols:
        print('⚠️  Adicionando coluna peso_criticidade...')
        conn.execute('ALTER TABLE tickets ADD COLUMN peso_criticidade INTEGER')

    if 'previsao_esperada' not in cols:
        conn.execute('ALTER TABLE tickets ADD COLUMN previsao_esperada DATETIME')

    if 'sla_criticidade_ok' not in cols:
        conn.execute('ALTER TABLE tickets ADD COLUMN sla_criticidade_ok INTEGER')

    conn.commit()

    analisar(conn)
    conn.close()

    print()
    print('✅ Análise concluída!')
    return 0


if __name__ == '__main__':
    sys.exit(main())