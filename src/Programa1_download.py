# ============================================================
# Programa1.py - Download de Tickets do Help360
# ============================================================

import time
import os
from getpass import getpass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils_help360 import criar_navegador, realizar_login


def baixar_tickets():
    """Automação para baixar a planilha de tickets do Help360."""
    print("=" * 60)
    print("PROGRAMA 1 - DOWNLOAD DE TICKETS")
    print("=" * 60)

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
                print(f"   ✅ Menu acessado via: {xpath[:60]}...")
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

        print("⏳ Aguardando download...")
        time.sleep(10)

        # 5. Verifica se o arquivo baixou
        pasta = os.path.join(os.path.expanduser('~'), 'Downloads')
        arquivo = os.path.join(pasta, 'tickets.xlsx')

        if os.path.exists(arquivo):
            tamanho = os.path.getsize(arquivo) / 1024
            print(f"✅ Download concluído: {arquivo} ({tamanho:.1f} KB)")
        else:
            print(f"⚠️  Arquivo não encontrado em: {arquivo}")
            print("   Verifique manualmente a pasta de Downloads")

    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()

    finally:
        input("\nPressione ENTER para fechar o navegador...")
        navegador.quit()


if __name__ == "__main__":
    baixar_tickets()