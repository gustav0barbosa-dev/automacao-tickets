# ============================================================
# dashboard/views/tendencias.py
# ============================================================

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
    botao_exportar, legenda_grafico, info_grafico,
)
from config import (
    COR_GOLD, COR_BAR, COR_SUCCESS, COR_DANGER,
    COR_WARNING, COR_TEXT_SEC, STATUS_FECHADOS,
)


def render(df):
    page_header('Tendências', 'e Evolução',
                'Análise temporal: volume, SLA e aging ao longo do tempo.')

    # ---------- Filtra por criado_data válido ----------
    df_temp = df[df['criado_data'].notna()].copy()

    if df_temp.empty:
        callout('warning', 'Atenção', 'Sem dados temporais no período.')
        return

    # ---------- Cria colunas derivadas ----------
    df_temp['mes'] = df_temp['criado_data'].dt.to_period('M').astype(str)
    df_temp['ano'] = df_temp['criado_data'].dt.year
    df_temp['dia_semana'] = df_temp['criado_data'].dt.day_name()
    df_temp['hora'] = df_temp['criado_data'].dt.hour

    # Ordem dos dias
    ordem_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                  'Saturday', 'Sunday']
    nomes_pt = {
        'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
        'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado',
        'Sunday': 'Domingo',
    }

    # ---------- KPIs ----------
    total = len(df_temp)
    df_aberto = df_temp[~df_temp['status'].isin(STATUS_FECHADOS)]
    df_resolvido = df_temp[df_temp['data_resolvido'].notna()]

    # Período coberto
    data_min = df_temp['criado_data'].min()
    data_max = df_temp['criado_data'].max()
    dias_cobertos = (data_max - data_min).days

    # Mês mais ativo
    mes_ativo = df_temp['mes'].value_counts().index[0] if not df_temp.empty else '—'
    tickets_mes_ativo = df_temp['mes'].value_counts().iloc[0] if not df_temp.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Total no Período', f'{total}')
    with col2:
        kpi('Meses Cobertos', f'{dias_cobertos // 30}')
    with col3:
        kpi('Mês Mais Ativo', mes_ativo,
            pill=f'{tickets_mes_ativo} tickets')
    with col4:
        media_mes = total / max(dias_cobertos // 30, 1)
        kpi('Média/Mês', f'{media_mes:.0f}')

    separador()

    # ---------- Volume por Mês ----------
    painel_title('Volume de Tickets por <b>Mês</b>')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Todos os tickets criados no período</div>',
                unsafe_allow_html=True)

    volume_mes = df_temp.groupby('mes').size().reset_index(name='qtd')
    volume_mes = volume_mes.sort_values('mes').tail(24)  # últimos 24 meses

    if not volume_mes.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=volume_mes['mes'],
            y=volume_mes['qtd'],
            marker_color=COR_GOLD,
            text=volume_mes['qtd'],
            textposition='outside',
            name='Tickets criados',
        ))
        fig.update_layout(
            height=320,
            xaxis_title='',
            yaxis_title='Tickets',
            xaxis_tickangle=-45,
        )
        fig = aplicar_tema_plotly(fig, altura=320)
        st.plotly_chart(fig, use_container_width=True,
                        config={'displayModeBar': False})

        legenda_grafico([
            {'cor': COR_GOLD, 'label': 'Tickets criados', 'tipo': 'barra'},
        ])

    separador()

    # ---------- Criados vs Resolvidos ----------
    painel_title('Criados vs <b>Resolvidos</b>')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Estamos dando conta da demanda?</div>',
                unsafe_allow_html=True)

    criados = df_temp.groupby('mes').size().reset_index(name='criados')

    # Resolvidos por mês (usa data_resolvido)
    if 'data_resolvido' in df_temp.columns:
        df_res = df_temp[df_temp['data_resolvido'].notna()].copy()
        if not df_res.empty:
            df_res['mes_resolvido'] = df_res['data_resolvido'].dt.to_period('M').astype(str)
            resolvidos = df_res.groupby('mes_resolvido').size().reset_index(name='resolvidos')
            resolvidos.columns = ['mes', 'resolvidos']

            comparativo = criados.merge(resolvidos, on='mes', how='outer').fillna(0)
            comparativo = comparativo.sort_values('mes').tail(24)

            if not comparativo.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=comparativo['mes'], y=comparativo['criados'],
                    mode='lines+markers',
                    line=dict(color=COR_GOLD, width=2),
                    marker=dict(color=COR_GOLD, size=6),
                    name='Criados',
                ))
                fig.add_trace(go.Scatter(
                    x=comparativo['mes'], y=comparativo['resolvidos'],
                    mode='lines+markers',
                    line=dict(color=COR_SUCCESS, width=2),
                    marker=dict(color=COR_SUCCESS, size=6),
                    name='Resolvidos',
                ))
                fig.update_layout(
                    height=350,
                    xaxis_title='',
                    yaxis_title='Tickets',
                    xaxis_tickangle=-45,
                    showlegend=True,
                    legend=dict(
                        orientation='h',
                        yanchor='bottom', y=1.02,
                        xanchor='right', x=1,
                        font=dict(color=COR_TEXT_SEC),
                    ),
                )
                fig = aplicar_tema_plotly(fig, altura=350)
                fig.update_layout(showlegend=True)
                st.plotly_chart(fig, use_container_width=True,
                                config={'displayModeBar': False})

                # Alerta de saldo
                ultimos_3 = comparativo.tail(3)
                if not ultimos_3.empty:
                    saldo = (ultimos_3['criados'] - ultimos_3['resolvidos']).mean()
                    if saldo > 5:
                        callout('warning', 'Atenção',
                                f'Backlog crescendo: em média <b>+{saldo:.0f} tickets/mês</b> '
                                f'nos últimos 3 meses.')
                    elif saldo < -5:
                        callout('success', 'OK',
                                f'Reduzindo backlog: média de <b>{saldo:.0f} tickets/mês</b>.')
                    else:
                        callout('info', 'Insight',
                                f'Balanço estável (média: {saldo:+.0f}/mês).')

        legenda_grafico([
            {'cor': COR_GOLD, 'label': 'Criados', 'tipo': 'linha'},
            {'cor': COR_SUCCESS, 'label': 'Resolvidos', 'tipo': 'linha'},
        ])
        info_grafico(
            'Se a linha de <b>criados</b> estiver acima da de <b>resolvidos</b>, '
            'o backlog está crescendo.'
        )

    separador()

    # ---------- SLA por Mês ----------
    painel_title('SLA Cumprido por <b>Mês</b>')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Estamos melhorando com o tempo?</div>',
                unsafe_allow_html=True)

    if 'sla_status' in df_temp.columns:
        df_sla_temp = df_temp[df_temp['sla_status'].isin(['cumprido', 'estourado'])].copy()
        if not df_sla_temp.empty:
            sla_mes = df_sla_temp.groupby('mes').agg(
                total=('id', 'count'),
                cumpridos=('sla_status', lambda x: (x == 'cumprido').sum()),
            ).reset_index()
            sla_mes['perc'] = (sla_mes['cumpridos'] / sla_mes['total'] * 100).round(1)
            sla_mes = sla_mes.sort_values('mes').tail(24)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=sla_mes['mes'], y=sla_mes['perc'],
                mode='lines+markers',
                line=dict(color=COR_SUCCESS, width=3),
                marker=dict(color=COR_SUCCESS, size=8),
                fill='tozeroy',
                fillcolor='rgba(127,201,155,.15)',
                name='% SLA',
            ))
            fig.add_hline(y=95, line_dash='dash',
                          line_color=COR_GOLD,
                          annotation_text='Meta 95%',
                          annotation_position='top right')
            fig.update_layout(
                height=320,
                xaxis_title='',
                yaxis_title='% SLA cumprido',
                xaxis_tickangle=-45,
                yaxis_range=[0, 105],
            )
            fig = aplicar_tema_plotly(fig, altura=320)
            st.plotly_chart(fig, use_container_width=True,
                            config={'displayModeBar': False})

        legenda_grafico([
            {'cor': COR_SUCCESS, 'label': '% SLA cumprido', 'tipo': 'linha'},
            {'cor': COR_GOLD, 'label': 'Meta (95%)', 'tipo': 'linha'},
        ])

    separador()

    # ---------- Volume por Dia da Semana ----------
    col_a, col_b = st.columns(2)

    with col_a:
        painel_title('Volume por <b>Dia da Semana</b>')

        by_dia = df_temp.groupby('dia_semana').size().reset_index(name='qtd')
        by_dia['ordem'] = by_dia['dia_semana'].map(
            {d: i for i, d in enumerate(ordem_dias)}
        )
        by_dia = by_dia.sort_values('ordem')
        by_dia['dia_pt'] = by_dia['dia_semana'].map(nomes_pt)

        if not by_dia.empty:
            hbar_list([
                {'label': r['dia_pt'],
                 'value': int(r['qtd']),
                 'formatted': str(int(r['qtd'])),
                 'accent': r['qtd'] == by_dia['qtd'].max()}
                for _, r in by_dia.iterrows()
            ])

    with col_b:
        painel_title('Volume por <b>Hora</b>')

        by_hora = df_temp.groupby('hora').size().reset_index(name='qtd')
        # Agrupa em faixas de 2h
        by_hora['faixa'] = (by_hora['hora'] // 2) * 2
        by_hora_agr = by_hora.groupby('faixa')['qtd'].sum().reset_index()
        by_hora_agr = by_hora_agr.sort_values('faixa')

        if not by_hora_agr.empty:
            hbar_list([
                {'label': f'{int(r["faixa"]):02d}h - {int(r["faixa"])+1:02d}h',
                 'value': int(r['qtd']),
                 'formatted': str(int(r['qtd'])),
                 'accent': r['qtd'] == by_hora_agr['qtd'].max()}
                for _, r in by_hora_agr.iterrows()
            ])

    separador()

    # ---------- Comparativo YoY ----------
    painel_title('Comparativo <b>Ano a Ano</b>')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Este ano vs. mesmo período do ano anterior</div>',
                unsafe_allow_html=True)

    yoy = df_temp.groupby(['ano', 'mes']).size().reset_index(name='qtd')
    yoy['mes_num'] = pd.to_datetime(yoy['mes'] + '-01').dt.month
    yoy = yoy.sort_values(['ano', 'mes_num'])

    if yoy['ano'].nunique() >= 2:
        # Pega os 2 últimos anos
        anos = sorted(yoy['ano'].unique())[-2:]
        yoy_filt = yoy[yoy['ano'].isin(anos)]

        fig = go.Figure()
        cores = [COR_TEXT_SEC, COR_GOLD]
        for i, ano in enumerate(anos):
            dados_ano = yoy_filt[yoy_filt['ano'] == ano]
            fig.add_trace(go.Scatter(
                x=dados_ano['mes_num'],
                y=dados_ano['qtd'],
                mode='lines+markers',
                line=dict(color=cores[i], width=2),
                marker=dict(color=cores[i], size=7),
                name=str(ano),
            ))

        fig.update_layout(
            height=320,
            xaxis=dict(
                title='Mês',
                tickmode='array',
                tickvals=list(range(1, 13)),
                ticktext=['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                          'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
            ),
            yaxis_title='Tickets',
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom', y=1.02,
                xanchor='right', x=1,
                font=dict(color=COR_TEXT_SEC),
            ),
        )
        fig = aplicar_tema_plotly(fig, altura=320)
        fig.update_layout(showlegend=True)
        st.plotly_chart(fig, use_container_width=True,
                        config={'displayModeBar': False})
    else:
        callout('info', 'Info',
                'Dados insuficientes para comparativo YoY (menos de 2 anos).')

        legenda_grafico([
            {'cor': COR_TEXT_SEC, 'label': 'Ano anterior', 'tipo': 'linha'},
            {'cor': COR_GOLD, 'label': 'Ano atual', 'tipo': 'linha'},
        ])

    separador()

    # ---------- Insights ----------
    st.markdown('### 💡 Insights')

    # Mês mais ativo
    if not volume_mes.empty:
        top_mes = volume_mes.loc[volume_mes['qtd'].idxmax()]
        callout('info', 'Pico',
                f'Mês com mais tickets: <b>{top_mes["mes"]}</b> '
                f'({int(top_mes["qtd"])} tickets).')

    # Melhor e pior mês de SLA
    if 'sla_status' in df_temp.columns and not df_sla_temp.empty:
        sla_sorted = sla_mes.dropna(subset=['perc'])
        if not sla_sorted.empty:
            melhor = sla_sorted.loc[sla_sorted['perc'].idxmax()]
            pior = sla_sorted.loc[sla_sorted['perc'].idxmin()]
            callout('info', 'SLA',
                    f'Melhor mês: <b>{melhor["mes"]}</b> ({melhor["perc"]:.1f}%). '
                    f'Pior mês: <b>{pior["mes"]}</b> ({pior["perc"]:.1f}%).')

    # Dia mais ativo
    if not by_dia.empty:
        top_dia = by_dia.loc[by_dia['qtd'].idxmax()]
        callout('info', 'Dia da Semana',
                f'<b>{top_dia["dia_pt"]}</b> é o dia mais ativo '
                f'({int(top_dia["qtd"])} tickets).')

    separador()

    # ---------- Botão Exportar ----------
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(df_temp, 'tendencias', key='export_tendencias')