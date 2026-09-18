# ============================================================
# dashboard/components_grafo.py
# ============================================================
"""
Componente de grafo de roteamento.
- Grafo geral (networkx + pyvis)
- Árvore de encaminhamentos de um ticket (networkx + matplotlib)
"""

import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'


# ==================== CORES ====================
COR_SPPREV = '#c9a666'
COR_ATLANTIC = '#7fc99b'
COR_EXTERNO = '#8b96a8'
COR_OUTRO = '#e0867a'
COR_ARESTA = '#5c6270'
COR_BG = '#141821'
COR_CARD = '#1b2029'
COR_TEXTO = '#eae7e1'
COR_TEXTO_SEC = '#9299a6'


def _cor_por_empresa(empresa):
    if empresa == 'SPPREV':   return COR_SPPREV
    if empresa == 'Atlantic': return COR_ATLANTIC
    if empresa == 'Externo':  return COR_EXTERNO
    return COR_OUTRO


# ==================== GRAFO GERAL (pyvis) ====================
def extrair_encaminhamentos(df_movs, df_analistas, max_nos=20):
    """Extrai pares (origem → destino) das movimentações."""
    mapa_empresa = dict(zip(df_analistas['nome'], df_analistas['empresa_tipo']))

    df = df_movs.dropna(subset=['autor', 'data_movimentacao']).copy()
    df = df.sort_values(['ticket_id', 'data_movimentacao'])

    pares = Counter()

    for _, grupo in df.groupby('ticket_id'):
        autores = grupo['autor'].tolist()
        for i in range(len(autores) - 1):
            origem = autores[i]
            destino = autores[i + 1]
            if origem != destino:
                pares[(origem, destino)] += 1

    nos_frequentes = Counter()
    for (o, d), qtd in pares.items():
        nos_frequentes[o] += qtd
        nos_frequentes[d] += qtd

    top_nos = set(n for n, _ in nos_frequentes.most_common(max_nos))

    resultado = []
    for (o, d), qtd in pares.most_common():
        if o in top_nos and d in top_nos:
            resultado.append({
                'origem': o,
                'destino': d,
                'peso': qtd,
                'empresa_origem': mapa_empresa.get(o, 'Outro'),
                'empresa_destino': mapa_empresa.get(d, 'Outro'),
            })

    return resultado


def criar_grafo(arestas, altura=600):
    """Cria o grafo pyvis."""
    if not arestas:
        return None

    net = Network(
        height=f'{altura}px',
        width='100%',
        bgcolor=COR_BG,
        font_color=COR_TEXTO,
        directed=True,
    )

    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 200,
          "springConstant": 0.04,
          "damping": 0.09
        },
        "stabilization": {"enabled": true, "iterations": 200}
      },
      "nodes": {
        "font": {"size": 14, "color": "#eae7e1", "face": "Inter, sans-serif"},
        "borderWidth": 2,
        "borderWidthSelected": 4
      },
      "edges": {
        "color": {"inherit": false},
        "smooth": {"type": "curvedCW", "roundness": 0.2},
        "arrows": {"to": {"enabled": true, "scaleFactor": 1.2}}
      },
      "interaction": {
        "hover": true, "tooltipDelay": 100, "navigationButtons": true
      }
    }
    """)

    nos = set()
    for a in arestas:
        nos.add((a['origem'], a['empresa_origem']))
        nos.add((a['destino'], a['empresa_destino']))

    peso_por_no = defaultdict(int)
    for a in arestas:
        peso_por_no[a['origem']] += a['peso']
        peso_por_no[a['destino']] += a['peso']

    for nome, empresa in nos:
        peso = peso_por_no[nome]
        tamanho = 15 + min(peso * 1.5, 50)
        cor = _cor_por_empresa(empresa)

        # Abrevia nome
        partes = nome.split()
        label = partes[0] + (' ' + partes[1] if len(partes) > 1 else '')

        net.add_node(
            nome,
            label=label,
            title=f'<b>{nome}</b><br>Empresa: {empresa}<br>Total: {peso}',
            color=cor,
            size=tamanho,
            shape='dot',
            font={'size': 14, 'color': COR_TEXTO},
        )

    for a in arestas:
        peso = a['peso']
        largura = 1 + min(peso * 0.3, 6)

        net.add_edge(
            a['origem'],
            a['destino'],
            value=peso,
            width=largura,
            title=f'{a["origem"]} → {a["destino"]}<br>Encaminhamentos: {peso}',
            color=COR_ARESTA,
            arrows='to',
        )

    try:
        return net.generate_html(notebook=False)
    except TypeError:
        return net.generate_html()


def render_grafo(df_movs, df_analistas, max_nos=20, altura=600):
    """Renderiza o grafo pyvis no Streamlit."""
    if df_movs is None or df_movs.empty:
        st.info('Sem movimentações para exibir.')
        return

    arestas = extrair_encaminhamentos(df_movs, df_analistas, max_nos=max_nos)

    if not arestas:
        st.info('Sem encaminhamentos suficientes para o grafo.')
        return

    html = criar_grafo(arestas, altura=altura)

    if html:
        components.html(html, height=altura + 50, scrolling=False)
    else:
        st.warning('Erro ao gerar o grafo.')


# ==================== LEGENDA ====================
def render_legenda():
    """Legenda do grafo."""
    st.markdown(f'''
        <div style="display: flex; gap: 20px; flex-wrap: wrap;
                    padding: 12px; background: {COR_CARD};
                    border: 1px solid rgba(255,255,255,.07);
                    border-radius: 8px; margin-bottom: 16px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 14px; height: 14px; border-radius: 50%;
                            background: {COR_SPPREV};"></div>
                <span style="font-size: 12px; color: {COR_TEXTO_SEC};">SPPREV</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 14px; height: 14px; border-radius: 50%;
                            background: {COR_ATLANTIC};"></div>
                <span style="font-size: 12px; color: {COR_TEXTO_SEC};">Atlantic</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 14px; height: 14px; border-radius: 50%;
                            background: {COR_EXTERNO};"></div>
                <span style="font-size: 12px; color: {COR_TEXTO_SEC};">Externo</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 14px; height: 14px; border-radius: 50%;
                            background: {COR_OUTRO};"></div>
                <span style="font-size: 12px; color: {COR_TEXTO_SEC};">Outro</span>
            </div>
            <span style="font-size: 12px; color: {COR_TEXTO_SEC};">
                Tamanho do nó = volume · Espessura = qtde
            </span>
        </div>
    ''', unsafe_allow_html=True)


# ==================== ÁRVORE (networkx + matplotlib) ====================
def buscar_ticket(conn, ticket_id):
    """Busca um ticket + suas movimentações."""
    ticket = pd.read_sql('''
        SELECT id, titulo, status, responsavel_atual, solicitante,
               categoria, prioridade, criado_data, alterado_data
        FROM tickets WHERE id = ?
    ''', conn, params=(int(ticket_id),))

    if ticket.empty:
        return None, None

    movs = pd.read_sql('''
        SELECT data_movimentacao, autor, para_status, tipo
        FROM movimentacoes
        WHERE ticket_id = ?
        ORDER BY data_movimentacao ASC
    ''', conn, params=(int(ticket_id),))

    return ticket.iloc[0], movs


def gerar_arvore_ticket_matplotlib(ticket, movs, analistas):
    """
    Gera árvore visual do fluxo do ticket (networkx + matplotlib).
    Layout vertical em cascata, de cima para baixo.
    """
    mapa_emp = dict(zip(analistas['nome'], analistas['empresa_tipo']))

    def cor_empresa(empresa):
        return _cor_por_empresa(empresa)

    # ===== Monta lista ordenada de nós =====
    # Cada item: (label_curto, label_longo, cor)
    nos = []

    # Solicitante
    solicitante = ticket['solicitante'] or 'Solicitante'
    emp_sol = mapa_emp.get(solicitante, 'Outro')

    nos.append({
        'id': 'sol',
        'autor': solicitante,
        'quando': str(ticket['criado_data'])[:16] if ticket['criado_data'] else '',
        'status': 'Solicitação',
        'cor': cor_empresa(emp_sol),
        'tipo': 'solicitante',
    })

    # Movimentações
    if not movs.empty:
        for i, (_, m) in enumerate(movs.iterrows()):
            autor = m['autor'] or 'Desconhecido'
            status = m['para_status'] or '—'
            data = m['data_movimentacao']

            try:
                data_str = pd.to_datetime(data).strftime('%d/%m %H:%M')
            except Exception:
                data_str = str(data)[:16]

            emp = mapa_emp.get(autor, 'Outro')

            nos.append({
                'id': f'm{i}',
                'autor': autor,
                'quando': data_str,
                'status': status,
                'cor': cor_empresa(emp),
                'tipo': 'mov',
            })

    # ===== Desenha com matplotlib =====
    n_nos = len(nos)
    altura_fig = max(8, n_nos * 0.75)
    fig, ax = plt.subplots(figsize=(14, altura_fig))

    fig.patch.set_facecolor(COR_BG)
    ax.set_facecolor(COR_BG)

    # Posições verticais (Y de cima para baixo)
    y_positions = list(range(n_nos))
    y_positions.reverse()  # topo = primeiro nó

    # X: alterna um pouco para dar dinamismo visual
    x_positions = [0.5 + (0.15 if i % 2 == 0 else -0.15) for i in range(n_nos)]
    x_positions[0] = 0.5  # primeiro centralizado

    # Ajusta escala
    ax.set_xlim(-0.3, 1.3)
    ax.set_ylim(-0.5, n_nos - 0.5)
    ax.axis('off')

    # ===== Conectores (linhas entre nós) =====
    for i in range(n_nos - 1):
        x1, y1 = x_positions[i], y_positions[i]
        x2, y2 = x_positions[i + 1], y_positions[i + 1]

        # Linha vertical
        ax.annotate(
            '',
            xy=(x2, y2 + 0.35),
            xytext=(x1, y1 - 0.35),
            arrowprops=dict(
                arrowstyle='-|>',
                color=COR_ARESTA,
                lw=1.8,
                connectionstyle='arc3,rad=0.05',
            ),
        )

    # ===== Nós =====
    for i, no in enumerate(nos):
        x, y = x_positions[i], y_positions[i]

        # Círculo
        circle = plt.Circle(
            (x, y), radius=0.13,
            facecolor=no['cor'],
            edgecolor='#eae7e1',
            linewidth=1.5,
            zorder=2,
        )
        ax.add_patch(circle)

        # Inicial do nome (dentro do círculo)
        inicial = no['autor'].split()[0][0].upper()
        ax.text(
            x, y, inicial,
            ha='center', va='center',
            fontsize=14, fontweight='bold',
            color='#141821',
            zorder=3,
        )

        # Box de informação ao lado
        info_box = (
            f"{no['autor']}\n"
            f"{no['quando']}\n"
            f"→ {no['status']}"
        )

        # Alinha do lado oposto para dar ritmo visual
        if i % 2 == 0:
            # Texto à direita
            ax.text(
                x + 0.18, y, info_box,
                ha='left', va='center',
                fontsize=8.5,
                color=COR_TEXTO,
                zorder=3,
                bbox=dict(
                    boxstyle='round,pad=0.4',
                    facecolor=COR_CARD,
                    edgecolor=no['cor'],
                    linewidth=1,
                    alpha=0.95,
                ),
            )
        else:
            # Texto à esquerda
            ax.text(
                x - 0.18, y, info_box,
                ha='right', va='center',
                fontsize=8.5,
                color=COR_TEXTO,
                zorder=3,
                bbox=dict(
                    boxstyle='round,pad=0.4',
                    facecolor=COR_CARD,
                    edgecolor=no['cor'],
                    linewidth=1,
                    alpha=0.95,
                ),
            )

    plt.tight_layout()
    return fig


def render_arvore_ticket(ticket_id, conn, df_analistas):
    """Renderiza a árvore de um ticket no Streamlit (sem Graphviz)."""
    ticket, movs = buscar_ticket(conn, ticket_id)

    if ticket is None:
        st.warning(f'❌ Ticket #{ticket_id} não encontrado.')
        return

    # ===== CABEÇALHO DO TICKET =====
    st.markdown(f'''
        <div style="background: {COR_CARD};
                    border: 1px solid rgba(255,255,255,.07);
                    border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <div style="font-family: Fraunces, serif; font-size: 18px;
                        color: {COR_TEXTO}; margin-bottom: 8px;">
                #{ticket['id']} — {ticket['titulo'][:70] if ticket['titulo'] else 'Sem título'}
            </div>
            <div style="display: flex; gap: 20px; flex-wrap: wrap;
                        font-size: 12px; color: {COR_TEXTO_SEC};">
                <span>📊 Status: <b style="color:{COR_TEXTO};">{ticket['status']}</b></span>
                <span>👤 Resp.: <b style="color:{COR_TEXTO};">{ticket['responsavel_atual'] or '—'}</b></span>
                <span>🏷️ Categoria: <b style="color:{COR_TEXTO};">{ticket['categoria'] or '—'}</b></span>
                <span>⚡ Prioridade: <b style="color:{COR_TEXTO};">{ticket['prioridade'] or '—'}</b></span>
            </div>
        </div>
    ''', unsafe_allow_html=True)

    if movs.empty:
        st.info('Sem movimentações registradas para este ticket.')
        return

    # Resumo das movimentações
    st.markdown(f'**📋 {len(movs)} movimentações registradas**')

    # Gera e renderiza a árvore
    try:
        fig = gerar_arvore_ticket_matplotlib(ticket, movs, df_analistas)
        st.pyplot(fig)
        plt.close(fig)  # Libera memória
    except Exception as e:
        st.error(f'❌ Erro ao renderizar árvore: {e}')
        # Fallback: mostra tabela
        st.dataframe(movs, use_container_width=True, hide_index=True)