"""
Diagnóstico do schema do Neon (Postgres) — versão para rodar NO RAILWAY.

Roda dentro do container do Railway, que tem acesso ao Neon.
"""
import os

from sqlalchemy import create_engine, text


def main():
    print('=' * 70)
    print('DIAGNÓSTICO DO NEON (via Railway)')
    print('=' * 70)

    # ==================== URL ====================
    # Railway injeta DATABASE_URL automaticamente
    url = os.environ.get('DATABASE_URL')

    if not url:
        print('❌ DATABASE_URL não encontrada')
        print('   Verifique se o serviço do Railway tem essa variável')
        return

    # Limpa a URL (remove parâmetros problemáticos)
    url = url.replace('&channel_binding=require', '')
    print(f'✅ URL: {url[:60]}...')
    print()

    # ==================== CONEXÃO ====================
    try:
        engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={'connect_timeout': 15},
        )

        with engine.connect() as conn:
            # ==================== TICKETS ====================
            print('📋 Colunas de tickets:')
            r = conn.execute(text('''
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'tickets'
                ORDER BY ordinal_position
            '''))
            colunas_tickets = []
            for row in r:
                print(f'   {row[0]:<30} {row[1]}')
                colunas_tickets.append(row[0])

            # ==================== MOVIMENTACOES ====================
            print()
            print('📋 Colunas de movimentacoes:')
            r = conn.execute(text('''
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'movimentacoes'
                ORDER BY ordinal_position
            '''))
            colunas_movs = []
            for row in r:
                print(f'   {row[0]:<30} {row[1]}')
                colunas_movs.append(row[0])

            # ==================== VERIFICAÇÕES ====================
            print()
            print('=' * 70)
            print('VERIFICAÇÕES')
            print('=' * 70)

            checks = [
                ('tickets.previsao', 'previsao' in colunas_tickets),
                ('tickets.id', 'id' in colunas_tickets),
                ('tickets.empresa', 'empresa' in colunas_tickets),
                ('tickets.responsavel_empresa', 'responsavel_empresa' in colunas_tickets),
                ('movimentacoes.para_status', 'para_status' in colunas_movs),
                ('movimentacoes.autor', 'autor' in colunas_movs),
                ('movimentacoes.data_movimentacao', 'data_movimentacao' in colunas_movs),
                ('movimentacoes.id', 'id' in colunas_movs),
                ('movimentacoes.ticket_id', 'ticket_id' in colunas_movs),
            ]

            for nome, existe in checks:
                emoji = '✅' if existe else '❌'
                print(f'   {emoji} {nome}')

            # ==================== CONTAGENS ====================
            print()
            print('📊 Contagens:')
            total = conn.execute(text('SELECT COUNT(*) FROM tickets')).scalar()
            print(f'   tickets: {total}')

            total_movs = conn.execute(text('SELECT COUNT(*) FROM movimentacoes')).scalar()
            print(f'   movimentacoes: {total_movs}')

            # ==================== TESTE DA QUERY ====================
            print()
            print('=' * 70)
            print('TESTE DA QUERY DO RELATÓRIO')
            print('=' * 70)

            try:
                query = '''
                WITH tickets_fechados AS (
                    SELECT DISTINCT ticket_id
                    FROM movimentacoes
                    WHERE para_status = 'Fechado'
                      AND DATE(data_movimentacao) >= '2026-09-01'
                      AND DATE(data_movimentacao) <= '2026-09-30'
                )
                SELECT COUNT(*) as n
                FROM tickets t
                INNER JOIN tickets_fechados tf ON tf.ticket_id = t.id
                '''
                r = conn.execute(text(query)).scalar()
                print(f'✅ Query simples funcionou: {r} tickets fechados')
            except Exception as e:
                print(f'❌ Erro na query: {e}')

            try:
                query2 = '''
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
                SELECT COUNT(*) as n
                FROM tickets t
                INNER JOIN tickets_fechados tf ON tf.ticket_id = t.id
                LEFT JOIN primeiro_resolvido pr ON pr.ticket_id = t.id AND pr.rn = 1
                '''
                r = conn.execute(text(query2)).scalar()
                print(f'✅ Query com ROW_NUMBER funcionou: {r} tickets')
            except Exception as e:
                print(f'❌ Erro na query com ROW_NUMBER: {e}')

    except Exception as e:
        print(f'❌ Erro na conexão: {e}')
    finally:
        try:
            engine.dispose()
        except Exception:
            pass


if __name__ == '__main__':
    main()