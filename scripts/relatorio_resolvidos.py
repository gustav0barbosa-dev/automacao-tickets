"""
Relatório de tickets que fecharam num período.

Colunas:
    ID Ticket | Data 1º Resolvido | Alterado por | Data Último Resolvido | Alterado por | Previsão

Uso:
    python scripts/relatorio_resolvidos.py --inicio 2026-09-01 --fim 2026-09-30
"""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'


def gerar_relatorio(inicio: str, fim: str, engine=None) -> pd.DataFrame:
    """
    Gera o relatório de tickets fechados no período.
    
    Args:
        inicio: data inicial (YYYY-MM-DD)
        fim: data final (YYYY-MM-DD)
        engine: engine do SQLAlchemy (opcional)
                Se None, usa SQLite local
    """
    # ==================== ENGINE ====================
    if engine is None:
        # Fallback: SQLite local
        conn = sqlite3.connect(BANCO)
        params = (f'{inicio} 00:00:00', f'{fim} 23:59:59')
        ph_inicio = '?'
        ph_fim = '?'
    else:
        # Postgres (via engine do dashboard)
        conn = engine
        params = {'inicio': f'{inicio} 00:00:00', 'fim': f'{fim} 23:59:59'}
        ph_inicio = ':inicio'
        ph_fim = ':fim'

    # ==================== QUERY ====================
    query = f'''
    WITH tickets_fechados AS (
        SELECT DISTINCT ticket_id
        FROM movimentacoes
        WHERE para_status = 'Fechado'
          AND data_movimentacao >= {ph_inicio}
          AND data_movimentacao <= {ph_fim}
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
    '''

    df = pd.read_sql(query, conn, params=params)

    if engine is None:
        conn.close()

    return df


def exportar_excel(df: pd.DataFrame, caminho: Path):
    """Exporta pra Excel com formatação."""
    if df.empty:
        return None

    # Formata datas
    for col in ['Data 1º Resolvido', 'Data Último Resolvido', 'Previsão']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df[col] = df[col].dt.strftime('%d/%m/%Y %H:%M')

    # Exporta
    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Resolvidos', index=False)

        # Ajusta largura
        ws = writer.sheets['Resolvidos']
        for col in ws.columns:
            max_len = max((len(str(c.value or '')) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    return caminho


def main():
    parser = argparse.ArgumentParser(description='Relatório de tickets resolvidos')
    parser.add_argument('--inicio', required=True, help='Data inicial (YYYY-MM-DD)')
    parser.add_argument('--fim', required=True, help='Data final (YYYY-MM-DD)')
    parser.add_argument('--saida', default=None, help='Caminho do Excel')

    args = parser.parse_args()

    print('=' * 60)
    print('RELATÓRIO DE TICKETS RESOLVIDOS')
    print('=' * 60)
    print(f'Período: {args.inicio} a {args.fim}')
    print()

    df = gerar_relatorio(args.inicio, args.fim)

    if df.empty:
        print('⚠️ Nenhum ticket encontrado no período')
        return 1

    print(f'📊 {len(df)} tickets encontrados\n')
    print(df.head(10).to_string(index=False))
    print()

    if args.saida:
        caminho = Path(args.saida)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        caminho = Path.home() / 'Downloads' / f'resolvidos_{args.inicio}_a_{args.fim}_{timestamp}.xlsx'

    exportar_excel(df, caminho)
    print(f'✅ Excel gerado: {caminho}')

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())