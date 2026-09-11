# ============================================================
# Programa3.py - Abertura de Tickets no Navegador (CORRIGIDO)
# ============================================================
# https://gemini.google.com/app/a40df1f59bbeeda0

import time
import pandas as pd
import os
from utils_help360 import criar_navegador, realizar_login


def abrir_tickets_por_status(navegador, df_followup, status_atual):
    """Abre tickets de um status específico em abas do navegador."""
    df_status = df_followup[df_followup['Status'] == status_atual]

    if df_status.empty:
        print(f'Nenhum ticket encontrado para {status_atual}')
        return

    print(f"🔄 Preparando para abrir {df_status.shape[0]} tickets com o status '{status_atual}'")

    navegador.switch_to.new_window('window')

    for i, (idx, linha) in enumerate(df_status.iterrows()):
        ticket_id = linha['ID']
        url = f'https://spprev.help360.com.br/tickets/{ticket_id}'

        if i == 0:
            print(f"📄 Abrindo ticket inicial nº {ticket_id}...")
            navegador.get(url)
        else:
            print(f'➕ Abrindo ticket nº {ticket_id} em uma nova aba...')
            navegador.execute_script(f"window.open('{url}', '_blank');")

        time.sleep(1.5)


def abrir_tickets():
    """Função principal para abrir tickets no navegador."""
    print("=" * 60)
    print("PROGRAMA 3 - ABERTURA DE TICKETS")
    print("=" * 60)

    # ==================== LOCALIZAR ARQUIVO ====================
    # Pasta de Downloads (onde o Programa2 salva o acompanhamento.xlsx)
    pasta_downloads = os.path.join(os.path.expanduser('~'), 'Downloads')

    # Ordem de preferência:
    #   1) ~/Downloads/acompanhamento.xlsx  (gerado pelo Programa2 atual)
    #   2) ~/Downloads/acompanhamento_2.xlsx (fallback de versões antigas)
    #   3) acompanhamento.xlsx              (fallback na pasta atual)
    caminho_arquivo = None
    candidatos = [
        os.path.join(pasta_downloads, 'acompanhamento.xlsx'),
        os.path.join(pasta_downloads, 'acompanhamento_2.xlsx'),
        'acompanhamento.xlsx',
        'acompanhamento_2.xlsx'
    ]

    for caminho in candidatos:
        if os.path.exists(caminho):
            caminho_arquivo = caminho
            break

    if not caminho_arquivo:
        print("❌ Nenhum arquivo de acompanhamento encontrado.")
        print(f"   Procurado em:")
        for c in candidatos:
            print(f"     - {c}")
        print("   Execute o Programa2 primeiro.")
        return

    try:
        # Carregar dados
        print(f"📂 Carregando arquivo: {caminho_arquivo}")
        df_followup = pd.read_excel(caminho_arquivo)

        if df_followup.empty:
            print("⚠️ Arquivo de acompanhamento está vazio. Nada para abrir.")
            return

        print(f"✅ {len(df_followup)} tickets carregados.\n")

        # Inicializar navegador
        navegador = criar_navegador()

        # Login
        realizar_login(navegador)

        # Status a serem monitorados
        status_monitorados = [
            'Em atendimento',
            'Resolvido',
            'Aguardando confirmação do usuário'
        ]

        # Processar cada status
        for status in status_monitorados:
            print()
            print('=' * 80)
            print(f'PROCESSANDO STATUS: {status}')
            print('=' * 80)
            abrir_tickets_por_status(navegador, df_followup, status)

        print("\n✅ Todas as abas foram abertas com sucesso!")

        # Mantém navegador aberto
        input("\nPressione ENTER para fechar o navegador...")
        navegador.quit()

    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")


if __name__ == "__main__":
    abrir_tickets()