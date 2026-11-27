# scripts_treinamento/debug_linhas.py
from pathlib import Path
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parent.parent
HTML = RAIZ / 'dados' / 'debug_html' / '110506.html'

with open(HTML, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

# Acha a tabela
tabela = None
for t in soup.find_all('table', class_='table-striped'):
    if 'Prioridade' in str(t):
        tabela = t
        break

# Percorre as linhas
linhas = tabela.find('tbody').find_all('tr', recursive=False)
print(f'Total de linhas: {len(linhas)}')
print()

for i, linha in enumerate(linhas[:20]):
    cells = linha.find_all('td', recursive=False)
    primeira = cells[0].get_text().strip()[:80] if cells else '(vazio)'
    n_cells = len(cells)
    
    # Detecta tipo
    texto = linha.get_text()
    tipo = '?'
    if 'Solução:' in texto[:100]:
        tipo = 'SOLUÇÃO'
    elif 'Mensagem:' in texto[:100]:
        tipo = 'MENSAGEM'
    elif 'Comentário interno:' in texto[:100]:
        tipo = 'COMENTÁRIO'
    elif n_cells >= 5:
        tipo = 'CABEÇALHO'
    
    print(f'[{i:2}] {tipo:15} ({n_cells} cells) — {primeira}')