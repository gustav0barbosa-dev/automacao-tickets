# ============================================================
# main.py - OrquestraÃ§Ã£o Completa do Pipeline (v3)
# ============================================================
"""
Pipeline completo de automaÃ§Ã£o do Help360.

Estrutura:
  raiz/
    â”œâ”€â”€ main.py                 (este arquivo)
    â”œâ”€â”€ src/
    â”‚   â”œâ”€â”€ utils_help360.py
    â”‚   â”œâ”€â”€ programa0_preprocessar.py
    â”‚   â”œâ”€â”€ programa1_download.py
    â”‚   â”œâ”€â”€ programa2_filtrar.py
    â”‚   â”œâ”€â”€ programa3_abrir.py
    â”‚   â””â”€â”€ programa4_persistir.py
    â”œâ”€â”€ scripts/
    â”œâ”€â”€ config/
    â”œâ”€â”€ dados/
    â””â”€â”€ docs/

Fluxo:
  FASE 1 â€” Coleta
    Programa0 â†’ processa Tabela fato
    Programa1 â†’ baixa tickets do site
    Programa2 â†’ filtra
    Programa3 â†’ abre no navegador

  FASE 2 â€” PersistÃªncia (opcional)
    Programa4 â†’ grava no SQLite
"""

import subprocess
import sys
import os
from pathlib import Path

# Detecta a raiz do projeto (o main.py estÃ¡ em scripts/, entÃ£o sobe 1 nÃ­vel)
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROJETO))


# ==================== CAMINHOS ====================
# (RAIZ_PROJETO jÃ¡ foi definida acima, nÃ£o redefine!)
PASTA_SRC = os.path.join(str(RAIZ_PROJETO), 'src')
PASTA_SRC = os.path.join(str(RAIZ_PROJETO), 'src')
PASTA_DOWNLOADS = os.path.join(os.path.expanduser('~'), 'Downloads')


# ==================== FUNÃ‡Ã•ES AUXILIARES ====================
def verificar_estrutura():
    """Valida se a estrutura de pastas estÃ¡ correta."""
    problemas = []

    if not os.path.exists(PASTA_SRC):
        problemas.append(f"âŒ Pasta 'src/' nÃ£o encontrada em {RAIZ_PROJETO}")

    if not os.path.exists(os.path.join(PASTA_SRC, 'utils_help360.py')):
        problemas.append("âŒ 'src/utils_help360.py' nÃ£o encontrado")

    if problemas:
        print("=" * 60)
        print("âš ï¸ PROBLEMAS DE ESTRUTURA DETECTADOS")
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
        print(f"âš ï¸ Arquivo '{caminho_completo}' nÃ£o encontrado. Pulando.")
        return False

    try:
        subprocess.run(
            [sys.executable, nome_arquivo],
            cwd=PASTA_SRC,
            check=True
        )
        print(f"âœ… src/{nome_arquivo} executado com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"âŒ Erro ao executar {nome_arquivo}: {e}")
        return False
    except Exception as e:
        print(f"âŒ Erro inesperado: {e}")
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
    """Pergunta s/n com validaÃ§Ã£o."""
    while True:
        resposta = input(mensagem).strip().lower()
        if not resposta:
            resposta = padrao
        if resposta in ('s', 'n'):
            return resposta == 's'
        print("âš ï¸ Responda 's' ou 'n'.")


# ==================== FASES ====================
def fase_coleta():
    """Executa a Fase 1 â€” Coleta e filtragem."""
    print("\n" + "â–ˆ" * 60)
    print("â–ˆ  FASE 1 â€” COLETA E FILTRAGEM")
    print("â–ˆ" * 60)

    # ---------- ETAPA 0: PrÃ©-processar Tabela fato ----------
    arquivo_tabela_fato = verificar_tabela_fato()
    if arquivo_tabela_fato:
        print(f"\nðŸ“‚ Tabela fato encontrada:")
        print(f"   {arquivo_tabela_fato}")

        if perguntar(
            "\nDeseja processar a Tabela fato para atualizar "
            "'tickets_com_respondido.xlsx'? (s/n) [s]: "
        ):
            if not executar_programa('programa0_preprocessar.py'):
                print("âš ï¸ Falha no Programa0. Continuando o pipeline...")
        else:
            print("â­ï¸ Pulando prÃ©-processamento da Tabela fato.")
    else:
        print("\nâ„¹ï¸ 'Tickets - Tabela fato.xlsx' nÃ£o encontrada em Downloads.")
        print("   O 'tickets_com_respondido.xlsx' nÃ£o serÃ¡ atualizado.\n")

    # ---------- ETAPA 1: Download ----------
    if perguntar("\nExecutar o download dos tickets (Programa1)? (s/n) [s]: "):
        if not executar_programa('programa1_download.py'):
            print("âŒ Falha no Programa1. Abortando pipeline.")
            return False
    else:
        print("â­ï¸ Pulando download. Usando 'tickets.xlsx' existente.")

    # ---------- ETAPA 2: Filtragem ----------
    if perguntar("\nExecutar a filtragem (Programa2)? (s/n) [s]: "):
        if not executar_programa('programa2_filtrar.py'):
            print("âŒ Falha no Programa2. Abortando pipeline.")
            return False
    else:
        print("â­ï¸ Pulando filtragem.")

    # ---------- ETAPA 3: Abertura ----------
    if perguntar("\nAbrir os tickets no navegador (Programa3)? (s/n) [s]: "):
        if not executar_programa('programa3_abrir.py'):
            print("âš ï¸ Falha no Programa3. Continuando...")
    else:
        print("â­ï¸ Pulando abertura.")

    return True


def fase_persistencia():
    """Executa a Fase 2 â€” PersistÃªncia em SQLite."""
    print("\n" + "â–ˆ" * 60)
    print("â–ˆ  FASE 2 â€” PERSISTÃŠNCIA")
    print("â–ˆ" * 60)

    # Verifica se o banco existe ou se o schema estÃ¡ disponÃ­vel
    caminho_schema = os.path.join(RAIZ_PROJETO, 'dados', 'schema.sql')
    if not os.path.exists(caminho_schema):
        print(f"\nâš ï¸ Schema nÃ£o encontrado: {caminho_schema}")
        print("   Crie 'dados/schema.sql' para habilitar a persistÃªncia.")
        return False

    print("\nâ„¹ï¸ O Programa4 grava todos os tickets no banco SQLite.")
    print("   Isso permite anÃ¡lises histÃ³ricas futuras.")

    if not perguntar("\nExecutar persistÃªncia (Programa4)? (s/n) [s]: "):
        print("â­ï¸ Pulando persistÃªncia.")
        return True

    # Executa â€” mas falha nÃ£o quebra o pipeline
    sucesso = executar_programa('programa4_persistir.py', obrigatorio=False)

    if sucesso:
        # Mostra resumo do banco
        caminho_banco = os.path.join(RAIZ_PROJETO, 'dados', 'tickets.db')
        if os.path.exists(caminho_banco):
            tamanho_kb = os.path.getsize(caminho_banco) / 1024
            print(f"\nðŸ“Š Banco SQLite: {caminho_banco}")
            print(f"   Tamanho: {tamanho_kb:.1f} KB")
    else:
        print("\nâš ï¸ Falha na persistÃªncia. O pipeline continuou mesmo assim.")
        print("   Os arquivos Excel continuam vÃ¡lidos.")

    return True


def fase_futura_programa5():
    """
    Placeholder para a Fase 3 â€” Enriquecimento (Fase 2 do roadmap).
    SerÃ¡ implementado quando o programa5_enriquecer.py existir.
    """
    caminho_p5 = os.path.join(PASTA_SRC, 'programa5_enriquecer.py')
    if not os.path.exists(caminho_p5):
        return  # Silencioso â€” sÃ³ roda se o arquivo existir

    print("\n" + "â–ˆ" * 60)
    print("â–ˆ  FASE 3 â€” ENRIQUECIMENTO")
    print("â–ˆ" * 60)

    if perguntar("\nExecutar enriquecimento (Programa5)? (s/n) [n]: ", padrao='n'):
        executar_programa('programa5_enriquecer.py', obrigatorio=False)
    else:
        print("â­ï¸ Pulando enriquecimento.")


# ==================== MAIN ====================
def main():
    print("=" * 60)
    print("PIPELINE DE AUTOMAÃ‡ÃƒO - HELP360")
    print("=" * 60)
    print(f"ðŸ“ Raiz do projeto  : {RAIZ_PROJETO}")
    print(f"ðŸ“ Programas        : {PASTA_SRC}")
    print(f"ðŸ“ Downloads        : {PASTA_DOWNLOADS}")
    print(f"ðŸ Python           : {sys.executable}")
    print()

    # ValidaÃ§Ã£o de estrutura
    if not verificar_estrutura():
        return 1

    # Fase 1 â€” Coleta
    if not fase_coleta():
        print("\nðŸ›‘ Pipeline interrompido por falha na Fase 1.")
        return 1

    # Fase 2 â€” PersistÃªncia
    fase_persistencia()

    # Fase 3 â€” Enriquecimento (sÃ³ roda se existir)
    fase_futura_programa5()

    # Fim
    print("\n" + "=" * 60)
    print("âœ… PIPELINE FINALIZADO")
    print("=" * 60)

    # Resumo dos arquivos gerados
    print("\nðŸ“‚ Arquivos gerados nesta execuÃ§Ã£o:")
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
            print(f"   âœ… {nome:<30} ({tamanho_kb:>8.1f} KB) - {data}")
        else:
            print(f"   âš ï¸  {nome:<30} (nÃ£o gerado)")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
