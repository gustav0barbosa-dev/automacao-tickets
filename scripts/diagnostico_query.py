"""
Diagnóstico da query do relatório — testa no Neon (Railway).
"""
import os

from sqlalchemy import create_engine, text


def main():
    print('=' * 70)
    print('DIAGNÓSTICO DA QUERY DO RELATÓRIO')
    print('=' * 70)

    url = os.environ.get('DATABASE_URL')
    if not url:
        print('❌ DATABASE_URL não encontrada')
        return

    url = url.replace('&channel_binding=require', '')
    print(f'✅ URL: {url[:60]}...')
    print()

    engine = create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout': 15})

    with engine.connect() as conn:
        # ==================== 1. TESTA QUERY SIMPLES ====================
        print('🔍 Teste 1: Query simples (só tickets_fechados)')
        try:
            query = '''
            SELECT DISTINCT ticket_id
            FROM movimentacoes
            WHERE para_status = 'Fechado'
              AND DATE(data_movimentacao) >= '2026-09-01'
              AND DATE(data_movimentacao) <= '2026-09-30'
            '''
            r = conn.execute(text(query)).fetchall()
            print(f'   ✅ OK: {len(r)} tickets')
        except Exception as e:
            print(f'   ❌ ERRO: {e}')
            return

        # ==================== 2. TESTA COM JOIN ====================
        print()
        print('🔍 Teste 2: Query com JOIN')
        try:
            query = '''
            WITH tickets_fechados AS (
                SELECT DISTINCT ticket_id
                FROM movimentacoes
                WHERE para_status = 'Fechado'
                  AND DATE(data_movimentacao) >= '2026-09-01'
                  AND DATE(data_movimentacao) <= '2026-09-30'
            )
            SELECT t.id, t.previsao
            FROM tickets t
            INNER JOIN tickets_fechados tf ON tf.ticket_id = t.id
            LIMIT 5
            '''
            r = conn.execute(text(query)).fetchall()
            print(f'   ✅ OK: {len(r)} registros')
            for row in r:
                print(f'      {row[0]} | previsao={row[1]}')
        except Exception as e:
            print(f'   ❌ ERRO: {e}')

        # ==================== 3. TESTA COM ROW_NUMBER ====================
        print()
        print('🔍 Teste 3: Query com ROW_NUMBER')
        try:
            query = '''
            WITH tickets_fechados AS (
                SELECT DISTINCT ticket_id
                FROM movimentacoes
                WHERE para_status = 'Fechado'
                  AND DATE(data_movimentacao) >= '2026-09-01'
                  AND DATE(data_movimentacao) <= '2026-09-30'
            ),
            primeiro_resolvido AS (
                SELECT
                    ticket_id,
                    data_movimentacao,
                    autor,
                    ROW_NUMBER() OVER (
                        PARTITION BY ticket_id
                        ORDER BY data_movimentacao ASC, id ASC
                    ) AS rn
                FROM movimentacoes
                WHERE para_status = 'Resolvido'
                  AND ticket_id IN (SELECT ticket_id FROM tickets_fechados)
            )
            SELECT
                t.id,
                pr.data_movimentacao,
                pr.autor
            FROM tickets t
            INNER JOIN tickets_fechados tf ON tf.ticket_id = t.id
            LEFT JOIN primeiro_resolvido pr ON pr.ticket_id = t.id AND pr.rn = 1
            LIMIT 5
            '''
            r = conn.execute(text(query)).fetchall()
            print(f'   ✅ OK: {len(r)} registros')
            for row in r:
                print(f'      {row[0]} | {row[1]} | {row[2]}')
        except Exception as e:
            print(f'   ❌ ERRO: {e}')

        # ==================== 4. TESTA QUERY COMPLETA ====================
        print()
        print('🔍 Teste 4: Query COMPLETA (a do relatório)')
        try:
            query = '''
            WITH tickets_fechados AS (
                SELECT DISTINCT ticket_id
                FROM movimentacoes
                WHERE para_status = 'Fechado'
                  AND DATE(data_movimentacao) >= :inicio
                  AND DATE(data_movimentacao) <= :fim
            ),
            primeiro_resolvido AS (
                SELECT
                    ticket_id,
                    data_movimentacao,
                    autor,
                    ROW_NUMBER() OVER (
                        PARTITION BY ticket_id
                        ORDER BY data_movimentacao ASC, id ASC
                    ) AS rn
                FROM movimentacoes
                WHERE para_status = 'Resolvido'
                  AND ticket_id IN (SELECT ticket_id FROM tickets_fechados)
            ),
            ultimo_resolvido AS (
                SELECT
                    m.ticket_id,
                    m.data_movimentacao,
                    m.autor,
                    ROW_NUMBER() OVER (
                        PARTITION BY m.ticket_id
                        ORDER BY m.data_movimentacao DESC, m.id DESC
                    ) AS rn
                FROM movimentacoes m
                WHERE m.para_status = 'Resolvido'
                  AND m.ticket_id IN (SELECT ticket_id FROM tickets_fechados)
            )
            SELECT
                t.id AS "ID Ticket",
                pr.data_movimentacao AS "Data 1º Resolvido",
                pr.autor AS "Alterado por (1º)",
                ur.data_movimentacao AS "Data Último Resolvido",
                ur.autor AS "Alterado por (Último)",
                t.previsao AS "Previsão"
            FROM tickets t
            INNER JOIN tickets_fechados tf ON tf.ticket_id = t.id
            LEFT JOIN primeiro_resolvido pr ON pr.ticket_id = t.id AND pr.rn = 1
            LEFT JOIN ultimo_resolvido ur ON ur.ticket_id = t.id AND ur.rn = 1
            ORDER BY pr.data_movimentacao ASC
            LIMIT 5
            '''
            r = conn.execute(text(query), {'inicio': '2026-09-01', 'fim': '2026-09-30'}).fetchall()
            print(f'   ✅ OK: {len(r)} registros')
            for row in result:
                print(f'      {row}')
        except Exception as e:
            print(f'   ❌ ERRO: {e}')

    engine.dispose()


if __name__ == '__main__':
    main()