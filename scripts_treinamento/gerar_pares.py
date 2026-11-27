"""
Gera pares (query, ticket_id) para fine-tuning.
Usa templates + palavras-chave extraídas dos tickets.
"""
import sqlite3
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

# IDs dos 27 tickets da analista
IDS_ANALISTA = [
    110388, 110506, 110522, 110557, 110688, 110711, 110852, 111156,
    111161, 111180, 111186, 111231, 111232, 111233, 111234, 111418,
    111532, 111703, 111757, 111835, 111910, 112126, 112134, 112265,
    112313, 112328, 112372,
]

# Templates de queries (genéricos, serão preenchidos com keywords)
TEMPLATES = [
    "erro em {tema}",
    "problema com {tema}",
    "não consigo acessar {tema}",
    "erro ao abrir {tema}",
    "falha em {tema}",
    "tarefa {tema} indisponível",
    "erro interno do servidor em {tema}",
    "problema no fluxo de {tema}",
    "divergência em {tema}",
    "sistema apresenta erro em {tema}",
    "preciso de ajuda com {tema}",
    "{tema} não está funcionando",
    "erro ao formalizar {tema}",
    "fluxo incorreto em {tema}",
    "tarefa {tema} apresenta erro",
]

# Temas comuns por ticket (extraídos manualmente ou por keyword)
TEMAS_POR_TICKET = {
    110506: ["composição de rubricas", "tarefa de composição", "abrir composição de rubricas"],
    110522: ["composição de rubricas", "erro interno do servidor"],
    110557: ["composição de rubricas", "tarefa reaberta"],
    110688: ["contagem de tempo", "INSS", "VTC"],
    110711: ["contagem de tempo", "quebras de tempo", "tempo zerado"],
    112265: ["conferência técnica preliminar", "contagem de tempo zerada"],
    112134: ["composição de rubricas", "protocolo VTC associado"],
    111234: ["cálculo da média", "ficha financeira complementar"],
    111233: ["cálculo da média", "ficha financeira complementar"],
    111232: ["cálculo da média", "ficha financeira complementar"],
    111231: ["cálculo da média", "ficha financeira complementar"],
    111180: ["cálculo da média", "mês não para"],
    110388: ["validação de tempo de contribuição", "VTC", "link não aparece"],
    112372: ["composição de rubricas", "protocolo cancelado"],
    112313: ["protocolo finalizado", "retornar em trâmite"],
    112126: ["composição de rubricas", "informativo de vantagens zerado"],
    111910: ["contagem de tempo", "quebras", "tempo zerado"],
    111757: ["aposentadoria por incapacidade", "data do requerimento"],
    111532: ["composição de rubricas", "erro interno do servidor"],
    111186: ["PAS", "protocolo de aposentadoria", "VTC"],
    111161: ["protocolo cancelado", "formalização da tarefa"],
    111418: ["valor estimado", "benefício previdenciário", "planilha SGGD"],
    111156: ["valor estimado", "benefício previdenciário", "planilha SGGD"],
    110852: ["requerimento de aposentadoria", "regra divergente"],
    111703: ["composição de rubricas", "levantamento de riscos"],
    111835: ["tabela de regras de aposentadoria", "revisão"],
}


def gerar_pares():
    pares = []
    for ticket_id, temas in TEMAS_POR_TICKET.items():
        for tema in temas:
            # 3 templates aleatórios por tema
            templates_escolhidos = random.sample(TEMPLATES, 3)
            for template in templates_escolhidos:
                query = template.format(tema=tema)
                pares.append((query, ticket_id))
    return pares


if __name__ == '__main__':
    pares = gerar_pares()
    print(f'Total de pares gerados: {len(pares)}')
    print()
    for i, (q, tid) in enumerate(pares[:10]):
        print(f'[{i}] "{q}" → {tid}')
    
    # Salva em arquivo
    import csv
    saida = RAIZ / 'dados' / 'pares_treino.csv'
    with open(saida, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['query', 'ticket_id'])
        writer.writerows(pares)
    print(f'\n✅ Salvo em: {saida}')