# ============================================================
# debug_login.py - Diagnóstico de login
# ============================================================

import sys
import time
from getpass import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from utils_help360 import criar_navegador, realizar_login

TICKET_ID = '111430'
EMAIL = 'gsilva@sp.gov.br'  # Ajuste se for outro

n = criar_navegador()

print('\n=== PASSO 1: Acessar tela de login ===')
n.get('https://spprev.help360.com.br/users/sign_in')
time.sleep(2)
print(f'URL: {n.current_url}')

print('\n=== PASSO 2: Fazer login ===')
senha = getpass('Senha: ')
realizar_login(n, usuario=EMAIL, senha=senha)

print(f'\nURL pós-login : {n.current_url}')
print(f'Tem "sign_in"? {"sign_in" in n.current_url.lower()}')

print('\n=== PASSO 3: Aguardar 5s ===')
time.sleep(5)
print(f'URL : {n.current_url}')

print('\n=== PASSO 4: Navegar para o ticket ===')
n.get(f'https://spprev.help360.com.br/tickets/{TICKET_ID}')
time.sleep(3)
print(f'URL final : {n.current_url}')
print(f'Tem "sign_in"? {"sign_in" in n.current_url.lower()}')
print(f'Tem "Título"? {"Título" in n.page_source}')

print('\n=== PASSO 5: Tentar outra navegação ===')
n.get(f'https://spprev.help360.com.br/tickets/{TICKET_ID}')
time.sleep(3)
print(f'URL final : {n.current_url}')
print(f'Tem "sign_in"? {"sign_in" in n.current_url.lower()}')

input('\nENTER para fechar...')
n.quit()