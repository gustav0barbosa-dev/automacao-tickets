import sqlite3
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, 'scripts_treinamento')

# Importa as funções sem executar o main
import re
import numpy as np

def limpar_placeholders(texto):
    if not texto:
        return ''
    texto = re.sub(r'<[A-Z_]+>', '', str(texto))
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

BANCO = Path('dados/tickets.db')
conn = sqlite3.connect(BANCO)

# Pega o ticket 110506
df = pd.read_sql('SELECT id, titulo, descricao, solucao FROM tickets WHERE id = 110506', conn)
print('TÍTULO:', df['titulo'].iloc[0])
print('DESCRIÇÃO:', df['descricao'].iloc[0][:500])
print('SOLUÇÃO:', df['solucao'].iloc[0][:500] if pd.notna(df['solucao'].iloc[0]) else 'VAZIA')

# Verifica se tem placeholders
desc = df['descricao'].iloc[0]
tem_placeholder = '<TELEFONE>' in desc or '<CPF>' in desc
print(f'\nTem placeholder antigo? {tem_placeholder}')

# Verifica protocolo preservado
import re as re2
protocolos = re2.findall(r'\b\d{8}\b', desc)
print(f'Protocolos de 8 dígitos encontrados: {protocolos}')

conn.close()