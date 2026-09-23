# ============================================================
# selecionar_amostra.py
# ============================================================
# Seleciona 200 tickets que atendem aos filtros do dashboard,
# garantindo pelo menos 1 de cada tipo (combinação de status,
# categoria, prioridade, empresa, backlog, respondido).
#
# Uso:
#     python scripts/selecionar_amostra.py
#     python scripts/selecionar_amostra.py --total 300
#     python scripts/selecionar_amostra.py --saida amostra_validacao.xlsx
# ============================================================

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
PASTA_SAIDA = RAIZ / 'relatorios'


# ============================================================
# CARREGAMENTO
# ============================================================
def conectar():
    if not BANCO.exists():
        print(f'❌ Banco não encontrado: {BANCO}')
        sys.exit(1)
    return sqlite3.connect(BANCO)


def carregar_tickets(conn):
    """Carrega todos os tickets e aplica os mesmos filtros do dashboard."""
    df = pd.read_sql('SELECT * FROM tickets', conn)

    print(f'📊 Total bruto: {len(df)} tickets')

    # ---------- FILTROS DO DASHBOARD ----------

    # 1. Só tickets com dados mínimos
    df = df[df['status'].notna() & df['categoria'].notna()]
    print(f'   Após filtrar status/categoria nulos: {len(df)}')

    # 2. Status monitorados (não fechados/cancelados)
    status_validos = ['Em atendimento', 'Resolvido',
                      'Aguardando confirmação do usuário']
    df = df[df['status'].isin(status_validos)]
    print(f'   Após filtrar status monitorados: {len(df)}')

    # 3. Categorias monitoradas (remove blacklist)
    categorias_fora = [
        '1ª Etapa Censo', 'Alteração de Grupo de Pagamento',
        'Alterações Bancárias', 'Aplicações Folha', 'Cancelar Protocolo',
        'Cálculo da Média', 'Composição', 'Consignatárias',
        'Deploy - Homologação', 'Extinção', 'Folha de Pagamento',
        'Monitoramento Folha', 'Parametrização Folha', 'Processamento Folha',
        'Reabertura de Protocolo', 'Reajuste', 'Recadastramento',
        'Reenvio Bancário', 'Reprocessamento Folha', 'Retorno de Tarefa ',
        'Rubricas', 'Rubricas Judiciais Base Duplicadas',
        'Rúbricas Concomitantes', 'Task', 'Vínculos', 'Visita domiciliar',
    ]
    df = df[~df['categoria'].isin(categorias_fora)]
    print(f'   Após filtrar categorias fora: {len(df)}')

    # 4. Remove tickets com dados essenciais nulos
    df = df.dropna(subset=['id', 'status', 'categoria', 'prioridade'])

    return df


# ============================================================
# SELEÇÃO POR TIPO
# ============================================================
def definir_tipo(row):
    """
    Define o "tipo" do ticket como combinação de campos relevantes.
    Cada combinação única gera uma "chave de tipo".
    """
    campos = [
        str(row.get('status', '?')),
        str(row.get('categoria', '?')),
        str(row.get('prioridade', '?')),
        str(row.get('responsavel_empresa', '?')),
        str(row.get('backlog', '?')),
        str(row.get('respondido', '?')),
    ]
    return ' | '.join(campos)


def selecionar_amostra(df, total_desejado=200, seed=42):
    """
    Seleciona `total_desejado` tickets, garantindo pelo menos 1 de cada tipo.
    """
    print()
    print('=' * 60)
    print('SELEÇÃO DE AMOSTRA')
    print('=' * 60)

    # 1. Adiciona a coluna 'tipo'
    df = df.copy()
    df['tipo'] = df.apply(definir_tipo, axis=1)

    # 2. Conta quantos tipos únicos existem
    tipos_unicos = df['tipo'].value_counts()
    n_tipos = len(tipos_unicos)

    print(f'📊 Tipos únicos encontrados: {n_tipos}')
    print()
    print('📋 Top 10 tipos mais frequentes:')
    for tipo, qtd in tipos_unicos.head(10).items():
        partes = tipo.split(' | ')
        resumo = f'{partes[0][:20]:<20} | {partes[1][:15]:<15} | {partes[2][:8]}'
        print(f'   {qtd:>5}x  {resumo}')
    print()

    # 3. Seleciona 1 de cada tipo (garantia)
    print(f'✅ Selecionando 1 amostra de CADA tipo ({n_tipos} tipos)...')
    amostra_tipos = df.groupby('tipo').sample(n=1, random_state=seed)
    print(f'   {len(amostra_tipos)} tickets selecionados (1 por tipo)')

    # 4. Se ainda não atingiu o total, completa com amostras aleatórias
    # 4. Se ainda não atingiu o total, completa com amostras aleatórias
    # 4. Se ainda não atingiu o total, completa com amostras aleatórias
    faltam = total_desejado - len(amostra_tipos)

    if faltam > 0:
        print()
        print(f'➕ Faltam {faltam} tickets. Completando com amostra aleatória...')

        # Remove os já selecionados
        restantes = df[~df['id'].isin(amostra_tipos['id'])].copy()

        if restantes.empty:
            print('   ⚠️ Não há tickets restantes.')
            amostra_final = amostra_tipos
        elif len(restantes) <= faltam:
            # Não tem o suficiente — pega tudo
            print(f'   ⚠️ Só há {len(restantes)} tickets disponíveis. Usando todos.')
            amostra_final = pd.concat([amostra_tipos, restantes])
        else:
            # ---------- Amostra ponderada SEM pandas.sample ----------
            # Peso = quantas vezes o tipo aparece no df original
            pesos_por_tipo = df['tipo'].value_counts()
            restantes['peso'] = restantes['tipo'].map(pesos_por_tipo).fillna(1)

            # Normaliza para probabilidades (soma = 1)
            probs = restantes['peso'].values.astype(float)
            probs = probs / probs.sum()

            # Sorteia índices sem reposição
            import numpy as np
            np.random.seed(seed)
            indices_sorteados = np.random.choice(
                restantes.index,
                size=faltam,
                replace=False,
                p=probs,
            )

            amostra_extra = restantes.loc[indices_sorteados].drop(columns=['peso'])
            amostra_final = pd.concat([amostra_tipos, amostra_extra])
    else:
        amostra_final = amostra_tipos

    # 5. Remove duplicatas e ordena
    amostra_final = amostra_final.drop_duplicates(subset=['id'])
    amostra_final = amostra_final.sort_values(
        by=['status', 'categoria', 'prioridade', 'id']
    ).reset_index(drop=True)

    print()
    print('=' * 60)
    print(f'✅ AMOSTRA FINAL: {len(amostra_final)} tickets')
    print('=' * 60)

    return amostra_final


# ============================================================
# RESUMO DA AMOSTRA
# ============================================================
def imprimir_resumo(amostra):
    print()
    print('📊 RESUMO DA AMOSTRA:')
    print()

    # Por status
    print('Por status:')
    for status, qtd in amostra['status'].value_counts().items():
        print(f'   {status:<40} {qtd:>4}')

    print()
    print('Por empresa:')
    for emp, qtd in amostra['responsavel_empresa'].value_counts().items():
        print(f'   {str(emp):<40} {qtd:>4}')

    print()
    print('Por prioridade:')
    for prio, qtd in amostra['prioridade'].value_counts().items():
        print(f'   {str(prio):<40} {qtd:>4}')

    print()
    print('Por categoria (top 10):')
    for cat, qtd in amostra['categoria'].value_counts().head(10).items():
        print(f'   {str(cat)[:40]:<40} {qtd:>4}')


# ============================================================
# EXPORTAÇÃO
# ============================================================
def exportar_excel(amostra, caminho_saida):
    """Gera um Excel com abas: Instruções, Tickets, Resumo."""

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

    # ---------- ABA 1: INSTRUÇÕES ----------
    instrucoes_lista = [
        ('🎯 Objetivo', 'Validar se os dados dos tickets estão corretos no dashboard'),
        ('📅 Data de geração', datetime.now().strftime('%d/%m/%Y %H:%M')),
        ('📊 Total de tickets', str(len(amostra))),
        ('📁 Fonte', 'Banco de dados Help360'),
        ('', ''),
        ('🔍 COMO VALIDAR:', 'Verificar cada campo contra o Help360'),
        ('1. Filtro de status', 'O status bate com o real?'),
        ('2. Filtro de categoria', 'A categoria está correta?'),
        ('3. Filtro de prioridade', 'A prioridade está correta?'),
        ('4. Filtro de responsável', 'O responsável está correto?'),
        ('5. Filtro de backlog', 'O backlog está marcado certo?'),
        ('6. Filtro de resposta', 'Está respondido sim/não?'),
        ('7. Cálculo de aging', 'O cálculo de dias está correto?'),
        ('8. Cálculo de SLA', 'O SLA (cumprido/estourado) está correto?'),
        ('', ''),
        ('📝 COMO PREENCHER:', ''),
        ('Coluna "OK?"', 'Marque SIM, NÃO ou N/A em cada linha'),
        ('Coluna "Observação"', 'Escreva o que está errado'),
        ('Coluna "Corrigir para"', 'Escreva qual seria o valor correto'),
        ('', ''),
        ('⚠️ IMPORTANTE:', 'Devolver planilha preenchida'),
        ('Devolver até', 'Definir prazo com o gestor'),
    ]
    instrucoes = pd.DataFrame(instrucoes_lista, columns=['Item', 'Descrição'])

    # ---------- ABA 2: TICKETS ----------
    colunas_export = [
        'id', 'status', 'categoria', 'subcategoria', 'prioridade',
        'responsavel_atual', 'responsavel_empresa',
        'solicitante', 'criado_data', 'alterado_data',
        'dias_aberto', 'sla_status', 'backlog', 'respondido',
        'titulo',
    ]
    colunas_export = [c for c in colunas_export if c in amostra.columns]

    tickets_export = amostra[colunas_export].copy()

    # Formata datas
    for col in ['criado_data', 'alterado_data']:
        if col in tickets_export.columns:
            tickets_export[col] = pd.to_datetime(
                tickets_export[col], errors='coerce'
            ).dt.strftime('%d/%m/%Y %H:%M')

    # Renomeia colunas
    renomear = {
        'id': 'ID',
        'status': 'Status',
        'categoria': 'Categoria',
        'subcategoria': 'Subcategoria',
        'prioridade': 'Prioridade',
        'responsavel_atual': 'Responsável',
        'responsavel_empresa': 'Empresa',
        'solicitante': 'Solicitante',
        'criado_data': 'Criado em',
        'alterado_data': 'Alterado em',
        'dias_aberto': 'Dias Aberto',
        'sla_status': 'SLA',
        'backlog': 'Backlog',
        'respondido': 'Respondido',
        'titulo': 'Título',
    }
    tickets_export = tickets_export.rename(columns=renomear)

    # Adiciona colunas de validação
    tickets_export['OK?'] = ''
    tickets_export['Observação'] = ''
    tickets_export['Corrigir para'] = ''

    # ---------- ABA 3: RESUMO ----------
    resumo_lista = [
        ('Total de tickets', len(amostra)),
        ('Status únicos', amostra['status'].nunique()),
        ('Categorias únicas', amostra['categoria'].nunique()),
        ('Prioridades únicas', amostra['prioridade'].nunique()),
        ('Empresas únicas', amostra['responsavel_empresa'].nunique()),
    ]
    resumo = pd.DataFrame(resumo_lista, columns=['Métrica', 'Valor'])

    # ---------- EXPORTA ----------
    print()
    print(f'💾 Gerando Excel: {caminho_saida}')

    with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
        instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
        tickets_export.to_excel(writer, sheet_name='Tickets', index=False)
        resumo.to_excel(writer, sheet_name='Resumo', index=False)

        # Ajusta larguras
        workbook = writer.book
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    try:
                        if cell.value:
                            max_len = max(max_len, len(str(cell.value)))
                    except Exception:
                        pass
                ws.column_dimensions[col_letter].width = min(max_len + 3, 50)

    print(f'✅ Excel gerado com {len(tickets_export)} tickets')
    return caminho_saida


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--total', type=int, default=200,
                        help='Total de tickets na amostra (padrão: 200)')
    parser.add_argument('--saida', type=str, default=None,
                        help='Nome do arquivo de saída')
    args = parser.parse_args()

    print('=' * 60)
    print('SELEÇÃO DE AMOSTRA PARA VALIDAÇÃO')
    print('=' * 60)
    print(f'🎯 Total desejado: {args.total}')
    print(f'📁 Banco: {BANCO}')
    print()

    # 1. Carrega
    conn = conectar()
    df = carregar_tickets(conn)
    conn.close()

    if df.empty:
        print('❌ Nenhum ticket disponível após filtros.')
        return 1

    # 2. Seleciona amostra
    amostra = selecionar_amostra(df, total_desejado=args.total)

    # 3. Imprime resumo
    imprimir_resumo(amostra)

    # 4. Exporta
    if args.saida:
        nome_saida = args.saida
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        nome_saida = f'amostra_validacao_{timestamp}.xlsx'

    caminho = PASTA_SAIDA / nome_saida
    exportar_excel(amostra, caminho)

    print()
    print('=' * 60)
    print('✅ AMOSTRA GERADA COM SUCESSO')
    print('=' * 60)
    print(f'📁 Arquivo: {caminho}')
    print()
    print('📋 Próximos passos:')
    print('   1. Enviar o Excel para a analista')
    print('   2. Ela preenche as colunas OK?, Observação, Corrigir para')
    print('   3. Você importa o feedback e ajusta o pipeline')

    return 0


if __name__ == '__main__':
    sys.exit(main())