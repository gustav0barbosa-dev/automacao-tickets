# ============================================================
# main.py - Orquestração Completa do Pipeline (v3)
# ============================================================
"""
Pipeline completo de automação do Help360.

Estrutura:
  raiz/
    ├── main.py                 (este arquivo)
    ├── src/
    │   ├── utils_help360.py
    │   ├── programa0_preprocessar.py
    │   ├── programa1_download.py
    │   ├── programa2_filtrar.py
    │   ├── programa3_abrir.py
    │   └── programa4_persistir.py
    ├── scripts/
    ├── config/
    ├── dados/
    └── docs/

Fluxo:
  FASE 1 — Coleta
    Programa0 → processa Tabela fato
    Programa1 → baixa tickets do site
    Programa2 → filtra
    Programa3 → abre no navegador

  FASE 2 — Persistência (opcional)
    Programa4 → grava no SQLite
"""

import subprocess
import sys
import os


# ==================== CAMINHOS ====================
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


def executar_programa(nome_arquivo, obrigatorio=True):
    """
    Executa um programa de src/ rodando com cwd=src.

    Args:
        nome_arquivo: nome do script (ex: 'programa4_persistir.py')
        obrigatorio: se True, falha interrompe o pipeline

    Returns:
        True se sucesso, False se falha
    """
    caminho_completo = os.path.join(PASTA_SRC, nome_arquivo)

    print(f"\n{'=' * 60}")
    print(f"EXECUTANDO: src/{nome_arquivo}")
    print('=' * 60)

    if not os.path.exists(caminho_completo):
        print(f"⚠️ Arquivo '{caminho_completo}' não encontrado. Pulando.")
        return False

    try:
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


def perguntar(mensagem, padrao='s'):
    """Pergunta s/n com validação."""
    while True:
        resposta = input(mensagem).strip().lower()
        if not resposta:
            resposta = padrao
        if resposta in ('s', 'n'):
            return resposta == 's'
        print("⚠️ Responda 's' ou 'n'.")


# ==================== FASES ====================
def fase_coleta():
    """Executa a Fase 1 — Coleta e filtragem."""
    print("\n" + "█" * 60)
    print("█  FASE 1 — COLETA E FILTRAGEM")
    print("█" * 60)

    # ---------- ETAPA 0: Pré-processar Tabela fato ----------
    arquivo_tabela_fato = verificar_tabela_fato()
    if arquivo_tabela_fato:
        print(f"\n📂 Tabela fato encontrada:")
        print(f"   {arquivo_tabela_fato}")

        if perguntar(
            "\nDeseja processar a Tabela fato para atualizar "
            "'tickets_com_respondido.xlsx'? (s/n) [s]: "
        ):
            if not executar_programa('programa0_preprocessar.py'):
                print("⚠️ Falha no Programa0. Continuando o pipeline...")
        else:
            print("⏭️ Pulando pré-processamento da Tabela fato.")
    else:
        print("\nℹ️ 'Tickets - Tabela fato.xlsx' não encontrada em Downloads.")
        print("   O 'tickets_com_respondido.xlsx' não será atualizado.\n")

    # ---------- ETAPA 1: Download ----------
    if perguntar("\nExecutar o download dos tickets (Programa1)? (s/n) [s]: "):
        if not executar_programa('programa1_download.py'):
            print("❌ Falha no Programa1. Abortando pipeline.")
            return False
    else:
        print("⏭️ Pulando download. Usando 'tickets.xlsx' existente.")

    # ---------- ETAPA 2: Filtragem ----------
    if perguntar("\nExecutar a filtragem (Programa2)? (s/n) [s]: "):
        if not executar_programa('programa2_filtrar.py'):
            print("❌ Falha no Programa2. Abortando pipeline.")
            return False
    else:
        print("⏭️ Pulando filtragem.")

    # ---------- ETAPA 3: Abertura ----------
    if perguntar("\nAbrir os tickets no navegador (Programa3)? (s/n) [s]: "):
        if not executar_programa('programa3_abrir.py'):
            print("⚠️ Falha no Programa3. Continuando...")
    else:
        print("⏭️ Pulando abertura.")

    return True


def fase_persistencia():
    """Executa a Fase 2 — Persistência em SQLite."""
    print("\n" + "█" * 60)
    print("█  FASE 2 — PERSISTÊNCIA")
    print("█" * 60)

    # Verifica se o banco existe ou se o schema está disponível
    caminho_schema = os.path.join(RAIZ_PROJETO, 'dados', 'schema.sql')
    if not os.path.exists(caminho_schema):
        print(f"\n⚠️ Schema não encontrado: {caminho_schema}")
        print("   Crie 'dados/schema.sql' para habilitar a persistência.")
        return False

    print("\nℹ️ O Programa4 grava todos os tickets no banco SQLite.")
    print("   Isso permite análises históricas futuras.")

    if not perguntar("\nExecutar persistência (Programa4)? (s/n) [s]: "):
        print("⏭️ Pulando persistência.")
        return True

    # Executa — mas falha não quebra o pipeline
    sucesso = executar_programa('programa4_persistir.py', obrigatorio=False)

    if sucesso:
        # Mostra resumo do banco
        caminho_banco = os.path.join(RAIZ_PROJETO, 'dados', 'tickets.db')
        if os.path.exists(caminho_banco):
            tamanho_kb = os.path.getsize(caminho_banco) / 1024
            print(f"\n📊 Banco SQLite: {caminho_banco}")
            print(f"   Tamanho: {tamanho_kb:.1f} KB")
    else:
        print("\n⚠️ Falha na persistência. O pipeline continuou mesmo assim.")
        print("   Os arquivos Excel continuam válidos.")

    return True


def fase_futura_programa5():
    """
    Placeholder para a Fase 3 — Enriquecimento (Fase 2 do roadmap).
    Será implementado quando o programa5_enriquecer.py existir.
    """
    caminho_p5 = os.path.join(PASTA_SRC, 'programa5_enriquecer.py')
    if not os.path.exists(caminho_p5):
        return  # Silencioso — só roda se o arquivo existir

    print("\n" + "█" * 60)
    print("█  FASE 3 — ENRIQUECIMENTO")
    print("█" * 60)

    if perguntar("\nExecutar enriquecimento (Programa5)? (s/n) [n]: ", padrao='n'):
        executar_programa('programa5_enriquecer.py', obrigatorio=False)
    else:
        print("⏭️ Pulando enriquecimento.")


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
        return 1

    # Fase 1 — Coleta
    if not fase_coleta():
        print("\n🛑 Pipeline interrompido por falha na Fase 1.")
        return 1

    # Fase 2 — Persistência
    fase_persistencia()

    # Fase 3 — Enriquecimento (só roda se existir)
    fase_futura_programa5()

    # Fim
    print("\n" + "=" * 60)
    print("✅ PIPELINE FINALIZADO")
    print("=" * 60)

    # Resumo dos arquivos gerados
    print("\n📂 Arquivos gerados nesta execução:")
    arquivos = [
        os.path.join(PASTA_DOWNLOADS, 'tickets.xlsx'),
        os.path.join(PASTA_DOWNLOADS, 'tickets_com_respondido.xlsx'),
        os.path.join(PASTA_DOWNLOADS, 'acompanhamento.xlsx'),
        os.path.join(RAIZ_PROJETO, 'dados', 'tickets.db'),
    ]
    for caminho in arquivos:
        nome = os.path.basename(caminho)
        if os.path.exists(caminho):
            tamanho_kb = os.path.getsize(caminho) / 1024
            mtime = os.path.getmtime(caminho)
            from datetime import datetime
            data = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M')
            print(f"   ✅ {nome:<30} ({tamanho_kb:>8.1f} KB) - {data}")
        else:
            print(f"   ⚠️  {nome:<30} (não gerado)")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())