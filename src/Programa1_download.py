# ============================================================
# Programa1.py - Download de Tickets do Help360 (v2)
# ============================================================

import time
import os
from datetime import datetime
from pathlib import Path
from getpass import getpass

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils_help360 import criar_navegador, realizar_login


# ==================== CAMINHOS ====================
PASTA_DOWNLOADS = Path(os.path.expanduser('~')) / 'Downloads'
ARQUIVO_TICKETS = PASTA_DOWNLOADS / 'tickets.xlsx'
PADRAO_BACKUP = 'tickets_backup_*.xlsx'


# ==================== LIMPEZA ====================
def limpar_downloads_antigos():
    """
    Limpa downloads antigos ANTES de baixar o novo:
      1. Renomeia 'tickets.xlsx' antigo para backup com timestamp
      2. Remove arquivos duplicados (tickets (1).xlsx, etc)
      3. Log do que foi feito
    """
    print("\n🧹 Limpando downloads antigos...")

    # 1. Renomeia 'tickets.xlsx' antigo
    if ARQUIVO_TICKETS.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = PASTA_DOWNLOADS / f'tickets_backup_{timestamp}.xlsx'
        ARQUIVO_TICKETS.rename(backup)
        tamanho_kb = backup.stat().st_size / 1024
        print(f"   📦 Backup: {backup.name} ({tamanho_kb:.1f} KB)")

    # 2. Remove duplicados (tickets (1).xlsx, tickets (2).xlsx, etc)
    duplicados = list(PASTA_DOWNLOADS.glob('tickets (*).xlsx'))
    for dup in duplicados:
        try:
            dup.unlink()
            print(f"   🗑️  Removido duplicado: {dup.name}")
        except Exception as e:
            print(f"   ⚠️  Erro removendo {dup.name}: {e}")

    # 3. Remove arquivos .crdownload (downloads incompletos)
    incompletos = list(PASTA_DOWNLOADS.glob('tickets*.crdownload'))
    for inc in incompletos:
        try:
            inc.unlink()
            print(f"   🗑️  Removido incompleto: {inc.name}")
        except Exception as e:
            pass

    # 4. Remove backups antigos (> 7 dias)
    backups = list(PASTA_DOWNLOADS.glob(PADRAO_BACKUP))
    agora = datetime.now()
    for bkp in backups:
        idade_dias = (agora - datetime.fromtimestamp(bkp.stat().st_mtime)).days
        if idade_dias > 7:
            try:
                bkp.unlink()
                print(f"   🗑️  Backup antigo removido: {bkp.name} ({idade_dias}d)")
            except Exception:
                pass

    print("   ✅ Limpeza concluída")


# ==================== VALIDAÇÃO ====================
def validar_arquivo_baixado():
    """
    Valida o arquivo tickets.xlsx após o download:
      - Existe?
      - Tamanho mínimo?
      - Tem as colunas esperadas?
      - Tem linhas?
    """
    print("\n🔍 Validando arquivo baixado...")

    if not ARQUIVO_TICKETS.exists():
        print(f"   ❌ Arquivo não encontrado: {ARQUIVO_TICKETS}")
        return False

    tamanho_kb = ARQUIVO_TICKETS.stat().st_size / 1024
    if tamanho_kb < 10:
        print(f"   ❌ Arquivo muito pequeno: {tamanho_kb:.1f} KB")
        return False

    try:
        df = pd.read_excel(ARQUIVO_TICKETS)
    except Exception as e:
        print(f"   ❌ Erro lendo Excel: {e}")
        return False

    if len(df) == 0:
        print(f"   ❌ Arquivo vazio (0 linhas)")
        return False

    # Colunas mínimas esperadas
    colunas_esperadas = ['ID', 'Status', 'Empresa']
    faltando = [c for c in colunas_esperadas if c not in df.columns]
    if faltando:
        print(f"   ⚠️  Colunas faltando: {faltando}")
        print(f"   Colunas disponíveis: {df.columns.tolist()}")
        return False

    # Conta empresas (verificação da Atlantic)
    if 'Empresa' in df.columns:
        empresas = df['Empresa'].value_counts().to_dict()
        print(f"   📊 Empresas: {empresas}")

        atlantic = df[df['Empresa'].isin(['Atlantic Solutions', 'Atlantic', 'ATLANTIC'])]
        if len(atlantic) > 0:
            print(f"   ⚠️  {len(atlantic)} tickets da Atlantic detectados")
            print(f"       (serão filtrados pelo Programa4)")

    print(f"   ✅ Arquivo válido: {len(df)} tickets, {tamanho_kb:.1f} KB")
    return True


# ==================== DOWNLOAD ====================
def baixar_tickets():
    """Automação para baixar a planilha de tickets do Help360."""
    print("=" * 60)
    print("PROGRAMA 1 - DOWNLOAD DE TICKETS")
    print("=" * 60)

    # ⬇️ PASSO 0: Limpa downloads antigos ANTES de baixar
    limpar_downloads_antigos()

    navegador = criar_navegador()
    wait = WebDriverWait(navegador, 15)

    try:
        # 1. Login
        realizar_login(navegador)

        # 2. Verifica se logou (checa URL)
        if 'sign_in' in navegador.current_url.lower():
            print("❌ Login falhou — ainda na tela de login")
            return

        print(f"✅ Logado: {navegador.current_url}")

        # 3. Aguarda o menu carregar
        print("🔄 Acessando área de tickets...")
        time.sleep(2)

        # Tenta 3 estratégias para clicar em "Tickets"
        estrategias = [
            '//*[@id="side-menu"]//a[@href="/tickets"]',
            '//*[@id="side-menu"]//a[contains(., "Tickets")]',
            '//a[contains(@href, "/tickets")]',
        ]

        clicou = False
        for xpath in estrategias:
            try:
                link = wait.until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                link.click()
                clicou = True
                print(f"   ✅ Menu acessado")
                break
            except Exception:
                continue

        if not clicou:
            print("❌ Não conseguiu acessar o menu de tickets")
            print("   Verifique a estrutura da página com F12")
            input("Pressione ENTER para fechar...")
            return

        time.sleep(2)

        # 4. Clica no botão de exportar
        print("📥 Baixando planilha de tickets...")

        botoes_exportar = [
            '//*[@id="div_list_tickets"]/div/div/div/div[1]/div/a/i',
            '//a[contains(@href, "export")]',
            '//i[contains(@class, "fa-download")]',
        ]

        exportou = False
        for xpath in botoes_exportar:
            try:
                botao = wait.until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                botao.click()
                exportou = True
                print(f"   ✅ Botão de exportar clicado")
                break
            except Exception:
                continue

        if not exportou:
            print("❌ Não conseguiu clicar no botão de exportar")
            input("Pressione ENTER para fechar...")
            return

        # 5. Aguarda o download completar (verifica tamanho estabilizar)
        print("⏳ Aguardando download...")
        aguardar_download_completo()

        # 6. Valida o arquivo baixado
        sucesso = validar_arquivo_baixado()

        if sucesso:
            print("\n✅ DOWNLOAD CONCLUÍDO COM SUCESSO")
        else:
            print("\n❌ FALHA NA VALIDAÇÃO — verifique manualmente")

    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()

    finally:
        input("\nPressione ENTER para fechar o navegador...")
        navegador.quit()


def aguardar_download_completo(timeout=60, intervalo=2):
    """
    Aguarda o download completar verificando:
      - Arquivo existe
      - Tamanho estabilizou (não muda entre verificações)
      - Não há .crdownload em andamento
    """
    inicio = time.time()
    ultimo_tamanho = 0
    estavel_por = 0

    while time.time() - inicio < timeout:
        # Verifica .crdownload (download em andamento)
        parciais = list(PASTA_DOWNLOADS.glob('*.crdownload'))
        if parciais:
            time.sleep(intervalo)
            continue

        # Verifica tamanho do arquivo final
        if ARQUIVO_TICKETS.exists():
            tamanho_atual = ARQUIVO_TICKETS.stat().st_size

            if tamanho_atual == ultimo_tamanho and tamanho_atual > 0:
                estavel_por += 1
                if estavel_por >= 2:  # Estável por 2 verificações (~4s)
                    print(f"   ✅ Download completo ({tamanho_atual / 1024:.1f} KB)")
                    return True
            else:
                estavel_por = 0
                ultimo_tamanho = tamanho_atual

        time.sleep(intervalo)

    print(f"   ⚠️  Timeout aguardando download ({timeout}s)")
    return False


if __name__ == "__main__":
    baixar_tickets()