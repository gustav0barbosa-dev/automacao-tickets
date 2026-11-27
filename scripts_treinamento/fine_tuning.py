"""
Fine-tuning do MiniLM com MultipleNegativesRankingLoss.
Treina por N épocas e avalia a cada época.
"""
import csv
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
PARES_CSV = RAIZ / 'dados' / 'pares_treino.csv'
MODELO_SAIDA = RAIZ / 'dados' / 'modelo_finetuned'

# Importa as funções do buscar_tickets
import sys
sys.path.insert(0, str(RAIZ / 'scripts_treinamento'))
from buscar_tickets import carregar_tickets_com_contexto, montar_texto


def carregar_pares():
    pares = []
    with open(PARES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pares.append((row['query'], int(row['ticket_id'])))
    return pares


def avaliar(modelo, queries, tickets_esperados, textos_por_id, ids):
    """Avalia recall das queries contra os tickets esperados."""
    embeddings = modelo.encode([textos_por_id[tid] for tid in ids], show_progress_bar=False)
    query_embs = modelo.encode(queries, show_progress_bar=False)
    
    total_acertos = 0
    for query_emb, query in zip(query_embs, queries):
        sims = np.dot(embeddings, query_emb) / (
            np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_emb)
        )
        top_100 = set(ids[np.argsort(sims)[-100:]].tolist())
        acertos = len(tickets_esperados & top_100)
        total_acertos += acertos
    
    return total_acertos / (len(queries) * len(tickets_esperados)) * 100


def main():
    print('=' * 70)
    print('FINE-TUNING DO MiniLM')
    print('=' * 70)

    # 1. Carrega dados
    print('\n📂 Carregando tickets...')
    df = carregar_tickets_com_contexto()
    textos_por_id = {
        row['id']: montar_texto(row)
        for _, row in df.iterrows()
    }
    ids = np.array(list(textos_por_id.keys()))

    # 2. Carrega pares
    print('📂 Carregando pares...')
    pares = carregar_pares()
    print(f'   {len(pares)} pares')

    # 3. Cria exemplos de treino
    exemplos = [
        InputExample(texts=[query, textos_por_id[tid]])
        for query, tid in pares
        if tid in textos_por_id
    ]
    print(f'   {len(exemplos)} exemplos válidos')

    # 4. Carrega modelo
    print('\n🧠 Carregando MiniLM...')
    modelo = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    # 5. DataLoader e loss
    train_dataloader = DataLoader(exemplos, shuffle=True, batch_size=16)
    train_loss = losses.MultipleNegativesRankingLoss(modelo)

    # 6. Queries de avaliação (do gabarito)
    QUERIES_AVALIACAO = [
        "erro ao abrir composição de rubricas",
        "contagem de tempo zerada",
        "cálculo da média não para no mês",
        "protocolo cancelado ao formalizar tarefa",
        "erro interno do servidor",
        "valor do benefício não cadastrado",
        "protocolo VTC associado não encontrado",
        "requerimento com data errada",
        "fluxo seguiu caminho errado",
        "tarefa reaberta após formalização",
    ]
    TICKETS_ESPERADOS = {
        112328, 111703, 111418, 111156, 110852, 112265, 112134,
        111835, 111234, 111233, 111232, 111231, 111180, 110711,
        110388, 112372, 112313, 112126, 111910, 111757, 111532,
        111186, 111161, 110688, 110557, 110522, 110506,
    }
    TICKETS_ESPERADOS = TICKETS_ESPERADOS & set(ids.tolist())

    # 7. Avaliação inicial
    print('\n📊 Recall ANTES do treino:')
    recall_antes = avaliar(modelo, QUERIES_AVALIACAO, TICKETS_ESPERADOS, textos_por_id, ids)
    print(f'   {recall_antes:.1f}%')

    # 8. Treino por épocas
    NUM_EPOCAS = 10
    print(f'\n🚀 Treinando por {NUM_EPOCAS} épocas...')
    
    melhor_recall = recall_antes
    for epoca in range(1, NUM_EPOCAS + 1):
        print(f'\n--- Época {epoca}/{NUM_EPOCAS} ---')
        modelo.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=1,
            warmup_steps=10,
            show_progress_bar=True,
        )
        
        recall = avaliar(modelo, QUERIES_AVALIACAO, TICKETS_ESPERADOS, textos_por_id, ids)
        print(f'   📊 Recall: {recall:.1f}%')
        
        if recall > melhor_recall:
            melhor_recall = recall
            print(f'   ✅ Melhor recall! Salvando modelo...')
            modelo.save(str(MODELO_SAIDA))
        else:
            print(f'   ⚠️  Recall não melhorou (melhor: {melhor_recall:.1f}%)')

    print(f'\n✅ Treino concluído! Melhor recall: {melhor_recall:.1f}%')
    print(f'   Modelo salvo em: {MODELO_SAIDA}')


if __name__ == '__main__':
    main()