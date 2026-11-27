"""
Analisa o HTML do ticket 110506 pra entender a estrutura.
"""
import re
from pathlib import Path

from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parent.parent
HTML = RAIZ / 'dados' / 'debug_html' / '110506.html'

with open(HTML, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
html_str = str(soup)

print('=' * 80)
print('ANÁLISE DO HTML — TICKET 110506')
print('=' * 80)

# ==================== 1. PROCURA "Histórico do Ticket" ====================
print('\n📋 1. BUSCA POR "Histórico do Ticket"')
pos = html_str.find('Histórico do Ticket')
if pos > 0:
    print(f'   Encontrado na posição {pos}')
    # Mostra o contexto (500 chars antes e depois)
    contexto = html_str[max(0, pos-200):pos+800]
    print(f'   Contexto:')
    print(contexto)
else:
    print('   ❌ NÃO ENCONTRADO')

# ==================== 2. PROCURA "Solução:" ====================
print('\n📋 2. BUSCA POR "Solução:"')
matches = list(re.finditer(r'Solução:', html_str))
print(f'   Encontrados: {len(matches)}')
for i, m in enumerate(matches[:3]):
    pos = m.start()
    contexto = html_str[max(0, pos-100):pos+500]
    print(f'\n   [{i}] Contexto:')
    print(f'   {contexto}')
    print()

# ==================== 3. PROCURA "Mensagem:" ====================
print('\n📋 3. BUSCA POR "Mensagem:"')
matches = list(re.finditer(r'Mensagem:', html_str))
print(f'   Encontrados: {len(matches)}')
for i, m in enumerate(matches[:3]):
    pos = m.start()
    contexto = html_str[max(0, pos-100):pos+500]
    print(f'\n   [{i}] Contexto:')
    print(f'   {contexto}')
    print()

# ==================== 4. PROCURA "Comentário interno:" ====================
print('\n📋 4. BUSCA POR "Comentário interno:"')
matches = list(re.finditer(r'Comentário interno:', html_str))
print(f'   Encontrados: {len(matches)}')

# ==================== 5. LISTA DE TABELAS ====================
print('\n📋 5. TABELAS ENCONTRADAS')
tabelas = soup.find_all('table')
print(f'   Total: {len(tabelas)}')

for i, tabela in enumerate(tabelas):
    texto = tabela.get_text()[:200]
    ths = [th.get_text().strip() for th in tabela.find_all('th')]
    print(f'\n   Tabela {i}:')
    print(f'      Ths: {ths[:10]}')
    print(f'      Texto: {texto[:150]}')

# ==================== 6. DIVS COM "well" ====================
print('\n📋 6. DIVS COM CLASS "well"')
wells = soup.find_all('div', class_='well')
print(f'   Total: {len(wells)}')
for i, well in enumerate(wells[:5]):
    texto = well.get_text().strip()[:200]
    print(f'\n   [{i}] {texto}')

# ==================== 7. DIVS COM "feed-element" ====================
print('\n📋 7. DIVS COM CLASS "feed-element"')
feeds = soup.find_all('div', class_='feed-element')
print(f'   Total: {len(feeds)}')
for i, feed in enumerate(feeds[:5]):
    texto = feed.get_text().strip()[:300]
    print(f'\n   [{i}] {texto}')

# ==================== 8. SALVA TRECHO ÚTIL ====================
# Salva o HTML em volta de "Histórico do Ticket"
if pos > 0:
    trecho = html_str[pos-500:pos+5000]
    arquivo = RAIZ / 'dados' / 'debug_html' / 'trecho_historico.html'
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write(trecho)
    print(f'\n💾 Trecho salvo em: {arquivo}')   