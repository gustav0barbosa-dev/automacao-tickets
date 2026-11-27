"""
Gera relatório de agrupamento de tickets por período (Excel).
Usa KMeans (clustering) + fallback inteligente para nomear os clusters.

Uso:
    python scripts_treinamento/gerar_relatorio_clusters.py --dias 30
    python scripts_treinamento/gerar_relatorio_clusters.py --dias 30 --n-clusters 20
    python scripts_treinamento/gerar_relatorio_clusters.py --dias 90 --excel nome.xlsx
"""
import argparse
import json
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
NOME_MODELO = 'paraphrase-multilingual-MiniLM-L12-v2'


# ==================== CARREGAMENTO ====================
def carregar_tickets_periodo(dias=30):
    """Carrega tickets dos últimos N dias (apenas com dados limpos)."""
    conn = sqlite3.connect(BANCO)
    data_limite = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

    df = pd.read_sql(f'''
        SELECT id, titulo, descricao, solucao, categoria, status,
               criado_data, alterado_data
        FROM tickets
        WHERE criado_data >= '{data_limite}'
          AND titulo NOT LIKE '%0000000000%'
          AND descricao NOT LIKE '%<TELEFONE>%'
          AND descricao NOT LIKE '%<CPF>%'
    ''', conn)
    conn.close()
    return df


def montar_texto_cluster(row):
    """Texto focado em descrição + solução (sem título)."""
    def tratar(valor, max_chars):
        if pd.isna(valor):
            return ''
        return str(valor)[:max_chars]

    descricao = tratar(row['descricao'], 800)
    solucao = tratar(row['solucao'], 400)
    return f"{descricao} {solucao}".strip()


# ==================== NOMEAÇÃO ====================
def fallback_inteligente(tickets_exemplo):
    """Extrai as palavras mais comuns dos títulos para nomear o cluster."""
    STOPWORDS = {
        'de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'em', 'para',
        'com', 'por', 'no', 'na', 'os', 'as', 'um', 'uma', 'ao', 'aos',
        'solicito', 'prezados', 'bom', 'dia', 'boa', 'tarde', 'noite',
        'favor', 'gentileza', 'verificar', 'podem', 'poderiam',
        'ticket', 'protocolo', 'acima', 'abaixo', 'seguinte',
        'segue', 'anexo', 'conforme', 'através', 'atraves',
        'informo', 'informamos', 'solicitamos', 'pedido', 'pedimos',
        'forma', 'geral', 'ainda', 'após', 'apos', 'sobre',
    }

    palavras = []
    for t in tickets_exemplo:
        titulo = str(t.get('titulo', '')).lower()
        palavras.extend(re.findall(r'\b[a-záàâãäéèêëíìîïóòôõöúùûüç]{4,}\b', titulo))

    contador = Counter(p for p in palavras if p not in STOPWORDS)
    top_palavras = [p.capitalize() for p, _ in contador.most_common(3)]

    if top_palavras:
        return ' - '.join(top_palavras)

    titulo = tickets_exemplo[0].get('titulo', '')
    return str(titulo)[:60] if titulo else 'Grupo sem título'


def nomear_cluster(tickets_exemplo):
    """Wrapper simples — usa apenas o fallback inteligente."""
    return fallback_inteligente(tickets_exemplo)


# ==================== EXCEL ====================
def gerar_excel(df, nomes_por_cluster, caminho_saida, periodo_dias):
    """Gera planilha Excel com 3 abas."""
    wb = Workbook()

    # ==================== ABA 1: RESUMO ====================
    ws_resumo = wb.active
    ws_resumo.title = 'Resumo'

    # Estilos
    header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=11)
    border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    # Título
    ws_resumo['A1'] = f'RELATÓRIO DE AGRUPAMENTO — Últimos {periodo_dias} dias'
    ws_resumo['A1'].font = Font(bold=True, size=14, color='1F4E78')
    ws_resumo.merge_cells('A1:E1')

    ws_resumo['A2'] = f'Gerado em: {datetime.now():%d/%m/%Y %H:%M}'
    ws_resumo['A2'].font = Font(italic=True, size=10, color='666666')
    ws_resumo.merge_cells('A2:E2')

    # Cabeçalho
    cabecalhos = ['Grupo', 'Nome do Grupo', 'Qtde Tickets', '% do Total', 'IDs']
    for col, cab in enumerate(cabecalhos, start=1):
        cell = ws_resumo.cell(row=4, column=col, value=cab)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    # Dados
    tamanhos = df.groupby('cluster').size().sort_values(ascending=False)
    row = 5
    for cluster_id, n in tamanhos.items():
        nome = nomes_por_cluster.get(cluster_id, 'Sem nome')
        ids = sorted(df[df['cluster'] == cluster_id]['id'].tolist())
        percentual = n / len(df) * 100

        ws_resumo.cell(row=row, column=1, value=cluster_id + 1)
        ws_resumo.cell(row=row, column=2, value=nome)
        ws_resumo.cell(row=row, column=3, value=n)
        ws_resumo.cell(row=row, column=4, value=f'{percentual:.1f}%')
        ws_resumo.cell(row=row, column=5, value=', '.join(map(str, ids)))

        for col in range(1, 6):
            cell = ws_resumo.cell(row=row, column=col)
            cell.border = border
            cell.alignment = Alignment(vertical='center', wrap_text=(col == 5))

        row += 1

    # Larguras
    ws_resumo.column_dimensions['A'].width = 10
    ws_resumo.column_dimensions['B'].width = 40
    ws_resumo.column_dimensions['C'].width = 15
    ws_resumo.column_dimensions['D'].width = 12
    ws_resumo.column_dimensions['E'].width = 60

    # Filtro
    ws_resumo.auto_filter.ref = f'A4:E{row - 1}'

    # ==================== ABA 2: TODOS OS TICKETS ====================
    ws_todos = wb.create_sheet('Todos os Tickets')

    # Cabeçalho
    colunas = ['ID', 'Grupo', 'Nome do Grupo', 'Título', 'Descrição',
               'Solução', 'Categoria', 'Status', 'Criado em', 'Alterado em']
    for col, cab in enumerate(colunas, start=1):
        cell = ws_todos.cell(row=1, column=col, value=cab)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    # Dados ordenados por cluster
    df_sorted = df.sort_values(['cluster', 'id'])
    for idx, row_data in enumerate(df_sorted.itertuples(), start=2):
        cid = row_data.cluster
        ws_todos.cell(row=idx, column=1, value=row_data.id)
        ws_todos.cell(row=idx, column=2, value=cid + 1)
        ws_todos.cell(row=idx, column=3, value=nomes_por_cluster.get(cid, ''))
        ws_todos.cell(row=idx, column=4, value=str(row_data.titulo)[:200] if pd.notna(row_data.titulo) else '')
        ws_todos.cell(row=idx, column=5, value=str(row_data.descricao)[:500] if pd.notna(row_data.descricao) else '')
        ws_todos.cell(row=idx, column=6, value=str(row_data.solucao)[:500] if pd.notna(row_data.solucao) else '')
        ws_todos.cell(row=idx, column=7, value=row_data.categoria or '')
        ws_todos.cell(row=idx, column=8, value=row_data.status or '')
        ws_todos.cell(row=idx, column=9, value=str(row_data.criado_data or ''))
        ws_todos.cell(row=idx, column=10, value=str(row_data.alterado_data or ''))

        for col in range(1, 11):
            cell = ws_todos.cell(row=idx, column=col)
            cell.border = border
            cell.alignment = Alignment(vertical='top', wrap_text=(col in (4, 5, 6)))

    # Larguras
    ws_todos.column_dimensions['A'].width = 10
    ws_todos.column_dimensions['B'].width = 8
    ws_todos.column_dimensions['C'].width = 30
    ws_todos.column_dimensions['D'].width = 40
    ws_todos.column_dimensions['E'].width = 50
    ws_todos.column_dimensions['F'].width = 50
    ws_todos.column_dimensions['G'].width = 20
    ws_todos.column_dimensions['H'].width = 15
    ws_todos.column_dimensions['I'].width = 18
    ws_todos.column_dimensions['J'].width = 18

    # Filtro
    ws_todos.auto_filter.ref = f'A1:J{len(df_sorted) + 1}'

    # ==================== ABA 3: POR GRUPO ====================
    ws_por_grupo = wb.create_sheet('Por Grupo')

    row = 1
    for cluster_id, n in tamanhos.items():
        nome = nomes_por_cluster.get(cluster_id, 'Sem nome')
        tickets_cluster = df[df['cluster'] == cluster_id].sort_values('id')

        # Título do grupo
        ws_por_grupo.cell(row=row, column=1, value=f'GRUPO {cluster_id + 1} — {nome} ({n} tickets)')
        ws_por_grupo.cell(row=row, column=1).font = Font(bold=True, size=12, color='1F4E78')
        ws_por_grupo.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        row += 1

        # Cabeçalho
        for col, cab in enumerate(['ID', 'Título', 'Status', 'Categoria'], start=1):
            cell = ws_por_grupo.cell(row=row, column=col, value=cab)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = border
        row += 1

        # Dados
        for t in tickets_cluster.itertuples():
            ws_por_grupo.cell(row=row, column=1, value=t.id)
            ws_por_grupo.cell(row=row, column=2, value=str(t.titulo)[:150] if pd.notna(t.titulo) else '')
            ws_por_grupo.cell(row=row, column=3, value=t.status or '')
            ws_por_grupo.cell(row=row, column=4, value=t.categoria or '')
            for col in range(1, 5):
                ws_por_grupo.cell(row=row, column=col).border = border
            row += 1

        row += 2  # linha em branco entre grupos

    ws_por_grupo.column_dimensions['A'].width = 10
    ws_por_grupo.column_dimensions['B'].width = 60
    ws_por_grupo.column_dimensions['C'].width = 20
    ws_por_grupo.column_dimensions['D'].width = 25

    # ==================== SALVA ====================
    wb.save(caminho_saida)
    print(f'\n✅ Excel salvo em: {caminho_saida}')


# ==================== MAIN ====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dias', type=int, default=30)
    parser.add_argument('--n-clusters', type=int, default=20)
    parser.add_argument('--excel', type=str, default=None,
                        help='Nome do arquivo Excel (sem caminho).')
    args = parser.parse_args()

    print('=' * 70)
    print(f'RELATÓRIO DE AGRUPAMENTO — Últimos {args.dias} dias')
    print('=' * 70)

    # 1. Carrega dados
    print('\n📂 Carregando tickets...')
    df = carregar_tickets_periodo(args.dias)
    print(f'   {len(df)} tickets no período (com dados limpos)')

    if df.empty:
        print('❌ Nenhum ticket encontrado.')
        return

    if len(df) < 4:
        print('⚠️  Poucos tickets para agrupar. Mínimo: 4.')
        return

    # 2. Embeddings
    print('\n🧠 Gerando embeddings...')
    model = SentenceTransformer(NOME_MODELO)
    textos = df.apply(montar_texto_cluster, axis=1).tolist()
    embeddings = model.encode(textos, show_progress_bar=True, batch_size=32)
    print(f'   Shape: {embeddings.shape}')

    # 3. KMeans
    n_clusters = args.n_clusters
    print(f'\n🔍 Agrupando {len(df)} tickets em {n_clusters} clusters...')
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['cluster'] = kmeans.fit_predict(embeddings)

    # 4. Nomeia clusters
    print('\n🏷️  Gerando nomes dos clusters...')
    nomes_por_cluster = {}
    for cluster_id in sorted(df['cluster'].unique()):
        tickets_cluster = df[df['cluster'] == cluster_id]
        exemplos = tickets_cluster.to_dict('records')
        nome = nomear_cluster(exemplos)
        nomes_por_cluster[cluster_id] = nome
        print(f'   Cluster {cluster_id}: {nome}')

    # 5. Relatório (console)
    print('\n' + '=' * 70)
    print('RELATÓRIO DE GRUPOS')
    print('=' * 70)

    tamanhos = df.groupby('cluster').size().sort_values(ascending=False)

    for cluster_id in tamanhos.index:
        n = tamanhos[cluster_id]
        tickets_cluster = df[df['cluster'] == cluster_id].sort_values('id')
        nome = nomes_por_cluster.get(cluster_id, 'Sem nome')

        print(f'\n📌 GRUPO {cluster_id + 1} — {nome}')
        print(f'   {n} tickets ({n / len(df) * 100:.1f}% do total)')
        print(f'   IDs: {sorted(tickets_cluster["id"].tolist())[:10]}...')

    # 6. Excel
    if args.excel:
        nome_arquivo = args.excel
    else:
        nome_arquivo = f'relatorio_clusters_{datetime.now():%Y%m%d_%H%M}.xlsx'

    caminho_excel = RAIZ / 'dados' / nome_arquivo
    gerar_excel(df, nomes_por_cluster, caminho_excel, args.dias)

    # 7. JSON (para integração com outros scripts)
    resumo = {
        'periodo_dias': args.dias,
        'total_tickets': len(df),
        'total_clusters': n_clusters,
        'clusters': [
            {
                'id': int(cid),
                'nome': nomes_por_cluster[cid],
                'n_tickets': int(tamanhos[cid]),
                'tickets': sorted(df[df['cluster'] == cid]['id'].tolist()),
            }
            for cid in tamanhos.index
        ],
    }
    saida_json = caminho_excel.with_suffix('.json')
    with open(saida_json, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)
    print(f'✅ Resumo JSON: {saida_json}')


if __name__ == '__main__':
    main()