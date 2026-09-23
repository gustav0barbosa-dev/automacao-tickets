# scripts/corrigir_movimentacoes_retroativo.py
"""
Corrige as movimentações já existentes no banco usando os arquivos
.xlsx salvos em dados/historicos/.
"""
import sqlite3
import pandas as pd
from pathlib import Path

CAMINHO_BANCO = Path('dados/tickets.db')
PASTA_HISTORICOS = Path('dados/historicos')

def parsear_data_br(texto):
    if texto is None:
        return None
    if hasattr(texto, 'year'):
        return pd.Timestamp(texto)
    texto = str(texto).strip()
    if not texto or texto.lower() in ('nan', 'nat', 'none', ''):
        return None
    for fmt in ('%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y'):
        try:
            return pd.to_datetime(texto, format=fmt)
        except Exception:
            continue
    return None

def corrigir_ticket(conn, ticket_id, arquivo_xlsx):
    """Lê o Excel, reescreve as movimentações e preenche de_status."""
    try:
        df = pd.read_excel(arquivo_xlsx)
    except Exception as e:
        print(f'❌ #{ticket_id}: erro lendo Excel: {e}')
        return 0

    # Ordena da MAIS ANTIGA para a MAIS NOVA (para o de_status fazer sentido)
    df['_data'] = df['Alterado Data'].apply(parsear_data_br)
    df = df.sort_values('_data', ascending=True).reset_index(drop=True)

    # Apaga movimentações antigas
    conn.execute('DELETE FROM movimentacoes WHERE ticket_id = ?', (ticket_id,))

    inseridos = 0
    status_anterior = None

    for _, row in df.iterrows():
        data_mov = parsear_data_br(row.get('Alterado Data'))
        status = row.get('Status')
        if pd.notna(status):
            status = str(status).strip()
        else:
            status = None

        autor = row.get('Alterado por')
        if pd.notna(autor):
            autor = str(autor).strip()
        else:
            autor = None

        responsavel = row.get('Responsável')
        if pd.notna(responsavel):
            responsavel = str(responsavel).strip()
        else:
            responsavel = None

        # de_status = status anterior DESTE ticket
        de_status = status_anterior

        conn.execute('''
            INSERT INTO movimentacoes
                (ticket_id, data_movimentacao, autor, tipo, de_status, para_status, comentario)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticket_id,
            data_mov.strftime('%Y-%m-%d %H:%M:%S') if data_mov is not None else None,
            autor,
            'historico',
            de_status,
            status,
            f'Responsável: {responsavel}' if responsavel else None,
        ))
        inseridos += 1

        # Atualiza o status anterior para a próxima iteração
        if status:
            status_anterior = status

    conn.commit()
    return inseridos

def main():
    if not CAMINHO_BANCO.exists():
        print(f'❌ Banco não encontrado: {CAMINHO_BANCO}')
        return

    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row

    arquivos = sorted(PASTA_HISTORICOS.glob('*.xlsx'))
    print(f'📁 {len(arquivos)} arquivos encontrados em {PASTA_HISTORICOS}')
    print()

    total_movs = 0
    total_tickets = 0

    for arq in arquivos:
        try:
            ticket_id = int(arq.stem)
        except ValueError:
            continue

        movs = corrigir_ticket(conn, ticket_id, arq)
        if movs > 0:
            total_tickets += 1
            total_movs += movs

        if total_tickets % 50 == 0:
            print(f'  ... {total_tickets} tickets processados')

    conn.close()
    print()
    print('=' * 60)
    print(f'✅ CORREÇÃO CONCLUÍDA')
    print(f'   Tickets corrigidos : {total_tickets}')
    print(f'   Movimentações      : {total_movs}')
    print('=' * 60)

if __name__ == '__main__':
    main()