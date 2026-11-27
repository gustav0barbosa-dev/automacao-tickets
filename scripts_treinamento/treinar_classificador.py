# scripts/treinar_classificador.py
"""
Treina classificador supervisionado usando os clusters rotulados.
"""
import sqlite3
from pathlib import Path

import joblib
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
ROTULOS = RAIZ / 'dados' / 'rotulos.csv'
MODELO = RAIZ / 'modelos' / 'classificador.pkl'

# 1. Carrega rótulos
rotulos = pd.read_csv(ROTULOS)
print(f'📋 {len(rotulos)} clusters rotulados')
print(f'   Temas: {rotulos["tema"].unique().tolist()}')

# 2. Carrega tickets + clusters
conn = sqlite3.connect(BANCO)
df = pd.read_sql('SELECT id, titulo, descricao FROM tickets', conn)
conn.close()

# 3. Associa clusters
df_clusters = pd.read_csv(RAIZ / 'relatorios' / 'clusters.csv')
# Precisa re-rodar o clustering pra ter os IDs associados...

# Ou salva o df com cluster no CSV
# ...