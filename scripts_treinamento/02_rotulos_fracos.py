# scripts_treinamento/02_rotulos_fracos.py
"""
Fase 2 (revisada) — Aplicação de rótulos fracos com regras hierárquicas.

Lê o corpus retrospectivo da Fase 1 e aplica a taxonomia de motivos
(config/taxonomia_motivos.yaml) usando regras com **precedência**:

  1. Motivos com menor `precedencia` vencem (regras específicas primeiro).
  2. Match no título vale mais que match no corpo (título é o sinal mais forte).
  3. Primeiro motivo que casar (respeitando precedência) é atribuído.

Saídas:
  - scripts_treinamento/artefatos/rotulos_fracos.csv
        colunas: ticket_id, id, categoria, subcategoria, titulo, descricao,
                 motivo_atribuido, motivo_id, origem='regra', confianca,
                 regras_matchadas, texto_util, score_titulo, score_corpo
  - scripts_treinamento/artefatos/amostra_validacao_YYYYMMDD_HHMMSS.xlsx
        amostra estratificada por categoria × motivo para validação humana.

Não quebra nada do pipeline nem do dashboard. Mudança aditiva.
"""

import sys
from datetime import datetime
from pathlib import Path

# Força UTF-8 no stdout (terminal Windows cp1252)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import yaml
import re

RAIZ = Path(__file__).resolve().parent.parent
ARTEFATOS = RAIZ / 'scripts_treinamento' / 'artefatos'
TAXONOMIA = RAIZ / 'config' / 'taxonomia_motivos.yaml'

# Pesos: match no título vale mais que no corpo
PESO_TITULO = 5
PESO_CORPO = 1


# ==================== CARREGAMENTO ====================


def carregar_taxonomia(caminho):
    with open(caminho, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def encontrar_corpus_mais_recente():
    candidatos = sorted(
        ARTEFATOS.glob('corpus_retrospectivo_*.csv'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidatos:
        raise FileNotFoundError(
            f'Não encontrou corpus retrospectivo em {ARTEFATOS}. '
            'Rode primeiro a Fase 1 (01_montar_corpus.py).'
        )
    return candidatos[0]


# ==================== COMPILAR REGRAS ====================


def compilar_regras(taxonomia):
    """
    Retorna dict: categoria -> lista de dicionários de motivo ordenados por precedencia.
    Cada item: {motivo_id, nome, padroes:[re.Pattern], requer_autorizacao, precedencia}
    """
    regras = {}
    for categoria, dados in taxonomia['categorias'].items():
        lista = []
        for motivo_id, motivo in dados['motivos'].items():
            padroes = [
                re.compile(pk, re.IGNORECASE)
                for pk in motivo.get('palavras_chave', [])
            ]
            lista.append({
                'motivo_id': motivo_id,
                'nome': motivo.get('nome', motivo_id),
                'padroes': padroes,
                'requer_autorizacao': motivo.get('requer_autorizacao', False),
                'precedencia': motivo.get('precedencia', 999),
            })
        # Ordena por precedencia (menor primeiro = mais prioritario)
        lista.sort(key=lambda x: x['precedencia'])
        regras[categoria] = lista
    return regras


# ==================== APLICAÇÃO DAS REGRAS ====================


def contar_matches(texto, padroes):
    """Conta quantos padrões casam no texto."""
    return sum(1 for p in padroes if p.search(texto))


def rotular_ticket(row, regras_categoria):
    """
    Aplica regras hierárquicas a um único ticket.
    Retorna dicionário com motivo_atribuido, motivo_id, confianca,
    regras_matchadas, score_titulo, score_corpo.
    """
    titulo = str(row.get('titulo', '') or '')
    corpo = str(row.get('texto_retrospectivo', '') or '')
    texto_util = len(corpo) > 10

    if not texto_util:
        return {
            'motivo_atribuido': 'Sem texto suficiente',
            'motivo_id': 'sem_texto_suficiente',
            'confianca': 1.0,
            'regras_matchadas': '',
            'score_titulo': 0,
            'score_corpo': 0,
        }

    categoria = row.get('categoria', '')
    lista_regras = regras_categoria.get(categoria, [])
    if not lista_regras:
        return {
            'motivo_atribuido': 'Outros / não classificado',
            'motivo_id': 'outros',
            'confianca': 0.0,
            'regras_matchadas': '',
            'score_titulo': 0,
            'score_corpo': 0,
        }

    # Percorre regras em ordem de precedencia (específicas primeiro)
    for regra in lista_regras:
        if not regra['padroes']:
            continue
        score_titulo = contar_matches(titulo, regra['padroes']) * PESO_TITULO
        score_corpo = contar_matches(corpo, regra['padroes']) * PESO_CORPO
        total = score_titulo + score_corpo

        if total > 0:
            # Confiança: fração de padrões do motivo que casaram no corpo
            n_padroes = len(regra['padroes'])
            n_match_corpo = contar_matches(corpo, regra['padroes'])
            confianca = min(1.0, n_match_corpo / max(1, n_padroes))
            # Se casou só no título, confiança média
            if score_titulo > 0 and score_corpo == 0:
                confianca = min(confianca, 0.6)
            return {
                'motivo_atribuido': regra['nome'],
                'motivo_id': regra['motivo_id'],
                'confianca': round(confianca, 3),
                'regras_matchadas': str(total),
                'score_titulo': score_titulo,
                'score_corpo': score_corpo,
            }

    # Nenhuma regra casou
    return {
        'motivo_atribuido': 'Outros / não classificado',
        'motivo_id': 'outros',
        'confianca': 0.0,
        'regras_matchadas': '',
        'score_titulo': 0,
        'score_corpo': 0,
    }


# ==================== AMOSTRA PARA VALIDAÇÃO HUMANA ====================


def gerar_amostra_validacao(df_rotulado, n_por_celula=20, seed=42):
    """Gera amostra estratificada por categoria × motivo para validação humana."""
    df = df_rotulado.copy()
    df['motivo_correto'] = ''
    df['observacao'] = ''

    # Ordena por confiança (dúvidosos primeiro)
    df = df.sort_values('confianca')

    id_col = 'ticket_id' if 'ticket_id' in df.columns else 'id'

    amostras = []
    for (cat, motivo), grupo in df.groupby(['categoria', 'motivo_id']):
        n = min(n_por_celula, len(grupo))
        if n > 0:
            amostras.append(grupo.sample(n=n, random_state=seed))

    if not amostras:
        return df.head(0)

    df_amostra = pd.concat(amostras).drop_duplicates(subset=[id_col])

    colunas = [
        id_col, 'categoria', 'motivo_atribuido', 'motivo_id',
        'confianca', 'regras_matchadas', 'texto_retrospectivo',
        'motivo_correto', 'observacao',
    ]
    colunas = [c for c in colunas if c in df_amostra.columns]
    df_amostra = df_amostra[colunas]

    return df_amostra


# ==================== MAIN ====================


def main():
    taxonomia = carregar_taxonomia(TAXONOMIA)
    regras = compilar_regras(taxonomia)

    mapa_nome_motivo = {}
    for categoria, dados in taxonomia['categorias'].items():
        for motivo_id, motivo in dados['motivos'].items():
            mapa_nome_motivo[motivo_id] = motivo.get('nome', motivo_id)

    corpus_path = encontrar_corpus_mais_recente()
    print(f'📂 Corpus: {corpus_path.name}')
    df = pd.read_csv(corpus_path)
    print(f'📊 Tickets no corpus: {len(df)}')

    print('🔖 Aplicando regras hierárquicas...')
    resultados = []
    for _, row in df.iterrows():
        res = rotular_ticket(row, regras)
        resultados.append(res)

    df_res = pd.DataFrame(resultados)

    # Garante ticket_id
    if 'ticket_id' not in df.columns:
        if 'id' in df.columns:
            df['ticket_id'] = df['id']

    df_saida = pd.concat([df.reset_index(drop=True), df_res.reset_index(drop=True)], axis=1)
    df_saida['origem'] = 'regra'
    df_saida['texto_util'] = df_saida['texto_retrospectivo'].apply(
        lambda x: len(str(x or '')) > 10
    )

    # Substitui placeholder do nome do motivo (já vem do rotular_ticket, mas garante)
    df_saida['motivo_atribuido'] = df_saida['motivo_atribuido'].fillna(
        df_saida['motivo_id'].map(lambda mid: mapa_nome_motivo.get(mid, mid))
    )

    # Reordena colunas
    colunas_saida = [
        'ticket_id', 'id', 'categoria', 'subcategoria', 'titulo', 'descricao',
        'motivo_atribuido', 'motivo_id', 'origem', 'confianca',
        'regras_matchadas', 'score_titulo', 'score_corpo', 'texto_util',
    ]
    colunas_existentes = [c for c in colunas_saida if c in df_saida.columns]
    colunas_extras = [c for c in df_saida.columns if c not in colunas_existentes]
    df_saida = df_saida[colunas_existentes + colunas_extras]

    # Salva rotulos_fracos.csv
    rotulos_path = ARTEFATOS / 'rotulos_fracos.csv'
    df_saida.to_csv(rotulos_path, index=False, encoding='utf-8')
    print(f'💾 Rótulos fracos salvos: {rotulos_path} ({len(df_saida)} tickets)')

    print('\n📊 Distribuição de motivos atribuídos (regras hierárquicas):')
    dist = df_saida['motivo_atribuido'].value_counts().head(25)
    for motivo, qtd in dist.items():
        print(f'   {motivo}: {qtd}')

    # Estatística de "Outros"
    n_outros = (df_saida['motivo_id'] == 'outros').sum()
    n_sem_texto = (df_saida['motivo_id'] == 'sem_texto_suficiente').sum()
    print(f'\n   Outros / não classificado: {n_outros} ({n_outros/len(df_saida)*100:.1f}%)')
    print(f'   Sem texto suficiente: {n_sem_texto} ({n_sem_texto/len(df_saida)*100:.1f}%)')

    # Gera amostra para validação humana
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    amostra = gerar_amostra_validacao(df_saida, n_por_celula=20)
    amostra_path = ARTEFATOS / f'amostra_validacao_{timestamp}.xlsx'
    try:
        amostra.to_excel(amostra_path, index=False, engine='openpyxl')
        print(f'📋 Amostra de validação salva: {amostra_path} ({len(amostra)} tickets)')
    except Exception as e:
        amostra_csv = amostra_path.with_suffix('.csv')
        amostra.to_csv(amostra_csv, index=False, encoding='utf-8')
        print(f'⚠️  Não foi possível salvar XLSX ({e}). Salvando CSV: {amostra_csv}')
        amostra_path = amostra_csv

    print('\n📝 PRÓXIMO PASSO: preencha a coluna "motivo_correto" na amostra de validação')
    print('   e devolva o arquivo para a Fase 3 (treinamento com conjunto ouro).')
    print('\n✅ Fase 2 (revisada) concluída.')


if __name__ == '__main__':
    main()
