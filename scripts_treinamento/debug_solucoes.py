# scripts_treinamento/debug_solucoes.py
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

linhas = tabela.find('tbody').find_all('tr', recursive=False)

# Pega cada Solução
solucoes = []
for i, linha in enumerate(linhas):
    cells = linha.find_all('td', recursive=False)
    if cells and 'Solução:' in cells[0].get_text():
        if len(cells) >= 2:
            conteudo = cells[1].get_text().strip()
            solucoes.append({
                'idx': i,
                'length': len(conteudo),
                'texto': conteudo[:500],
            })

print(f'Total de soluções: {len(solucoes)}')
print()

for i, s in enumerate(solucoes):
    print(f'=' * 80)
    print(f'SOLUÇÃO [{i}] — idx {s["idx"]} — {s["length"]} chars')
    print(f'=' * 80)
    print(s['texto'])
    print()