# scripts_treinamento/11_inteligencia_tickets.py
"""
Etapa 5 — Inteligência de Tickets: Script de análise para o dashboard.

Gera os dados consolidados para as 5 funcionalidades da área Inteligência de Tickets:
  1. Análise de recorrência (entrega 1)
  2. Qualidade da abertura dos tickets (entrega 2)
  3. Análise de problemas operacionais (entrega 3)
  4. Recomendações inteligentes (entrega 4)
  5. Investigação detalhada (entrega 4)

Saídas em scripts_treinamento/artefatos/:
  - inteligencia_tickets_recorrencia.csv      -> Painel de recorrência
  - inteligencia_tickets_qualidade.csv        -> Painel de qualidade/eficiência
  - inteligencia_tickets_operacional.csv      -> Problemas operacionais
  - inteligencia_tickets_recomendacoes.csv    -> Recomendações inteligentes

Não quebra nada do pipeline nem do dashboard. Mudança aditiva.
"""

import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
import sqlite3

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
ARTEFATOS = RAIZ / 'scripts_treinamento' / 'artefatos'


def carregar_dados():
    """Carrega tickets e movimentações do banco SQLite."""
    conn = sqlite3.connect(BANCO)

    tickets = pd.read_sql('SELECT * FROM tickets', conn)
    movs = pd.read_sql('SELECT * FROM movimentacoes', conn)
    msgs = pd.read_sql('SELECT * FROM mensagens', conn)

    conn.close()

    # Converte datas
    for df in [tickets, movs, msgs]:
        for col in df.columns:
            if 'data' in col.lower() or 'criado' in col.lower() or 'alterado' in col.lower():
                df[col] = pd.to_datetime(df[col], errors='coerce')

    return tickets, movs, msgs


def analisar_recorrencia(tickets, movs):
    """
    Entrega 1: Análise de recorrência.
    Ranking dos assuntos, evolução mensal, distribuição por sistema e setor.
    """
    # Usa motivo real se disponível (coluna motivo_real do MLP), senão categoria
    col_motivo = 'motivo_real' if 'motivo_real' in tickets.columns else 'categoria'

    # Ranking dos assuntos (top 20)
    ranking = tickets[col_motivo].value_counts().head(20).reset_index()
    ranking.columns = ['assunto', 'qtd_tickets']
    ranking['pct'] = (ranking['qtd_tickets'] / len(tickets) * 100).round(2)

    # Evolução mensal (últimos 12 meses)
    tickets_copia = tickets.copy()
    tickets_copia['criado_data'] = pd.to_datetime(
        tickets_copia['criado_data'], errors='coerce'
    )
    tickets_copia = tickets_copia[tickets_copia['criado_data'].notna()]
    tickets_copia['mes'] = tickets_copia['criado_data'].dt.to_period('M')
    evolucao = tickets_copia.groupby('mes').size().reset_index()
    evolucao.columns = ['mes', 'qtd_tickets']
    evolucao['mes_str'] = evolucao['mes'].astype(str)
    evolucao = evolucao.sort_values('mes').tail(12)

    # Crescimento mês a mês
    evolucao['crescimento_pct'] = evolucao['qtd_tickets'].pct_change() * 100
    evolucao['crescimento_pct'] = evolucao['crescimento_pct'].round(2)

    # Distribuição por sistema
    if 'sistema' in tickets.columns:
        dist_sistema = tickets['sistema'].value_counts().head(10).reset_index()
        dist_sistema.columns = ['sistema', 'qtd_tickets']
    else:
        dist_sistema = pd.DataFrame(columns=['sistema', 'qtd_tickets'])

    # Distribuição por área/setor
    if 'area' in tickets.columns:
        dist_area = tickets['area'].value_counts().head(10).reset_index()
        dist_area.columns = ['area', 'qtd_tickets']
    else:
        dist_area = pd.DataFrame(columns=['area', 'qtd_tickets'])

    # Distribuição por categoria declarada (assunto informado vs real)
    dist_categoria = tickets['categoria'].value_counts().head(15).reset_index()
    dist_categoria.columns = ['categoria_declarada', 'qtd_tickets']

    return {
        'ranking_assuntos': ranking,
        'evolucao_mensal': evolucao,
        'dist_sistema': dist_sistema,
        'dist_area': dist_area,
        'dist_categoria': dist_categoria,
    }


def analisar_qualidade_abertura(tickets, movs, msgs):
    """
    Entrega 2: Qualidade da abertura dos tickets.
    Identifica assuntos genéricos, descrições insuficientes, divergências.
    """
    resultado = {}

    # Tickets com descrição insuficiente (menos de 20 caracteres)
    tickets_copia = tickets.copy()
    tickets_copia['descricao_tamanho'] = tickets_copia['descricao'].fillna('').str.len()
    descricao_insuficiente = tickets_copia[
        tickets_copia['descricao_tamanho'] < 20
    ].copy()
    descricao_insuficiente['motivo'] = 'Descrição insuficiente (<20 chars)'
    resultado['descricao_insuficiente'] = descricao_insuficiente[
        ['id', 'titulo', 'descricao', 'categoria', 'criado_data', 'descricao_tamanho']
    ]

    # Assunto genérico: categoria declarada muito usada + título curto
    assunto_generico = tickets_copia[
        (tickets_copia['titulo'].fillna('').str.len() < 30) &
        (tickets_copia['descricao_tamanho'] < 50)
    ].copy()
    assunto_generico['motivo'] = 'Assunto genérico / título curto'
    resultado['assunto_generico'] = assunto_generico[
        ['id', 'titulo', 'descricao', 'categoria', 'criado_data', 'descricao_tamanho']
    ]

    # Divergência: categoria declarada vs motivo real (se houver coluna motivo_real)
    if 'motivo_real' in tickets.columns:
        div = tickets_copia[
            tickets_copia['categoria'] != tickets_copia['motivo_real']
        ].copy()
        div['motivo'] = 'Divergência categoria vs motivo real'
        resultado['divergencia'] = div[
            ['id', 'titulo', 'categoria', 'motivo_real', 'criado_data']
        ]
    else:
        resultado['divergencia'] = pd.DataFrame()

    # Reaberturas: ticket que voltou para status aberto após fechamento
    # Usa movimentacoes para detectar reabertura
    if not movs.empty:
        reaberturas = []
        for ticket_id, grupo in movs.groupby('ticket_id'):
            grupo = grupo.sort_values('data_movimentacao')
            status_anterior = None
            for _, linha in grupo.iterrows():
                if status_anterior in ('Fechado', 'Resolvido', 'Cancelado') \
                        and linha['para_status'] in ('Aberto', 'Em Atendimento'):
                    reaberturas.append({
                        'ticket_id': ticket_id,
                        'data_reabertura': linha['data_movimentacao'],
                        'status_anterior': status_anterior,
                        'status_atual': linha['para_status'],
                        'autor': linha['autor'],
                    })
                status_anterior = linha['para_status']
        if reaberturas:
            resultado['reaberturas'] = pd.DataFrame(reaberturas)
        else:
            resultado['reaberturas'] = pd.DataFrame()
    else:
        resultado['reaberturas'] = pd.DataFrame()

    return resultado


def analisar_problemas_operacionais(tickets, movs):
    """
    Entrega 3: Análise de problemas operacionais.
    Reincidências, tickets parados, demora, violações de SLA.
    """
    resultado = {}

    # Tickets parados: sem movimentação há mais de X dias
    if not movs.empty:
        ultima_mov = movs.groupby('ticket_id')['data_movimentacao'].max().reset_index()
        ultima_mov.columns = ['ticket_id', 'ultima_movimentacao']
        # tickets usa 'id' como PK
        tickets_com_mov = tickets.merge(
            ultima_mov, left_on='id', right_on='ticket_id', how='left'
        )
        tickets_com_mov['dias_sem_movimento'] = (
            pd.Timestamp.now() - tickets_com_mov['ultima_movimentacao']
        ).dt.days

        tickets_parados = tickets_com_mov[
            (tickets_com_mov['dias_sem_movimento'] > 7) &
            (tickets_com_mov['status'].notna()) &
            (~tickets_com_mov['status'].isin(['Fechado', 'Resolvido', 'Cancelado']))
        ].copy()
        tickets_parados['motivo'] = 'Ticket parado sem movimento'
        resultado['tickets_parados'] = tickets_parados[
            ['id', 'titulo', 'categoria', 'status', 'ultima_movimentacao',
             'dias_sem_movimento', 'motivo']
        ]
    else:
        resultado['tickets_parados'] = pd.DataFrame()

    # Violações de SLA: data_resolvido > previsao
    if 'previsao' in tickets.columns and 'data_resolvido' in tickets.columns:
        sla_df = tickets.copy()
        sla_df['data_resolvido'] = pd.to_datetime(sla_df['data_resolvido'], errors='coerce')
        sla_df['previsao'] = pd.to_datetime(sla_df['previsao'], errors='coerce')
        sla_estourado = sla_df[
            (sla_df['data_resolvido'].notna()) &
            (sla_df['previsao'].notna()) &
            (sla_df['data_resolvido'] > sla_df['previsao'])
        ].copy()
        sla_estourado['atraso_horas'] = (
            sla_estourado['data_resolvido'] - sla_estourado['previsao']
        ).dt.total_seconds() / 3600
        sla_estourado['motivo'] = 'SLA estourado'
        resultado['sla_estourado'] = sla_estourado[
            ['id', 'titulo', 'categoria', 'sistema', 'previsao', 'data_resolvido',
             'atraso_horas', 'motivo']
        ]
    else:
        resultado['sla_estourado'] = pd.DataFrame()

    # Tempo médio de resolução por motivo/categoria
    if 'data_resolvido' in tickets.columns and 'criado_data' in tickets.columns:
        tickets_com_resolucao = tickets.copy()
        tickets_com_resolucao['data_resolvido'] = pd.to_datetime(
            tickets_com_resolucao['data_resolvido'], errors='coerce'
        )
        tickets_com_resolucao['criado_data'] = pd.to_datetime(
            tickets_com_resolucao['criado_data'], errors='coerce'
        )
        tickets_com_resolucao = tickets_com_resolucao[
            tickets_com_resolucao['data_resolvido'].notna() &
            tickets_com_resolucao['criado_data'].notna()
        ].copy()
        tickets_com_resolucao['horas_resolucao_calc'] = (
            tickets_com_resolucao['data_resolvido'] - tickets_com_resolucao['criado_data']
        ).dt.total_seconds() / 3600

        col_motivo = 'motivo_real' if 'motivo_real' in tickets.columns else 'categoria'
        tempo_por_motivo = tickets_com_resolucao.groupby(col_motivo)['horas_resolucao_calc'].agg(
            ['mean', 'count', 'min', 'max']
        ).reset_index()
        tempo_por_motivo.columns = ['motivo', 'tempo_medio_horas', 'qtd_tickets',
                                    'tempo_min_horas', 'tempo_max_horas']
        tempo_por_motivo = tempo_por_motivo.sort_values('tempo_medio_horas', ascending=False)
        resultado['tempo_por_motivo'] = tempo_por_motivo.head(15)
    else:
        resultado['tempo_por_motivo'] = pd.DataFrame()

    return resultado


def gerar_recomendacoes(recorrencia, qualidade, operacional):
    """
    Entrega 4: Recomendações inteligentes baseadas nos dados analisados.
    """
    recomendacoes = []

    # 1. Alta recorrência de assunto
    if not recorrencia['ranking_assuntos'].empty:
        top = recorrencia['ranking_assuntos'].iloc[0]
        if top['qtd_tickets'] >= 20:
            recomendacoes.append({
                'tipo': 'Melhoria operacional',
                'prioridade': 'Alta',
                'problema': f"Alta recorrência de '{top['assunto']}'",
                'evidencias': f"{top['qtd_tickets']} tickets ({top['pct']}% do total)",
                'acao_recomendada': (
                    f"Investigar a funcionalidade relacionada a '{top['assunto']}' "
                    "e avaliar necessidade de correção sistêmica ou automação."
                ),
            })

    # 2. Assuntos genéricos
    if not qualidade['assunto_generico'].empty:
        qtd = len(qualidade['assunto_generico'])
        recomendacoes.append({
            'tipo': 'Melhoria de formulário',
            'prioridade': 'Média',
            'problema': 'Assuntos genéricos ou títulos curtos na abertura',
            'evidencias': f"{qtd} tickets com título <30 chars e descrição <50 chars",
            'acao_recomendada': (
                "Revisar o catálogo de assuntos e incluir opções mais específicas "
                "no formulário de abertura, obrigando preenchimento de descrição."
            ),
        })

    # 3. Descrição insuficiente
    if not qualidade['descricao_insuficiente'].empty:
        qtd = len(qualidade['descricao_insuficiente'])
        recomendacoes.append({
            'tipo': 'Melhoria de formulário',
            'prioridade': 'Alta',
            'problema': 'Descrição insuficiente na abertura',
            'evidencias': f"{qtd} tickets com descrição menor que 20 caracteres",
            'acao_recomendada': (
                "Tornar o campo descrição obrigatório com mínimo de caracteres "
                "e adicionar validação no frontend."
            ),
        })

    # 4. SLA estourado
    if not operacional['sla_estourado'].empty:
        qtd = len(operacional['sla_estourado'])
        atraso_medio = operacional['sla_estourado']['atraso_horas'].mean()
        recomendacoes.append({
            'tipo': 'Melhoria operacional',
            'prioridade': 'Alta',
            'problema': 'Violações de SLA',
            'evidencias': f"{qtd} tickets estouraram o prazo, atraso médio de {atraso_medio:.1f}h",
            'acao_recomendada': (
                "Revisar SLAs por categoria e prioridade, e investigar gargalos "
                "nas etapas com maior atraso."
            ),
        })

    # 5. Tickets parados
    if not operacional['tickets_parados'].empty:
        qtd = len(operacional['tickets_parados'])
        recomendacoes.append({
            'tipo': 'Melhoria operacional',
            'prioridade': 'Média',
            'problema': 'Tickets parados sem movimento',
            'evidencias': f"{qtd} tickets sem movimentação há mais de 7 dias",
            'acao_recomendada': (
                "Implementar alerta automático para tickets parados e revisar "
                "filas de atendimento com maior acúmulo."
            ),
        })

    # 6. Reincidência
    if not qualidade['reaberturas'].empty:
        qtd = len(qualidade['reaberturas'])
        recomendacoes.append({
            'tipo': 'Prevenção',
            'prioridade': 'Média',
            'problema': 'Reincidência operacional',
            'evidencias': f"{qtd} reaberturas de tickets identificadas",
            'acao_recomendada': (
                "Investigar tickets reabertos para identificar causas raiz e "
                "avaliar se a resolução inicial foi insuficiente."
            ),
        })

    # 7. Crescimento de ocorrências (se houver evolução mensal)
    if not recorrencia['evolucao_mensal'].empty:
        evo = recorrencia['evolucao_mensal']
        if len(evo) >= 2:
            ultimo = evo.iloc[-1]['qtd_tickets']
            anterior = evo.iloc[-2]['qtd_tickets']
            if anterior > 0:
                cresc = ((ultimo - anterior) / anterior) * 100
                if cresc > 20:
                    recomendacoes.append({
                        'tipo': 'Prevenção',
                        'prioridade': 'Alta',
                        'problema': 'Crescimento significativo de tickets',
                        'evidencias': f"Crescimento de {cresc:.1f}% no último mês",
                        'acao_recomendada': (
                            "Investigar causas do aumento repentino e "
                            "avaliar necessidade de reforço na equipe."
                        ),
                    })

    return pd.DataFrame(recomendacoes)


def salvar_todos(recorrencia, qualidade, operacional, recomendacoes, timestamp):
    """Salva todos os artefatos da Inteligência de Tickets."""
    ARTEFATOS.mkdir(parents=True, exist_ok=True)

    # Recorrência
    recorrencia['ranking_assuntos'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_recorrencia_ranking_{timestamp}.csv',
        index=False, encoding='utf-8'
    )
    recorrencia['evolucao_mensal'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_recorrencia_evolucao_{timestamp}.csv',
        index=False, encoding='utf-8'
    )
    recorrencia['dist_sistema'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_recorrencia_sistema_{timestamp}.csv',
        index=False, encoding='utf-8'
    )
    recorrencia['dist_area'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_recorrencia_area_{timestamp}.csv',
        index=False, encoding='utf-8'
    )
    recorrencia['dist_categoria'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_recorrencia_categoria_{timestamp}.csv',
        index=False, encoding='utf-8'
    )

    # Qualidade
    qualidade['descricao_insuficiente'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_qualidade_descricao_{timestamp}.csv',
        index=False, encoding='utf-8'
    )
    qualidade['assunto_generico'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_qualidade_generico_{timestamp}.csv',
        index=False, encoding='utf-8'
    )
    qualidade['divergencia'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_qualidade_divergencia_{timestamp}.csv',
        index=False, encoding='utf-8'
    )
    qualidade['reaberturas'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_qualidade_reaberturas_{timestamp}.csv',
        index=False, encoding='utf-8'
    )

    # Operacional
    operacional['tickets_parados'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_operacional_parados_{timestamp}.csv',
        index=False, encoding='utf-8'
    )
    operacional['sla_estourado'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_operacional_sla_{timestamp}.csv',
        index=False, encoding='utf-8'
    )
    operacional['tempo_por_motivo'].to_csv(
        ARTEFATOS / f'inteligencia_tickets_operacional_tempo_motivo_{timestamp}.csv',
        index=False, encoding='utf-8'
    )

    # Recomendações
    recomendacoes.to_csv(
        ARTEFATOS / f'inteligencia_tickets_recomendacoes_{timestamp}.csv',
        index=False, encoding='utf-8'
    )

    return timestamp


def main():
    print('🚀 INTELIGÊNCIA DE TICKETS — Geração de dados para o dashboard')
    print('=' * 70)

    print('📂 Carregando dados do banco...')
    tickets, movs, msgs = carregar_dados()
    print(f'   Tickets: {len(tickets)}')
    print(f'   Movimentações: {len(movs)}')
    print(f'   Mensagens: {len(msgs)}')

    print('\n📊 Analisando recorrência (Entrega 1)...')
    recorrencia = analisar_recorrencia(tickets, movs)

    print('\n🔍 Analisando qualidade de abertura (Entrega 2)...')
    qualidade = analisar_qualidade_abertura(tickets, movs, msgs)

    print('\n⚙️  Analisando problemas operacionais (Entrega 3)...')
    operacional = analisar_problemas_operacionais(tickets, movs)

    print('\n💡 Gerando recomendações inteligentes (Entrega 4)...')
    recomendacoes = gerar_recomendacoes(recorrencia, qualidade, operacional)

    print('\n💾 Salvando artefatos...')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    salvar_todos(recorrencia, qualidade, operacional, recomendacoes, timestamp)

    print('\n' + '=' * 70)
    print('RESUMO DA INTELIGÊNCIA DE TICKETS')
    print('=' * 70)
    print(f'   Assuntos distintos: {len(tickets["categoria"].unique())}')
    print(f'   Top assunto: {recorrencia["ranking_assuntos"].iloc[0]["assunto"]} '
          f'({recorrencia["ranking_assuntos"].iloc[0]["qtd_tickets"]} tickets)')
    print(f'   Tickets com descrição insuficiente: {len(qualidade["descricao_insuficiente"])}')
    print(f'   Tickets com assunto genérico: {len(qualidade["assunto_generico"])}')
    print(f'   Tickets parados: {len(operacional["tickets_parados"])}')
    print(f'   SLA estourado: {len(operacional["sla_estourado"])}')
    print(f'   Reaberturas: {len(qualidade["reaberturas"])}')
    print(f'   Recomendações geradas: {len(recomendacoes)}')
    print('\n✅ Inteligência de Tickets concluída.')


if __name__ == '__main__':
    main()
