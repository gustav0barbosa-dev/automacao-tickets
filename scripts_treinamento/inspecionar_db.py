# inspecionar_db.py
import sqlite3
import os

# Tenta encontrar o banco em locais comuns
caminhos_possiveis = [
    'dados/tickets.db',
    'data/tickets.db',
    'tickets.db',
    'dados/tickets.db.gz',  # caso só exista o .gz
]

db_path = None
for caminho in caminhos_possiveis:
    if os.path.exists(caminho):
        db_path = caminho
        break

if not db_path:
    print("❌ Banco de dados não encontrado!")
    print("Caminhos testados:", caminhos_possiveis)
    print("\nArquivos na pasta 'dados':")
    if os.path.exists('dados'):
        print(os.listdir('dados'))
    else:
        print("Pasta 'dados' não existe.")
    exit(1)

print(f"✅ Banco encontrado: {db_path}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tabelas = cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

if not tabelas:
    print("⚠️ O banco NÃO tem nenhuma tabela!")
    print("Isso confirma que o banco está vazio.")
    exit(0)

for t in tabelas:
    nome_tabela = t[0]
    colunas = cursor.execute(f"PRAGMA table_info({nome_tabela})").fetchall()
    nomes_colunas = [col[1] for col in colunas]

    # Conta quantos registros tem
    try:
        count = cursor.execute(f"SELECT COUNT(*) FROM {nome_tabela}").fetchone()[0]
    except Exception as e:
        count = f"erro: {e}"

    print(f"=== {nome_tabela} ({count} registros) ===")
    print(f"Colunas: {nomes_colunas}\n")

conn.close()