"""
Exporta os tickets do banco SQLite (dados/tickets.db) para uma planilha Excel.

Gera duas abas:
    Tickets  — todos os dados dos tickets
    Resumo   — contagens por status, prioridade e categoria

Uso:
    python scripts/exportar_tickets_excel.py
    python scripts/exportar_tickets_excel.py --dias 30
    python scripts/exportar_tickets_excel.py --status "Em atendimento,Resolvido"
    python scripts/exportar_tickets_excel.py --saida relatorios/meus_tickets.xlsx
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RAIZ = Path(__file__).resolve().parent.parent
BANCO_PADRAO = RAIZ / 'dados' / 'tickets.db'
PASTA_RELATORIOS = RAIZ / 'relatorios'

# Colunas exportadas: (coluna_no_banco, cabeçalho_no_excel)
COLUNAS = [
    ('id',                   'ID'),
    ('titulo',               'Título'),
    ('descricao',            'Descrição'),
    ('categoria',            'Categoria'),
    ('subcategoria',         'Subcategoria'),
    ('status',               'Status'),
    ('prioridade',           'Prioridade'),
    ('responsavel_atual',    'Responsável'),
    ('solicitante',          'Solicitante'),
    ('empresa',              'Empresa'),
    ('responsavel_empresa',  'Empresa do responsável'),
    ('area',                 'Área'),
    ('sistema',              'Sistema'),
    ('classificacao',        'Classificação'),
    ('criado_data',          'Criado em'),
    ('alterado_data',        'Alterado em'),
    ('previsao',             'Previsão'),
    ('data_resolvido',       'Resolvido em'),
    ('data_1_resolvido',     '1º Resolvido em'),
    ('horas_resolucao',      'Horas de resolução'),
    ('dias_uteis_resolucao', 'Dias úteis de resolução'),
    ('backlog',              'Backlog'),
    ('respondido',           'Respondido'),
    ('pendente_usuario',     'Pendente do usuário'),
    ('acao_interna',         'Ação interna'),
    ('diagnostico',          'Diagnóstico'),
    ('solucao',              'Solução'),
]

COLUNAS_DATA = {
    'criado_data', 'alterado_data', 'previsao',
    'data_resolvido', 'data_1_resolvido',
}
COLUNAS_SIM_NAO = {'backlog', 'respondido', 'pendente_usuario', 'acao_interna'}

FORMATO_DATA = 'dd/mm/yyyy hh:mm'


def colunas_existentes(conn) -> list:
    """Descobre quais colunas da lista existem na tabela tickets."""
    existentes = {linha[1] for linha in conn.execute('PRAGMA table_info(tickets)')}
    return [(col, rotulo) for col, rotulo in COLUNAS if col in existentes]


def ler_tickets(banco: Path, dias=None, status=None, limite=None) -> pd.DataFrame:
    """Lê os tickets do SQLite, com filtros opcionais."""
    if not banco.exists():
        raise FileNotFoundError(
            f'Banco não encontrado: {banco}\n'
            'Rode o Programa1 + Programa4 (ou descomprima o .gz) primeiro.'
        )

    conn = sqlite3.connect(banco)
    conn.row_factory = sqlite3.Row

    try:
        colunas = colunas_existentes(conn)
        if not colunas:
            raise RuntimeError('Tabela "tickets" não encontrada no banco.')

        selecao = ', '.join(col for col, _ in colunas)
        sql = f'SELECT {selecao} FROM tickets WHERE 1 = 1'
        params = []

        if dias is not None:
            sql += (" AND (alterado_data >= date('now', ?)"
                    " OR criado_data >= date('now', ?))")
            params.extend([f'-{dias} days', f'-{dias} days'])

        if status:
            placeholders = ', '.join('?' * len(status))
            sql += f' AND status IN ({placeholders})'
            params.extend(status)

        sql += ' ORDER BY alterado_data DESC'
        if limite:
            sql += ' LIMIT ?'
            params.append(limite)

        df = pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()

    # Renomeia para os cabeçalhos amigáveis
    df = df.rename(columns=dict(colunas))
    return df


def preparar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Converte datas e indicadores para valores legíveis no Excel."""
    df = df.copy()

    rotulos_data = {rotulo for col, rotulo in COLUNAS if col in COLUNAS_DATA}
    rotulos_sim_nao = {rotulo for col, rotulo in COLUNAS if col in COLUNAS_SIM_NAO}

    for col in df.columns:
        if col in rotulos_data:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        elif col in rotulos_sim_nao:
            df[col] = df[col].map({1: 'Sim', 0: 'Não',
                                   1.0: 'Sim', 0.0: 'Não'})

    return df


def _ajustar_larguras(ws, max_linhas=200, largura_max=60):
    """Ajusta a largura das colunas com base no conteúdo."""
    ultima_linha = min(max_linhas, ws.max_row)
    for col_idx, coluna in enumerate(
            ws.iter_cols(min_row=1, max_row=ultima_linha), 1):
        maior = max((len(str(c.value)) for c in coluna if c.value is not None),
                    default=8)
        letra = get_column_letter(col_idx)
        ws.column_dimensions[letra].width = min(max(maior + 2, 10), largura_max)


def _escrever_resumo(writer, df: pd.DataFrame):
    """Cria a aba Resumo com contagens por status, prioridade e categoria."""
    ws = writer.book.create_sheet('Resumo')

    blocos = [
        ('A', 'Tickets por status', 'Status'),
        ('D', 'Tickets por prioridade', 'Prioridade'),
        ('G', 'Tickets por categoria', 'Categoria'),
    ]

    cabecalho_fonte = Font(bold=True, color='FFFFFF')
    cabecalho_fundo = PatternFill('solid', fgColor='1F4E78')

    for letra, titulo, campo in blocos:
        letra_qtd = get_column_letter(ord(letra) - 64 + 1)

        for celula, texto in ((f'{letra}1', titulo), (f'{letra_qtd}1', 'Qtd')):
            ws[celula] = texto
            ws[celula].font = cabecalho_fonte
            ws[celula].fill = cabecalho_fundo

        if campo in df.columns:
            contagem = (df[campo].fillna('(vazio)')
                        .astype(str).value_counts().head(20))
            for linha, (valor, qtd) in enumerate(contagem.items(), start=2):
                ws[f'{letra}{linha}'] = valor
                ws[f'{letra_qtd}{linha}'] = int(qtd)

        ws.column_dimensions[letra].width = 28
        ws.column_dimensions[letra_qtd].width = 10

    ws.sheet_view.showGridLines = False


def exportar_excel(df: pd.DataFrame, caminho: Path) -> Path:
    """Grava o DataFrame em Excel com formatação."""
    caminho.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Tickets', index=False)

        ws = writer.sheets['Tickets']

        # Cabeçalho
        for celula in ws[1]:
            celula.font = Font(bold=True, color='FFFFFF')
            celula.fill = PatternFill('solid', fgColor='1F4E78')
            celula.alignment = Alignment(horizontal='center', vertical='center')

        # Datas como data real no Excel
        for col_idx, nome in enumerate(df.columns, 1):
            if pd.api.types.is_datetime64_any_dtype(df[nome]):
                for (celula,) in ws.iter_rows(min_row=2, min_col=col_idx,
                                              max_col=col_idx):
                    celula.number_format = FORMATO_DATA

        ws.freeze_panes = 'B2'
        ws.auto_filter.ref = ws.dimensions
        _ajustar_larguras(ws)

        _escrever_resumo(writer, df)

    return caminho


def main():
    parser = argparse.ArgumentParser(
        description='Exporta os tickets do SQLite para Excel')
    parser.add_argument('--banco', default=str(BANCO_PADRAO),
                        help='Caminho do tickets.db (padrão: dados/tickets.db)')
    parser.add_argument('--saida', default=None,
                        help='Caminho do .xlsx de saída')
    parser.add_argument('--dias', type=int, default=None,
                        help='Só tickets criados/alterados nos últimos N dias')
    parser.add_argument('--status', type=str, default=None,
                        help='Filtra por status, separados por vírgula')
    parser.add_argument('--limite', type=int, default=None,
                        help='Máximo de tickets exportados')
    args = parser.parse_args()

    banco = Path(args.banco)
    status = None
    if args.status:
        status = [s.strip() for s in args.status.split(',') if s.strip()]

    print('=' * 60)
    print('EXPORTAÇÃO DE TICKETS PARA EXCEL')
    print('=' * 60)
    print(f'📁 Banco: {banco}')

    filtros = []
    if args.dias:
        filtros.append(f'últimos {args.dias} dias')
    if status:
        filtros.append('status: ' + ', '.join(status))
    if args.limite:
        filtros.append(f'limite: {args.limite}')
    print(f'🎯 Filtros: {"; ".join(filtros) if filtros else "nenhum"}')
    print()

    try:
        df = ler_tickets(banco, dias=args.dias, status=status,
                         limite=args.limite)
    except (FileNotFoundError, RuntimeError) as e:
        print(f'❌ {e}')
        return 1

    if df.empty:
        print('⚠️ Nenhum ticket encontrado com esses filtros.')
        return 1

    df = preparar_dataframe(df)

    if args.saida:
        caminho = Path(args.saida)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        caminho = PASTA_RELATORIOS / f'tickets_{timestamp}.xlsx'

    exportar_excel(df, caminho)

    print(f'✅ {len(df)} ticket(s) exportado(s)')
    print(f'✅ Planilha gerada: {caminho}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
