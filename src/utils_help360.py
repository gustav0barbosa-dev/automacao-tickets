# ============================================================
# utils_help360.py - Módulo Auxiliar Reutilizável (ATUALIZADO)
# ============================================================
"""
Módulo auxiliar para automação do Help360.
Contém funções compartilhadas entre todos os programas.
"""

import subprocess
import sys
import os
import re
import time
from getpass import getpass


# ==================== INSTALAÇÃO DE PACOTES ====================
def instalar_pacotes_necessarios():
    """Verifica e instala automaticamente todos os pacotes necessários."""
    pacotes = [
        'selenium',
        'webdriver-manager',
        'pandas',
        'openpyxl'
    ]

    print("📦 Verificando pacotes necessários...")
    for pacote in pacotes:
        try:
            # Tenta importar o pacote
            if pacote == 'webdriver-manager':
                __import__('webdriver_manager')
            else:
                __import__(pacote)
            print(f"✅ '{pacote}' já está instalado.")
        except ImportError:
            print(f"📦 Instalando '{pacote}'...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pacote],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"✅ '{pacote}' instalado com sucesso!")
            except Exception as e:
                print(f"❌ Erro ao instalar '{pacote}': {e}")
                print(f"   Execute manualmente: pip install {pacote}")


# Executa a instalação quando o módulo é importado
instalar_pacotes_necessarios()


# ==================== IMPORTAÇÕES ====================
# Agora que os pacotes estão instalados, importamos as bibliotecas
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# ==================== TRATAMENTO DE DATAS ====================
DATA_COLUNAS = [
    'Criado Data',
    'Alterado Data',
    'Previsão',
    'Data do Resolvido',
    'Data do 1°resolvido'
]


def tratar_datas_excel(df, colunas=DATA_COLUNAS):
    """
    Converte colunas de data para datetime.

    - dayfirst=True → garante interpretação BR (DD/MM/AAAA), evitando
      que o Pandas inverta dia/mês em datas ambíguas como '04/09/2026'.
    - format='mixed' → permite que a mesma coluna tenha formatos diferentes
      (ex: '2026-09-04' ISO e '04/09/2026' BR lado a lado).
    - errors='coerce' → valores inválidos viram NaT em vez de estourar erro.
    """
    for coluna in colunas:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(
                df[coluna],
                errors='coerce',
                dayfirst=True,
                format='mixed'
            )
    return df


# ==================== FILTROS ====================
CATEGORIAS_FORA = [
    '1ª Etapa Censo',
    'Alteração de Grupo de Pagamento',
    'Alterações Bancárias',
    'Aplicações Folha',
    'Cancelar Protocolo',
    'Cálculo da Média',
    'Consignatárias',
    'Deploy - Homologação',
    'Extinção',
    'Folha de Pagamento',
    'Monitoramento Folha',
    'Parametrização Folha',
    'Processamento Folha',
    'Reabertura de Protocolo',
    'Reajuste',
    'Recadastramento',
    'Reenvio Bancário',
    'Reprocessamento Folha',
    'Retorno de Tarefa ',
    'Rubricas',
    'Rubricas Judiciais Base Duplicadas',
    'Rúbricas Concomitantes',
    'Task',
    'Vínculos',
    'Visita domiciliar'
]


def filtrar_categoria(df, categorias=CATEGORIAS_FORA):
    """Remove categorias que não são monitoradas."""
    if 'Categoria' in df.columns:
        df = df[~df['Categoria'].isin(categorias)]
    return df


# ==================== NAVEGADOR CHROME ====================
def criar_navegador(headless=False):
    options = Options()

    # Anti-detecção
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    # User-Agent real do Chrome (sem "HeadlessChrome")
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/153.0.0.0 Safari/537.36'
    )

    # Remove flags que denunciam automação
    options.add_argument('--disable-infobars')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-gpu')
    options.add_argument('--lang=pt-BR')

    # Preferências de download
    prefs = {
        'download.default_directory': os.path.join(os.path.expanduser('~'), 'Downloads'),
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': True,
        'credentials_enable_service': False,
        'profile.password_manager_enabled': False,
    }
    options.add_experimental_option('prefs', prefs)

    if headless:
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

    servico = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=servico, options=options)
    navegador.maximize_window()

    # Remove navigator.webdriver via CDP (elimina detecção)
    try:
        navegador.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en']
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            '''
        })
    except Exception:
        pass

    return navegador


def realizar_login(navegador, usuario=None, senha=None):
    if not usuario:
        import getpass as _gp
        usuario = input('Digite seu email (@sp.gov.br): ').strip()
        if not usuario:
            usuario = 'mmarcondes@sp.gov.br'

    url_help = 'https://spprev.help360.com.br/users/sign_in'
    navegador.get(url_help)
    time.sleep(2)

    navegador.find_element(By.XPATH, '//*[@id="user_email"]').send_keys(usuario)
    navegador.find_element(By.XPATH, '//*[@id="user_password"]').send_keys(senha)
    navegador.find_element(By.XPATH, '//*[@id="new_user"]/input[3]').click()

    # Aguarda redirecionar para a home
    for _ in range(10):
        time.sleep(1)
        if 'sign_in' not in navegador.current_url.lower():
            break

    # Aquece a sessão: navega para a home e para a lista de tickets
    try:
        navegador.get('https://spprev.help360.com.br/')
        time.sleep(2)
        navegador.get('https://spprev.help360.com.br/tickets')
        time.sleep(2)
    except Exception:
        pass


# ==================== PROTEÇÃO DE DADOS (LGPD) ====================
def anonimizar_dados_lgpd(texto):
    """Aplica regex para anonimizar CPF, email e telefone."""
    if not texto or not isinstance(texto, str):
        return texto

    padrao_cpf = r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'
    padrao_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    padrao_telefone = r'\b(?:\(?\d{2}\)?\s?)??(?:9?\d{4})-?\d{4}\b'

    texto = re.sub(padrao_cpf, '<CPF>', texto)
    texto = re.sub(padrao_email, '<EMAIL>', texto)
    texto = re.sub(padrao_telefone, '<TELEFONE>', texto)

    return texto


# ==================== UTILITÁRIOS ADICIONAIS ====================
def aguardar_download(pasta, timeout=30):
    """Espera o primeiro arquivo .xlsx aparecer na pasta de download."""
    import os
    if not os.path.exists(pasta):
        os.makedirs(pasta)

    fim = time.time() + timeout
    while time.time() < fim:
        arquivos = [f for f in os.listdir(pasta) if f.endswith('.xlsx')]
        if arquivos:
            caminhos = [os.path.join(pasta, f) for f in arquivos]
            caminhos.sort(key=os.path.getmtime, reverse=True)
            return caminhos[0]
        time.sleep(1)
    return None


def verificar_arquivo(caminho, timeout=30):
    """Verifica se um arquivo existe e aguarda se necessário."""
    inicio = time.time()
    while time.time() - inicio < timeout:
        if os.path.exists(caminho):
            return True
        time.sleep(1)
    return False


# Executa a verificação quando o módulo é importado
if __name__ == "__main__":
    print("✅ Módulo utils_help360 carregado com sucesso!")