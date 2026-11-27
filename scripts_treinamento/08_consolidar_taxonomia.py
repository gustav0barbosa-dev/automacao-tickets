# scripts_treinamento/08_consolidar_taxonomia.py
"""
Etapa 3 — Construção da taxonomia de motivos (Fase 3).

Objetivo:
  1. Consolidar motivos existentes na taxonomia (config/taxonomia_motivos.yaml)
  2. Criar novos motivos a partir dos clusters aprovados na auditoria (Etapa 1)
  3. Identificar motivos redundantes (mesmo assunto com nomes diferentes)
  4. Criar hierarquia categoria → subcategoria → motivo

Saídas:
  - config/taxonomia_motivos_consolidada.yaml  (nova taxonomia proposta)
  - scripts_treinamento/artefatos/relatorio_consolidacao_*.xlsx
      relatório de mudanças: motivos mantidos, adicionados, redundantes, a revisar

NÃO altera regras hierárquicas de classificação nem treina modelo.
É pura construção de catálogo de conhecimento.
"""

import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import yaml
import re
from collections import Counter

RAIZ = Path(__file__).resolve().parent.parent
TAXONOMIA_ATUAL = RAIZ / 'config' / 'taxonomia_motivos.yaml'
ARTEFATOS = RAIZ / 'scripts_treinamento' / 'artefatos'
TAXONOMIA_NOVA = RAIZ / 'config' / 'taxonomia_motivos_consolidada.yaml'


# ==================== CARREGAMENTO ====================


def carregar_taxonomia_atual():
    with open(TAXONOMIA_ATUAL, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def encontrar_auditoria_mais_recente():
    candidatos = sorted(
        ARTEFATOS.glob('auditoria_clusters_*.xlsx'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidatos:
        raise FileNotFoundError(
            f'Não encontrou auditoria_clusters em {ARTEFATOS}. '
            'Rode primeiro 07_auditar_clusters.py.'
        )
    return candidatos[0]


def encontrar_sugestoes_mais_recentes():
    candidatos = sorted(
        ARTEFATOS.glob('sugestoes_novos_motivos_*.xlsx'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidatos:
        return candidatos[0]
    return None


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
    return None


# ==================== LIMPEZA E NORMALIZAÇÃO ====================


def slugify_motivo(nome):
    """Converte nome do motivo em slug para motivo_id."""
    s = nome.lower()
    s = re.sub(r'[àáâãä]', 'a', s)
    s = re.sub(r'[êèé]', 'e', s)
    s = re.sub(r'[íìîï]', 'i', s)
    s = re.sub(r'[óòôõö]', 'o', s)
    s = re.sub(r'[úùûü]', 'u', s)
    s = re.sub(r'[ç]', 'c', s)
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s or 'motivo'


def normalizar_texto(texto):
    """Remove acentos e coloca em lowercase para comparação."""
    if not texto:
        return ''
    t = str(texto).lower()
    t = re.sub(r'[àáâãä]', 'a', t)
    t = re.sub(r'[êèé]', 'e', t)
    t = re.sub(r'[íìîï]', 'i', t)
    t = re.sub(r'[óòôõö]', 'o', t)
    t = re.sub(r'[úùûü]', 'u', t)
    t = re.sub(r'[ç]', 'c', t)
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


# ==================== DETECÇÃO DE REDUNDÂNCIA ====================


def sao_redundantes(nome_a, nome_b, limiar=0.6):
    """
    Heurística: dois nomes são redundantes se compartilham pelo menos
    2 palavras significativas ou se um contém o outro (após normalização).
    """
    a = normalizar_texto(nome_a).split()
    b = normalizar_texto(nome_b).split()
    stop = {'de', 'do', 'da', 'em', 'que', 'para', 'com', 'por', 'ao', 'aos',
            'e', 'a', 'o', 'as', 'os', 'sem', 'se', 'ser'}
    a_sig = {w for w in a if w not in stop and len(w) > 2}
    b_sig = {w for w in b if w not in stop and len(w) > 2}
    if not a_sig or not b_sig:
        return False
    intersecao = a_sig.intersection(b_sig)
    if len(intersecao) >= 2:
        return True
    # Um contém o outro (ignorando stopwords)
    if a_sig.issubset(b_sig) or b_sig.issubset(a_sig):
        return True
    return False


# ==================== CONSOLIDAÇÃO ====================


def consolidar(taxonomia_atual, df_auditoria, df_sugestoes, df_rotulos):
    """
    Constrói a nova taxonomia:
    - Mantém motivos existentes que têm uso nos rótulos fracos
    - Adiciona novos motivos de clusters de alta coerência aprovados
    - Marca clusters de média coerência como "a revisar"
    - Identifica redundâncias
    - Cria hierarquia categoria → subcategoria (motivo)
    """
    novo = {
        'versao': taxonomia_atual.get('versao', '1.0'),
        'criado_em': taxonomia_atual.get('criado_em', ''),
        'atualizado_em': datetime.now().strftime('%Y-%m-%d'),
        'fonte': 'Auditoria de clusters (Etapa 1) + taxonomia anterior',
        'categorias': {},
        'motivos_transversais': taxonomia_atual.get('motivos_transversais', {}),
        'ambiguidades': taxonomia_atual.get('ambiguidades', []),
    }

    # Conta uso de cada motivo existente nos rótulos fracos
    uso_motivo_existente = Counter()
    if df_rotulos is not None and 'motivo_id' in df_rotulos.columns:
        for mid in df_rotulos['motivo_id'].dropna():
            uso_motivo_existente[mid] += 1

    # ============================================================
    # 1. Motivos existentes (categorias da taxonomia atual)
    # ============================================================
    for categoria, dados in taxonomia_atual.get('categorias', {}).items():
        novo['categorias'][categoria] = {'motivos': {}}
        for motivo_id, motivo in dados.get('motivos', {}).items():
            qtd_uso = uso_motivo_existente.get(motivo_id, 0)
            novo['categorias'][categoria]['motivos'][motivo_id] = {
                'nome': motivo.get('nome', motivo_id),
                'descricao': motivo.get('descricao', ''),
                'palavras_chave': motivo.get('palavras_chave', []),
                'requer_autorizacao': motivo.get('requer_autorizacao', False),
                'ativo': motivo.get('ativo', True),
                'precedencia': motivo.get('precedencia', 999),
                'uso_tickets': qtd_uso,
                'origem': 'taxonomia_anterior',
                'status': 'mantido' if qtd_uso > 0 else 'sem_uso',
            }

    # ============================================================
    # 2. Novos motivos a partir dos clusters aprovados
    # ============================================================
    motivos_novos = []
    clusters_a_revisar = []
    clusters_dividir = []

    for _, row in df_auditoria.iterrows():
        cluster_id = row['cluster_id']
        n_tickets = row['n_tickets']
        coerencia = row['coerencia']
        acao = row['acao_recomendada']
        assunto = row.get('assunto_sugerido', '')
        categorias = row.get('categorias_dominantes', '')

        # Pula ruído
        if cluster_id == -1:
            continue

        # Determina categoria predominante (primeira do campo categorias_dominantes)
        cat_predominante = ''
        if pd.notna(categorias) and str(categorias).strip():
            primeira = str(categorias).split(' | ')[0]
            cat_predominante = primeira.split(' (')[0].strip() if '(' in primeira else primeira.strip()

        if acao == 'Aprovar motivo' and coerencia == 'alta' and n_tickets >= 15:
            motivo_id = slugify_motivo(assunto)
            novo['categorias'].setdefault(cat_predominante, {'motivos': {}})
            novo['categorias'][cat_predominante]['motivos'][motivo_id] = {
                'nome': assunto,
                'descricao': f'Motivo descoberto via clustering emergente (cluster {cluster_id}, {n_tickets} tickets).',
                'palavras_chave': [],
                'requer_autorizacao': False,
                'ativo': True,
                'precedencia': 50,
                'uso_tickets': int(n_tickets),
                'origem': f'cluster_{cluster_id}',
                'status': 'novo_aprovado',
            }
            motivos_novos.append({
                'motivo_id': motivo_id,
                'nome': assunto,
                'categoria': cat_predominante,
                'qtd_tickets': int(n_tickets),
                'acao': 'Adicionar à taxonomia',
            })

        elif acao == 'Aprovar com revisão leve' and coerencia == 'média' and n_tickets >= 15:
            clusters_a_revisar.append({
                'cluster_id': cluster_id,
                'nome': assunto,
                'categoria': cat_predominante,
                'qtd_tickets': int(n_tickets),
                'acao': 'Revisar antes de adicionar',
            })

        elif acao == 'Dividir cluster':
            clusters_dividir.append({
                'cluster_id': cluster_id,
                'nome': assunto,
                'categoria': cat_predominante,
                'qtd_tickets': int(n_tickets),
                'acao': 'Dividir em sub-clusters',
            })

    # ============================================================
    # 3. Detecção de redundâncias entre motivos existentes e novos
    # ============================================================
    redundantes = []
    todos_nomes = []
    for cat, dados in novo['categorias'].items():
        for mid, motivo in dados['motivos'].items():
            todos_nomes.append((mid, motivo['nome'], cat))

    for i in range(len(todos_nomes)):
        for j in range(i + 1, len(todos_nomes)):
            mid_a, nome_a, cat_a = todos_nomes[i]
            mid_b, nome_b, cat_b = todos_nomes[j]
            if sao_redundantes(nome_a, nome_b):
                redundantes.append({
                    'motivo_a': f'{mid_a} ({nome_a}) [{cat_a}]',
                    'motivo_b': f'{mid_b} ({nome_b}) [{cat_b}]',
                    'acao_sugerida': 'Mesclar',
                })

    # ============================================================
    # 4. Relatório de consolidação
    # ============================================================
    relatorio = {
        'resumo': {
            'total_motivos_existentes': sum(
                len(d['motivos']) for d in novo['categorias'].values()
            ),
            'novos_motivos_aprovados': len(motivos_novos),
            'clusters_a_revisar': len(clusters_a_revisar),
            'clusters_dividir': len(clusters_dividir),
            'redundancias_detectadas': len(redundantes),
        },
        'motivos_mantidos': [],
        'novos_motivos': motivos_novos,
        'clusters_a_revisar': clusters_a_revisar,
        'clusters_dividir': clusters_dividir,
        'redundancias': redundantes,
    }

    # Lista motivos mantidos
    for cat, dados in novo['categorias'].items():
        for mid, motivo in dados['motivos'].items():
            if motivo['origem'] == 'taxonomia_anterior':
                relatorio['motivos_mantidos'].append({
                    'motivo_id': mid,
                    'nome': motivo['nome'],
                    'categoria': cat,
                    'uso_tickets': motivo['uso_tickets'],
                    'status': motivo['status'],
                })

    return novo, relatorio


# ==================== SAÍDA ====================


def salvar_taxonomia(taxonomia_nova):
    with open(TAXONOMIA_NOVA, 'w', encoding='utf-8') as f:
        yaml.dump(taxonomia_nova, f, allow_unicode=True, sort_keys=False)
    print(f'💾 Taxonomia consolidada salva: {TAXONOMIA_NOVA}')


def salvar_relatorio(relatorio, timestamp):
    caminho = ARTEFATOS / f'relatorio_consolidacao_{timestamp}.xlsx'
    try:
        with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
            pd.DataFrame(relatorio['motivos_mantidos']).to_excel(
                writer, sheet_name='motivos_mantidos', index=False)
            pd.DataFrame(relatorio['novos_motivos']).to_excel(
                writer, sheet_name='novos_motivos', index=False)
            pd.DataFrame(relatorio['clusters_a_revisar']).to_excel(
                writer, sheet_name='clusters_a_revisar', index=False)
            pd.DataFrame(relatorio['clusters_dividir']).to_excel(
                writer, sheet_name='clusters_dividir', index=False)
            pd.DataFrame(relatorio['redundancias']).to_excel(
                writer, sheet_name='redundancias', index=False)
            pd.DataFrame([relatorio['resumo']]).to_excel(
                writer, sheet_name='resumo', index=False)
        print(f'💾 Relatório de consolidação salvo: {caminho}')
    except Exception as e:
        print(f'⚠️  Erro ao salvar XLSX: {e}')


# ==================== MAIN ====================


def main():
    print('📂 Carregando taxonomia atual...')
    taxonomia_atual = carregar_taxonomia_atual()

    print('📂 Carregando auditoria de clusters...')
    auditoria_path = encontrar_auditoria_mais_recente()
    print(f'   Arquivo: {auditoria_path.name}')
    df_auditoria = pd.read_excel(auditoria_path)

    print('📂 Carregando sugestões de novos motivos...')
    sugestoes_path = encontrar_sugestoes_mais_recentes()
    df_sugestoes = pd.read_excel(sugestoes_path) if sugestoes_path else pd.DataFrame()

    print('📂 Carregando rótulos fracos...')
    rotulos_path = encontrar_rotulos_mais_recentes()
    df_rotulos = pd.read_csv(rotulos_path) if rotulos_path else pd.DataFrame()
    print(f'   Rotulados: {len(df_rotulos)} tickets')

    print('\n🔨 Consolidando taxonomia...')
    taxonomia_nova, relatorio = consolidar(
        taxonomia_atual, df_auditoria, df_sugestoes, df_rotulos
    )

    print('\n📊 Resumo da consolidação:')
    for k, v in relatorio['resumo'].items():
        print(f'   {k}: {v}')

    print('\n🆕 Novos motivos aprovados:')
    for m in relatorio['novos_motivos'][:10]:
        print(f'   - {m["nome"]} ({m["qtd_tickets"]} tickets, {m["categoria"]})')

    print('\n🔄 Clusters para dividir:')
    for c in relatorio['clusters_dividir'][:5]:
        print(f'   - Cluster {c["cluster_id"]}: {c["nome"]} ({c["qtd_tickets"]} tickets)')

    print('\n🔍 Redundâncias detectadas:')
    for r in relatorio['redundancias'][:10]:
        print(f'   - {r["motivo_a"]} ~ {r["motivo_b"]} → {r["acao_sugerida"]}')

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    salvar_taxonomia(taxonomia_nova)
    salvar_relatorio(relatorio, timestamp)

    print('\n✅ Etapa 3 — Construção da taxonomia concluída.')
    print(f'\n📄 Nova taxonomia: {TAXONOMIA_NOVA}')
    print('   Revise o arquivo antes de substituir o config/taxonomia_motivos.yaml atual.')


if __name__ == '__main__':
    main()
