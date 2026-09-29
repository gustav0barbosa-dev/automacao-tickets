# ============================================================
# analisar_sla_criticidade.py — v3 (novo SLA em horas úteis)
# ============================================================
# Novo SLA:
#   Urgente = 3h úteis
#   Alta    = 24h úteis
#   Média   = 48h / 72h úteis
#   Baixa   = 120h / 168h úteis
#
# Expediente: 08h-17h (seg-sex)
# SLA termina em: data_resolvido
#
# OTIMIZAÇÕES:
#   - Processa APENAS tickets novos ou alterados (filtro inteligente)
#   - Barra de progresso no terminal
#   - Timeout de segurança em contar_horas_uteis (evita loop infinito)
#   - Log de ticket travado
# ============================================================

import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))

from utils_sla import (
    prazo_por_criticidade, peso_por_criticidade,
    previsao_esperada, contar_horas_uteis,
)

BANCO = RAIZ / 'dados' / 'tickets.db'

# Tempo máximo (segundos) que um ticket pode demorar pra ser processado
TIMEOUT_POR_TICKET = 10
# Máximo de iterações em contar_horas_uteis (evita loop infinito)
MAX_ITERACOES = 50000


# ==================== PROGRESSO ====================
def imprimir_barra(i, total, inicio, extra=''):
    """Imprime barra de progresso no terminal."""
    pct = i / total * 100
    preenchido = int(pct / 2.5)  # 40 chars = 100%
    barra = '█' * preenchido + '░' * (40 - preenchido)
    tempo = time.time() - inicio
    velocidade = i / tempo if tempo > 0 else 0
    eta = (total - i) / velocidade if velocidade > 0 else 0

    print(
        f'\r   [{barra}] {i}/{total} ({pct:5.1f}%) — '
        f'{tempo:5.1f}s (ETA {eta:5.1f}s) {extra}',
        end='', flush=True,
    )


# ==================== ANÁLISE ====================
def analisar(conn):
    """
    Analisa SLA APENAS de tickets novos ou alterados.
    Mostra barra de progresso.
    """
    inicio = time.time()

    # ==================== FILTRO INTELIGENTE ====================
    try:
        ultima_analise = pd.read_sql(
            "SELECT MAX(atualizado_em) as ultima FROM tickets "
            "WHERE sla_criticidade_ok IS NOT NULL",
            conn,
        )['ultima'].iloc[0]
    except Exception:
        ultima_analise = None

    if ultima_analise:
        print(f'📅 Última análise: {ultima_analise}')
        sql = '''
            SELECT id, prioridade, criado_data, data_resolvido, status, atualizado_em
            FROM tickets
            WHERE prioridade IS NOT NULL
              AND (
                  sla_criticidade_ok IS NULL
                  OR atualizado_em > ?
              )
            ORDER BY id
        '''
        df = pd.read_sql(sql, conn, params=(ultima_analise,))
    else:
        print('📅 Primeira análise — processando todos os tickets')
        sql = '''
            SELECT id, prioridade, criado_data, data_resolvido, status, atualizado_em
            FROM tickets
            WHERE prioridade IS NOT NULL
              AND sla_criticidade_ok IS NULL
            ORDER BY id
        '''
        df = pd.read_sql(sql, conn)

    if df.empty:
        print('✅ Nenhum ticket novo ou alterado para analisar')
        return pd.DataFrame()

    total = len(df)
    print(f'📊 {total} tickets para analisar (novos ou alterados)\n')

    # ==================== PREPARAÇÃO ====================
    df['criado_data'] = pd.to_datetime(df['criado_data'], errors='coerce')
    df['data_resolvido'] = pd.to_datetime(df['data_resolvido'], errors='coerce')

    # ==================== PROCESSAMENTO ====================
    resultados = []
    com_prazo = 0
    sem_prazo = 0
    travados = []

    for i, (_, row) in enumerate(df.iterrows(), 1):
        tid = row['id']

    for i, (_, row) in enumerate(df.iterrows(), 1):
        tid = row['id']
        prio = row['prioridade']
        criado = row['criado_data']
        resolvido = row['data_resolvido']

        # ⬇️ ADICIONAR ESTE PRINT DE DEBUG
        print(f'\n   🔍 [{i}/{total}] #{tid} ({prio}) criado={criado} resolvido={resolvido}', flush=True)

        t_inicio = time.time()
        # ... (resto do loop)       
        prio = row['prioridade']
        criado = row['criado_data']
        resolvido = row['data_resolvido']

        t_inicio = time.time()

                # No início do loop, antes de processar
        if pd.notna(criado) and criado.year < 2000:
            # Data suspeita — pula
            continue

        if pd.notna(resolvido) and resolvido.year < 2000:
            continue

        try:
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
            else:
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
                    'previsao_esperada': prev_esp.strftime('%Y-%m-%d %H:%M:%S')
                        if prev_esp is not None else None,
                    'horas_resolucao': round(horas, 2) if horas is not None else None,
                    'peso_criticidade': peso_por_criticidade(prio),
                    'sla_criticidade_ok': sla_ok,
                })

        except Exception as e:
            # Registra o ticket com erro
            travados.append({'id': tid, 'erro': str(e)[:100]})
            resultados.append({
                'id': tid,
                'previsao_esperada': None,
                'horas_resolucao': None,
                'peso_criticidade': None,
                'sla_criticidade_ok': None,
            })

        # ==================== TIMEOUT DE SEGURANÇA ====================
        t_fim = time.time()
        duracao = t_fim - t_inicio
        if duracao > TIMEOUT_POR_TICKET:
            print(f'\n   ⚠️  Ticket #{tid} demorou {duracao:.1f}s '
                  f'(>{TIMEOUT_POR_TICKET}s)')
            print(f'      Prioridade: {prio}, '
                  f'Criado: {criado}, Resolvido: {resolvido}')

        # ==================== BARRA DE PROGRESSO ====================
        if i % 10 == 0 or i == total:
            imprimir_barra(i, total, inicio)

    print()  # quebra linha
    tempo_processamento = time.time() - inicio
    print(f'   ✅ Processados em {tempo_processamento:.1f}s '
          f'({total/tempo_processamento:.0f} tickets/s)\n')

    if travados:
        print(f'⚠️  {len(travados)} tickets com erro:')
        for t in travados[:5]:
            print(f'   #{t["id"]}: {t["erro"]}')
        print()

    # ==================== ATUALIZA BANCO ====================
    print(f'💾 Atualizando {len(resultados)} tickets no banco...')
    t_update = time.time()
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
    print(f'   ✅ Banco atualizado em {time.time() - t_update:.1f}s\n')

    # ==================== RESUMO ====================
    df_res = pd.DataFrame(resultados).merge(
        df[['id', 'prioridade', 'status']], on='id'
    )

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
            total_p = len(sub)
            ok = int((sub['sla_criticidade_ok'] == 1).sum())
            perc = (ok / total_p * 100) if total_p else 0
            print(f'   {prio:<12} {total_p:>4} · {ok:>4} cumpridos · {perc:>5.1f}%')

    print()
    print('📊 Média de horas úteis por criticidade (só resolvidos, sem outliers):')
    if not df_c.empty:
        # Filtra outliers (horas > 10.000 = ~5 anos)
        df_c_clean = df_c[df_c['horas_resolucao'] < 10000].copy()
        
        if df_c_clean.empty:
            print('   (todos os tickets são outliers)')
        else:
            media = df_c_clean.groupby('prioridade')['horas_resolucao'].mean().round(1)
            for prio, m in media.items():
                n_outliers = len(df_c[df_c['prioridade'] == prio]) - len(df_c_clean[df_c_clean['prioridade'] == prio])
                extra = f' ({n_outliers} outliers)' if n_outliers > 0 else ''
                print(f'   {prio:<12} {m:>7.1f}h{extra}')

    return df_res


# ==================== MAIN ====================
def main():
    print('=' * 60)
    print('ANÁLISE DE SLA POR CRITICIDADE (v3 — horas úteis)')
    print('=' * 60)
    print(f'📁 Banco: {BANCO}')
    print(f'⏰ Expediente: 08h-17h (seg-sex)')
    print()

    if not BANCO.exists():
        print(f'❌ Banco não encontrado: {BANCO}')
        return 1

    conn = sqlite3.connect(BANCO)

    # Verifica/adiciona colunas necessárias
    cols = [r[1] for r in conn.execute('PRAGMA table_info(tickets)')]

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