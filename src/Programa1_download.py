# ============================================================
# Programa1.py - Download de Tickets do Help360
# ============================================================
# https://gemini.google.com/app/45c75210d86b2270?hl=pt-BR

import time
from getpass import getpass
from selenium import webdriver
from selenium.webdriver.common.by import By
from utils_help360 import criar_navegador, realizar_login


def baixar_tickets():
    """Automação para baixar a planilha de tickets do Help360."""
    print("=" * 60)
    print("PROGRAMA 1 - DOWNLOAD DE TICKETS")
    print("=" * 60)

    # Inicializar navegador
    navegador = criar_navegador()

    try:
        # Login no sistema
        realizar_login(navegador)

        # Clica no menu lateral para acessar a área de chamados
        print("🔄 Acessando área de tickets...")
        navegador.find_element(
            By.XPATH, '//*[@id="side-menu"]/li[4]/a/span'
        ).click()
        time.sleep(2)

        # Clica no botão para exportar o relatório
        print("📥 Baixando planilha de tickets...")
        navegador.find_element(
            By.XPATH, '//*[@id="div_list_tickets"]/div/div/div/div[1]/div/a/i'
        ).click()

        print("⏳ Aguardando download...")
        time.sleep(5)

        print("✅ Download concluído! Arquivo salvo em: C:\\Users\\mmarcondes\\Downloads\\tickets.xlsx")

    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")

    finally:
        # Mantém navegador aberto para visualização
        input("\nPressione ENTER para fechar o navegador...")
        navegador.quit()


if __name__ == "__main__":
    baixar_tickets()