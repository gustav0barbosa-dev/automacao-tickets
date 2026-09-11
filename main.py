# ============================================================
# main.py - Orquestração Completa do Pipeline (v2 - src/)
# ============================================================
"""
Pipeline completo de automação do Help360.

Estrutura:
  raiz/
    ├── main.py                 (este arquivo)
    ├── src/                    (programas)
    │   ├── utils_help360.py
    │   ├── programa0_preprocessar.py
    │   ├── programa1_download.py
    │   ├── programa2_filtrar.py
    │   └── programa3_abrir.py
    ├── scripts/                (utilitários)
    ├── config/                 (configurações)
    ├── dados/                  (logs, snapshots)
    └── docs/                   (documentação)
"""

import subprocess
import sys
import os


# ==================== CAMINHOS ====================
# Detecta a raiz do projeto (pasta onde está este main.py)
RAIZ_PROJETO = os.path.dirname(os.path.abspath(__file__))
PASTA_SRC = os.path.join(RAIZ_PROJETO, 'src')
PASTA_DOWNLOADS = os.path.join(os.path.expanduser('~'), 'Downloads')


# ==================== FUNÇÕES AUXILIARES ====================
def verificar_estrutura():
    """Valida se a estrutura de pastas está correta."""
    problemas = []

    if not os.path.exists(PASTA_SRC):
        problemas.append(f"❌ Pasta 'src/' não encontrada em {RAIZ_PROJETO}")

    if not os.path.exists(os.path.join(PASTA_SRC, 'utils_help360.py')):
        problemas.append("❌ 'src/utils_help360.py' não encontrado")

    if problemas:
        print("=" * 60)
        print("⚠️ PROBLEMAS DE ESTRUTURA DETECTADOS")
        print("=" * 60)
        for p in problemas:
            print(f"  {p}")
        print("\nVerifique se os arquivos foram movidos corretamente para src/")
        return False
    return True


def executar_programa(nome_arquivo):
    """
    Executa um programa de src/ rodando com cwd=src,
    para que os imports internos (from utils_help360 import ...) funcionem.
    """
    caminho_completo = os.path.join(PASTA_SRC, nome_arquivo)

    print(f"\n{'=' * 60}")
    print(f"EXECUTANDO: src/{nome_arquivo}")
    print('=' * 60)

    if not os.path.exists(caminho_completo):
        print(f"❌ Arquivo '{caminho_completo}' não encontrado.")
        return False

    try:
        # Executa dentro de src/ para os imports relativos funcionarem
        subprocess.run(
            [sys.executable, nome_arquivo],
            cwd=PASTA_SRC,
            check=True
        )
        print(f"✅ src/{nome_arquivo} executado com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar {nome_arquivo}: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False


def verificar_tabela_fato():
    """Verifica se a Tabela fato existe em Downloads."""
    caminhos = [
        os.path.join(PASTA_DOWNLOADS, 'Tickets - Tabela fato.xlsx'),
        'Tickets - Tabela fato.xlsx'
    ]
    for caminho in caminhos:
        if os.path.exists(caminho):
            return caminho
    return None


# ==================== MAIN ====================
def main():
    print("=" * 60)
    print("PIPELINE DE AUTOMAÇÃO - HELP360")
    print("=" * 60)
    print(f"📁 Raiz do projeto  : {RAIZ_PROJETO}")
    print(f"📁 Programas        : {PASTA_SRC}")
    print(f"📁 Downloads        : {PASTA_DOWNLOADS}")
    print(f"🐍 Python           : {sys.executable}")
    print()

    # Validação de estrutura
    if not verificar_estrutura():
        return

    # ============================================================
    # ETAPA 0: PRÉ-PROCESSAR A TABELA FATO (opcional)
    # ============================================================
    arquivo_tabela_fato = verificar_tabela_fato()
    if arquivo_tabela_fato:
        print(f"📂 Tabela fato encontrada: {arquivo_tabela_fato}\n")
        resposta = input(
            "Deseja processar a Tabela fato para atualizar "
            "'tickets_com_respondido.xlsx'? (s/n): "
        ).lower()

        if resposta == 's':
            if not executar_programa('programa0_preprocessar.py'):
                print("⚠️ Falha no Programa0. Continuando o pipeline...")
        else:
            print("⏭️ Pulando pré-processamento da Tabela fato.")
    else:
        print("ℹ️ 'Tickets - Tabela fato.xlsx' não encontrada em Downloads.")
        print("   O 'tickets_com_respondido.xlsx' não será atualizado.\n")

    # ============================================================
    # ETAPAS PRINCIPAIS
    # ============================================================
    programas = [
        'programa1_download.py',   # Baixa tickets.xlsx do site
        'programa2_filtrar.py',    # Filtra e gera acompanhamento.xlsx
        'programa3_abrir.py'       # Abre no navegador
    ]

    for programa in programas:
        continuar = input(f"Executar src/{programa}? (s/n): ").lower()
        if continuar != 's':
            print(f"⏭️ Pulando {programa}")
            continue

        sucesso = executar_programa(programa)
        if not sucesso:
            print(f"❌ Falha ao executar {programa}.")
            cont = input("Continuar com os próximos? (s/n): ").lower()
            if cont != 's':
                print("🛑 Pipeline interrompido pelo usuário.")
                break

    print("\n" + "=" * 60)
    print("PIPELINE FINALIZADO!")
    print("=" * 60)


if __name__ == "__main__":
    main()