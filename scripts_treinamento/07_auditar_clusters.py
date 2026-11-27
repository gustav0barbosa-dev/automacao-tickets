# scripts_treinamento/07_auditar_clusters.py
"""
Etapa 1 — Auditoria de qualidade semântica dos 112 clusters emergentes.

Objetivo: classificar os clusters por coerência aparente, identificar agrupamentos
misturados, redundantes, analisar ruído e sugerir novos motivos para a taxonomia.

NÃO altera regras hierárquicas nem treina modelo nesta etapa. É pura auditoria de
dados para estabelecer a referência de desempenho atual.

Saídas:
  - scripts_treinamento/artefatos/auditoria_clusters_YYYYMMDD_HHMMSS.xlsx
      uma linha por cluster com: id, quantidade, coerência, categoria predominante,
      assunto sugerido, termos, exemplos representativos, exemplos divergentes,
      ação recomendada.
  - scripts_treinamento/artefatos/analise_ruido_YYYYMMDD_HHMMSS.xlsx
      análise dos tickets classificados como ruído (-1).
  - scripts_treinamento/artefatos/especificacao_interface_YYYYMMDD_HHMMSS.txt
      especificação dos dados necessários para a interface Streamlit.

Não quebra nada do pipeline nem do dashboard. Mudança aditiva.
"""

import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
import re
from collections import Counter

RAIZ = Path(__file__).resolve().parent.parent
ARTEFATOS = RAIZ / 'scripts_treinamento' / 'artefatos'


# ==================== CARREGAMENTO ====================


def encontrar_relatorio_clusters_mais_recente():
    candidatos = sorted(
        ARTEFATOS.glob('grupos_emergentes_*.xlsx'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidatos:
        raise FileNotFoundError(
            f'Não encontrou grupos_emergentes em {ARTEFATOS}. '
            'Rode primeiro 06_descobrir_grupos.py.'
        )
    return candidatos[0]


def encontrar_rotulos_mais_recentes():
    fixo = ARTEFATOS / 'rotulos_fracos.csv'
    if fixo.exists():
        return fixo
    candidatos = sorted(
        ARTEFATOS.glob('rotulos_fracos_*.csv'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidatos:
        return candidatos[0]
    raise FileNotFoundError(
        f'Não encontrou rotulos_fracos em {ARTEFATOS}.'
    )


# ==================== MÉTRICAS DE COERÊNCIA ====================


def classificar_coerencia(n_tickets, n_categorias_dominantes, termos_top, share_categoria_principal=None):
    """
    Classifica coerência em: alta, média, baixa.
    Regras heurísticas baseadas em:
      - tamanho do cluster (quanto maior, mais relevante)
      - nº de categorias dominantes (1 = alta coerência, >3 = misturado)
      - termos top (se dominados por stopwords administrativas = baixa)
      - share da categoria principal (proporção de tickets da categoria mais frequente)
    """
    stopwords_admin = {
        'de', 'do', 'da', 'em', 'que', 'para', 'com', 'por', 'ao', 'aos',
        'às', 'um', 'uma', 'os', 'as', 'e', 'não', 'sem', 'se', 'ser',
        'ticket', 'ref', 'protocolo', 'mensagem', 'erro', 'solicitação',
    }
    termos_limpos = [t for t in termos_top if t.lower() not in stopwords_admin]
    termos_semanticos = len(termos_limpos)

    # Alta coerência: cluster grande, categoria principal domina (>60%), termos semânticos claros
    if (n_tickets >= 30 and termos_semanticos >= 3 and
            (share_categoria_principal is None or share_categoria_principal >= 0.60)):
        return 'alta'
    # Média coerência: tamanho médio, pelo menos 1 termo semântico, categoria principal razoavelmente dominante
    if (n_tickets >= 15 and termos_semanticos >= 1 and
            (share_categoria_principal is None or share_categoria_principal >= 0.40)):
        return 'média'
    return 'baixa'


def eh_cluster_misturado(categorias_dominantes):
    """True se o cluster tem mais de 2 categorias dominantes relevantes."""
    return len(categorias_dominantes) > 2


def extrair_categorias_dominantes(campo_categorias):
    """Extrai lista de categorias a partir do campo 'categoria (qtd) | categoria2 (qtd)'. """
    if not campo_categorias or pd.isna(campo_categorias):
        return []
    partes = str(campo_categorias).split(' | ')
    categorias = []
    for parte in partes:
        parte = parte.strip()
        if '(' in parte:
            nome = parte.split('(')[0].strip()
        else:
            nome = parte
        if nome:
            categorias.append(nome)
    return categorias


def detectar_redundancia(termo_sugerido, termo_outro):
    """
    Heurística simples: se dois motivos sugeridos compartilham 2+ termos
    significativos, podem ser redundantes.
    """
    t1 = set(termo_sugerido.lower().split(' + '))
    t2 = set(termo_outro.lower().split(' + '))
    significativo = lambda x: x.strip() not in {'de', 'do', 'da', 'em', 'que', 'para'}
    t1_sig = {t for t in t1 if significativo(t)}
    t2_sig = {t for t in t2 if significativo(t)}
    intersecao = t1_sig.intersection(t2_sig)
    return len(intersecao) >= 2


# ==================== AUDITORIA ====================


def auditar_clusters(df_relatorio, df_rotulados, coluna_texto='texto_retrospectivo'):
    resultados = []

    for _, row in df_relatorio.iterrows():
        cluster_id = row['cluster_id']
        n_tickets = row['n_tickets']
        termos_raw = str(row.get('terros_caracteristicos', '') or '')
        termos_top = [t.split(' (')[0].strip() for t in termos_raw.split(' | ') if t.strip()]

        # Tickets desse cluster
        sub = df_rotulados[df_rotulados.get('cluster_id') == cluster_id] if 'cluster_id' in df_rotulados.columns else pd.DataFrame()
        if sub.empty:
            sub = pd.DataFrame()

        # Categorias dominantes: usa dados reais dos tickets vinculados, com fallback para o campo do relatório
        categorias_dominantes = []
        if not sub.empty and 'categoria' in sub.columns:
            cats = sub['categoria'].value_counts().head(3)
            categorias_dominantes = [f'{c} ({q})' for c, q in cats.items()]
            n_cats = len(categorias_dominantes)
            # Share da categoria principal (proporção de tickets da categoria mais frequente)
            total_sub = len(sub)
            share_principal = float(cats.iloc[0]) / total_sub if total_sub > 0 else 0.0
        elif 'categorias_dominantes' in row.index and pd.notna(row['categorias_dominantes']):
            categorias_dominantes = extrair_categorias_dominantes(row['categorias_dominantes'])
            n_cats = len(categorias_dominantes)
            share_principal = None
        else:
            n_cats = 0
            share_principal = None

        coerencia = classificar_coerencia(n_tickets, n_cats, termos_top, share_principal)

        # Exemplos representativos e divergentes
        exemplos_rep = str(row.get('exemplos_titulos', '') or '')
        exemplos_rep_list = [e.strip() for e in exemplos_rep.split(' | ') if e.strip()][:3]

        exemplos_div = ''
        if not sub.empty:
            sub_div = sub.sample(n=min(3, len(sub)), random_state=42)
            exemplos_div_list = [str(t)[:80] for t in sub_div['titulo'].tolist() if pd.notna(t)]
            exemplos_div = ' | '.join(exemplos_div_list[:3])

        # Ação recomendada: usa share real da categoria principal, não apenas nº de categorias listadas
        misturado = eh_cluster_misturado(categorias_dominantes)
        # Se a categoria principal representa > 60% do cluster, não é "misturado" mesmo tendo 2-3 categorias listadas
        eh_dominada = (share_principal is not None and share_principal >= 0.60)
        if coerencia == 'alta' and not (misturado and not eh_dominada):
            acao = 'Aprovar motivo'
        elif coerencia == 'média' and not (misturado and not eh_dominada):
            acao = 'Aprovar com revisão leve'
        elif misturado and not eh_dominada:
            acao = 'Dividir cluster'
        else:
            acao = 'Descartar ou revisar termos'

        resultados.append({
            'cluster_id': cluster_id,
            'tipo': row.get('tipo', 'cluster'),
            'n_tickets': n_tickets,
            'coerencia': coerencia,
            'categorias_dominantes': ' | '.join(categorias_dominantes),
            'assunto_sugerido': row.get('motivo_sugerido', ''),
            'termos_caracteristicos': termos_raw[:200],
            'exemplos_representativos': ' | '.join(exemplos_rep_list),
            'exemplos_divergentes': exemplos_div,
            'acao_recomendada': acao,
        })

    return pd.DataFrame(resultados)


def analisar_ruido(df_rotulados, coluna_texto='texto_retrospectivo', amostra=150):
    """Analisa tickets classificados como ruído (cluster_id == -1)."""
    if 'cluster_id' in df_rotulados.columns:
        ruido = df_rotulados[df_rotulados['cluster_id'] == -1].copy()
    else:
        ruido = pd.DataFrame()

    if ruido.empty:
        # fallback: tickets rotulados como 'outros' que não entraram em cluster
        ruido = df_rotulados[df_rotulados['motivo_id'] == 'outros'].head(amostra).copy()
    else:
        ruido = ruido.head(amostra).copy()

    ruido['tamanho_texto'] = ruido[coluna_texto].apply(lambda x: len(str(x or '')))
    ruido['tem_protocolo'] = ruido[coluna_texto].apply(
        lambda x: bool(re.search(r'\b\d{6,10}\b', str(x or '')))
    )
    ruido['tem_sigeprev'] = ruido[coluna_texto].apply(
        lambda x: bool(re.search(r'sigeprev', str(x or ''), re.IGNORECASE))
    )
    ruido['tem_erro'] = ruido[coluna_texto].apply(
        lambda x: bool(re.search(r'erro|falha|não funciona|nao funciona', str(x or ''), re.IGNORECASE))
    )

    resumo = {
        'total_ruido': len(ruido) if 'cluster_id' in df_rotulados.columns else len(ruido),
        'amostra_analisada': len(ruido),
        'tamanho_medio_texto': round(ruido['tamanho_texto'].mean(), 1) if len(ruido) else 0,
        'pct_com_protocolo': round(ruido['tem_protocolo'].mean() * 100, 1) if len(ruido) else 0,
        'pct_com_sigeprev': round(ruido['tem_sigeprev'].mean() * 100, 1) if len(ruido) else 0,
        'pct_com_erro': round(ruido['tem_erro'].mean() * 100, 1) if len(ruido) else 0,
    }
    return ruido, resumo


def sugerir_novos_motivos(df_auditoria, top_n=15):
    """Sugere novos motivos a partir de clusters coerentes não misturados.
    Considera coerência 'alta' ou 'média' com tamanho razoável e sem mistura de categorias."""
    candidatos = df_auditoria[
        (df_auditoria['coerencia'].isin(['alta', 'média'])) &
        (~df_auditoria['categorias_dominantes'].str.contains(r'\|', regex=False)) &
        (df_auditoria['n_tickets'] >= 15) &
        (df_auditoria['acao_recomendada'].isin(['Aprovar motivo', 'Revisar exemplos divergentes']))
    ].copy()

    candidatos = candidatos.sort_values('n_tickets', ascending=False).head(top_n)
    sugestoes = []
    for _, row in candidatos.iterrows():
        sugestoes.append({
            'motivo_sugerido': row['assunto_sugerido'],
            'categoria_origem': row['categorias_dominantes'].split(' (')[0] if row['categorias_dominantes'] else 'outros',
            'qtd_tickets': row['n_tickets'],
            'coerencia': row['coerencia'],
            'termos': row['termos_caracteristicos'],
            'exemplos': row['exemplos_representativos'],
            'acao': 'Adicionar à taxonomia',
        })
    return pd.DataFrame(sugestoes)


# ==================== ESPECIFICAÇÃO DA INTERFACE ====================


def gerar_especificacao_interface():
    espec = """
================================================================================
ESPECIFICAÇÃO DOS DADOS PARA A INTERFACE STREAMLIT (Etapa 2)
================================================================================

1. ESTRUTURA DE DADOS DE ENTRADA (saída desta auditoria)

Tabela 1 — clusters_auditoria (uma linha por cluster):
- cluster_id: identificador do cluster
- n_tickets: quantidade de tickets no cluster
- coerencia: 'alta' | 'média' | 'baixa'
- categorias_dominantes: categoria(s) predominante(s) com contagem
- assunto_sugerido: texto curto baseado nos termos característicos
- termos_caracteristicos: top termos (c-TF-IDF)
- exemplos_representativos: até 3 títulos de tickets do cluster
- exemplos_divergentes: até 3 títulos que não se encaixam bem
- acao_recomendada: 'Aprovar motivo' | 'Revisar exemplos divergentes' |
                      'Dividir cluster' | 'Descartar ou revisar termos'

Tabela 2 — tickets_com_cluster (uma linha por ticket):
- ticket_id: identificador interno do ticket (anonimizado, OK para exibir)
- categoria: categoria declarada no banco
- cluster_id: cluster ao qual pertence (-1 = ruído)
- titulo: título do ticket (já anonimizado)
- texto_retrospectivo: texto completo já anonimizado
- motivo_atribuido_regras: motivo pelas regras frágeis
- distancia_ao_centroide: (opcional, Fase 4) distância semântica ao centro do cluster
- eh_divergente: booleano se o ticket é divergente dentro do cluster

2. QUATRO FILAS DE REVISÃO

Fila 1 — Alta confiança (prioridade baixa)
- Clusters com coerência 'alta' e ação 'Aprovar motivo'
- Exemplo em lote: analista aprova todo o cluster de uma vez

Fila 2 — Divergência (prioridade alta)
- Tickets onde regras classificam como categoria X, mas o cluster aponta categoria Y
- Ou tickets com exemplos_divergentes preenchidos

Fila 3 — Baixa confiança (prioridade alta)
- Clusters com coerência 'baixa'
- Tickets com texto curto (< 50 chars) ou sem contexto suficiente

Fila 4 — Assunto emergente (exploração)
- Clusters ainda não aprovados, com coerência 'média' ou 'alta'
- Ruído com padrões recorrentes (protocolo, sigeprev, erro)

3. DECISÕES DO ANALISTA

Por cluster:
- Aprovar motivo → cria/atualiza motivo na taxonomia
- Dividir cluster → gera sub-clusters para revisão posterior
- Descartar → remove do catálogo de motivos candidatos
- Revisar exemplos divergentes → marca tickets individuais para Fila 2

Por ticket individual:
- motivo_correto: texto livre ou seleção da taxonomia
- observacao: campo livre
- não é possível determinar: checkbox para não forçar escolha

4. ANONIMIZAÇÃO E CONTROLE DE ACESSO

- Todos os textos já passaram por anonimização LGPD (src/utils_anonimizacao.py)
  antes de chegar aos artefatos: CPF→00000000000, nomes→iniciais,
  telefones→0000000000, anexos→<ARQUIVO>.
- ticket_id pode ser exibido (identificador interno, não dado pessoal).
- Antes de disponibilizar a interface para múltiplos analistas, aplicar
  controle de acesso por perfil (ADMIN vs analista vs apenas-leitura).

5. INDICADORES DE QUALIDADE (para a Fase 5)

- Coerência média dos clusters aprovados
- % de clusters divididos vs aprovados
- Taxa de concordância analista × sugestão automática
- Nº de novos motivos adicionados à taxonomia

================================================================================
"""
    return espec


# ==================== MAIN ====================


def main():
    clusters_path = encontrar_relatorio_clusters_mais_recente()
    rotulos_path = encontrar_rotulos_mais_recentes()

    print(f'📂 Clusters: {clusters_path.name}')
    print(f'📂 Rotulados: {rotulos_path.name}')

    df_clusters = pd.read_excel(clusters_path)
    df_rotulados = pd.read_csv(rotulos_path)

    print(f'📊 Clusters no relatório: {len(df_clusters)}')
    print(f'📊 Tickets rotulados: {len(df_rotulados)}')

    # Adicionar cluster_id ao df_rotulados se existir arquivo de IDs
    ids_clusters_path = ARTEFATOS / 'tickets_clusters_*.csv'
    candidatos_ids = sorted(ARTEFATOS.glob('tickets_clusters_*.csv'),
                            key=lambda p: p.stat().st_mtime, reverse=True)
    if candidatos_ids:
        df_ids = pd.read_csv(candidatos_ids[0])
        print(f'🔗 Vinculando tickets a clusters via {candidatos_ids[0].name}')
        df_rotulados = df_rotulados.merge(df_ids, on='id', how='left')
        # O arquivo tickets_clusters tem coluna 'cluster' (HDBSCAN); renomear para cluster_id
        if 'cluster' in df_rotulados.columns and 'cluster_id' not in df_rotulados.columns:
            df_rotulados = df_rotulados.rename(columns={'cluster': 'cluster_id'})

    ARTEFATOS.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # ============================================================
    # 1. AUDITORIA DOS CLUSTERS
    # ============================================================
    print('\n' + '=' * 70)
    print('AUDITORIA DE COERÊNCIA DOS CLUSTERS')
    print('=' * 70)

    df_auditoria = auditar_clusters(df_clusters, df_rotulados)

    resumo_coerencia = df_auditoria['coerencia'].value_counts()
    print('\nDistribuição por coerência:')
    for c, q in resumo_coerencia.items():
        print(f'   {c}: {q} clusters')

    resumo_acao = df_auditoria['acao_recomendada'].value_counts()
    print('\nDistribuição por ação recomendada:')
    for a, q in resumo_acao.items():
        print(f'   {a}: {q} clusters')

    # Clusters misturados
    misturados = df_auditoria[df_auditoria['categorias_dominantes'].str.contains(r'\|', regex=False)]
    print(f'\n⚠️  Clusters misturados (múltiplas categorias): {len(misturados)}')
    for _, row in misturados.head(10).iterrows():
        print(f"   Cluster {row['cluster_id']} ({row['n_tickets']} tickets): {row['categorias_dominantes']}")

    # Salvar auditoria
    caminho_auditoria = ARTEFATOS / f'auditoria_clusters_{timestamp}.xlsx'
    try:
        df_auditoria.to_excel(caminho_auditoria, index=False, engine='openpyxl')
        print(f'\n💾 Auditoria de clusters salva: {caminho_auditoria}')
    except Exception as e:
        caminho_csv = caminho_auditoria.with_suffix('.csv')
        df_auditoria.to_csv(caminho_csv, index=False, encoding='utf-8')
        print(f'⚠️  Não foi possível salvar XLSX ({e}). Salvando CSV: {caminho_csv}')
        caminho_auditoria = caminho_csv

    # ============================================================
    # 2. ANÁLISE DO RUÍDO
    # ============================================================
    print('\n' + '=' * 70)
    print('ANÁLISE DO RUÍDO (tickets sem cluster)')
    print('=' * 70)

    df_ruido, resumo_ruido = analisar_ruido(df_rotulados)
    print(f'   Total de tickets em ruído: {resumo_ruido["total_ruido"]}')
    print(f'   Amostra analisada: {resumo_ruido["amostra_analisada"]}')
    print(f'   Tamanho médio do texto: {resumo_ruido["tamanho_medio_texto"]} chars')
    print(f'   % com protocolo: {resumo_ruido["pct_com_protocolo"]}%')
    print(f'   % com sigeprev: {resumo_ruido["pct_com_sigeprev"]}%')
    print(f'   % com erro: {resumo_ruido["pct_com_erro"]}%')

    caminho_ruido = ARTEFATOS / f'analise_ruido_{timestamp}.xlsx'
    try:
        df_ruido.to_excel(caminho_ruido, index=False, engine='openpyxl')
        print(f'💾 Análise de ruído salva: {caminho_ruido}')
    except Exception as e:
        caminho_csv = caminho_ruido.with_suffix('.csv')
        df_ruido.to_csv(caminho_csv, index=False, encoding='utf-8')
        print(f'⚠️  Salvando CSV: {caminho_csv}')
        caminho_ruido = caminho_csv

    # ============================================================
    # 3. SUGESTÕES DE NOVOS MOTIVOS
    # ============================================================
    print('\n' + '=' * 70)
    print('SUGESTÕES DE NOVOS MOTIVOS PARA A TAXONOMIA')
    print('=' * 70)

    df_sugestoes = sugerir_novos_motivos(df_auditoria, top_n=20)
    print(f'   Novos motivos sugeridos: {len(df_sugestoes)}')
    for _, row in df_sugestoes.head(10).iterrows():
        print(f"   - {row['motivo_sugerido']} ({row['qtd_tickets']} tickets, {row['categoria_origem']})")

    caminho_sugestoes = ARTEFATOS / f'sugestoes_novos_motivos_{timestamp}.xlsx'
    try:
        df_sugestoes.to_excel(caminho_sugestoes, index=False, engine='openpyxl')
        print(f'💾 Sugestões salvas: {caminho_sugestoes}')
    except Exception as e:
        caminho_csv = caminho_sugestoes.with_suffix('.csv')
        df_sugestoes.to_csv(caminho_csv, index=False, encoding='utf-8')
        print(f'⚠️  Salvando CSV: {caminho_csv}')
        caminho_sugestoes = caminho_csv

    # ============================================================
    # 4. ESPECIFICAÇÃO DA INTERFACE
    # ============================================================
    espec_path = ARTEFATOS / f'especificacao_interface_{timestamp}.txt'
    with open(espec_path, 'w', encoding='utf-8') as f:
        f.write(gerar_especificacao_interface())
    print(f'📄 Especificação da interface salva: {espec_path}')

    print('\n' + '=' * 70)
    print('ETAPA 1 — AUDITORIA CONCLUÍDA')
    print('=' * 70)
    print('\n📋 Próximo passo: revisar a auditoria e as sugestões de novos motivos,')
    print('   então prosseguir para a Etapa 2 (interface Streamlit de validação).')
    print('\n⚠️  Lembrete: não alterar regras hierárquicas nem treinar modelo nesta etapa.')


if __name__ == '__main__':
    main()
