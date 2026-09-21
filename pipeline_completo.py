# ============================================================
# pipeline_completo.py
# ============================================================
"""
Pipeline completo: roda tudo de uma vez.

Uso:
    python pipeline_completo.py              # interativo
    python pipeline_completo.py --auto       # sem parar para perguntar
    python pipeline_completo.py --rapido     # só pipeline base (sem enriquecer)
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


RAIZ = Path(__file__).resolve().parent
SRC = RAIZ / 'src'
SCRIPTS = RAIZ / 'scripts'


def log(mensagem, nivel='INFO'):
    agora = datetime.now().strftime('%H:%M:%S')
    emoji = {'INFO': 'ℹ️', 'OK': '✅', 'AVISO': '⚠️', 'ERRO': '❌'}.get(nivel, '•')
    print(f'[{agora}] {emoji} {mensagem}')


def executar(script, args=None, obrigatorio=True):
    """Executa um script Python."""
    nome = Path(script).name
    log(f'▶️  Rodando {nome}')

    cmd = [sys.executable, str(script)]
    if args:
        cmd.extend(args)

    try:
        # Executa no diretório do script para imports funcionarem
        resultado = subprocess.run(
            cmd,
            cwd=str(Path(script).parent),
            check=True,
        )
        log(f'   OK', 'OK')
        return True
    except subprocess.CalledProcessError as e:
        log(f'   Falhou: {e}', 'ERRO')
        if obrigatorio:
            raise
        return False
    except Exception as e:
        log(f'   Erro: {e}', 'ERRO')
        if obrigatorio:
            raise
        return False


def perguntar(mensagem):
    """Pergunta s/n."""
    resposta = input(f'{mensagem} (s/n): ').strip().lower()
    return resposta == 's'


# ==================== MAIN ====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true',
                        help='Não pergunta nada, roda tudo')
    parser.add_argument('--rapido', action='store_true',
                        help='Só pipeline base (sem enriquecer)')
    parser.add_argument('--dias-enriq', type=int, default=7,
                        help='Dias para enriquecer (padrão: 7)')
    args = parser.parse_args()

    inicio = datetime.now()

    print('=' * 60)
    print('PIPELINE COMPLETO - HELP360')
    print('=' * 60)
    print(f'📁 Raiz: {RAIZ}')
    print(f'⚙️  Modo: {"AUTO" if args.auto else "INTERATIVO"}')
    print(f'⚙️  Enriquecimento: {"PULADO" if args.rapido else f"últimos {args.dias_enriq} dias"}')
    print()

    # ==================== ETAPA 1: PIPELINE BASE ====================
    print('=' * 60)
    print('ETAPA 1 — PIPELINE BASE')
    print('=' * 60)

    # Programa0
    if args.auto or perguntar('Processar Tabela fato?'):
        executar(SRC / 'programa0_preprocessar.py', obrigatorio=False)

    # Programa1
    if args.auto or perguntar('Baixar tickets do Help360?'):
        executar(SRC / 'programa1_download.py', obrigatorio=True)

    # Programa2
    if args.auto or perguntar('Filtrar tickets?'):
        executar(SRC / 'programa2_filtrar.py', obrigatorio=True)

    # Programa3
    if args.auto or perguntar('Abrir tickets no navegador?'):
        executar(SRC / 'programa3_abrir.py', obrigatorio=False)

    # Programa4
    if args.auto or perguntar('Persistir no banco?'):
        executar(SRC / 'programa4_persistir.py', obrigatorio=True)

    # ==================== ETAPA 2: ENRIQUECIMENTO ====================
    if not args.rapido:
        print()
        print('=' * 60)
        print('ETAPA 2 — ENRIQUECIMENTO')
        print('=' * 60)
        print(f'⏱️  Pode levar ~{args.dias_enriq * 1.5:.0f} minutos')

        if args.auto or perguntar(f'Enriquecer últimos {args.dias_enriq} dias?'):
            executar(
                SRC / 'programa5_enriquecer.py',
                args=[f'--dias={args.dias_enriq}'],
                obrigatorio=False,
            )

    # ==================== ETAPA 3: SCRIPTS DE ANÁLISE ====================
    print()
    print('=' * 60)
    print('ETAPA 3 — SCRIPTS DE ANÁLISE')
    print('=' * 60)

    scripts_analise = [
        ('carregar_analistas.py',          'Carregar analistas'),
        ('marcar_respondidos.py',          'Marcar respondidos'),
        ('marcar_empresa_responsavel.py',  'Classificar empresas'),
        ('diagnosticar_tickets.py',        'Aplicar matriz de verdade'),
        ('analisar_sla_criticidade.py',    'Analisar SLA por criticidade'),
    ]

    for script, nome in scripts_analise:
        caminho = SCRIPTS / script
        if not caminho.exists():
            log(f'   {nome}: script não encontrado', 'AVISO')
            continue

        if args.auto or perguntar(f'{nome}?'):
            executar(caminho, obrigatorio=False)

    # ==================== ETAPA 4: ALERTAS (opcional) ====================
    print()
    print('=' * 60)
    print('ETAPA 4 — ALERTAS TEAMS')
    print('=' * 60)

    if perguntar('Enviar alertas para o Teams?'):
        executar(SCRIPTS / 'alertas.py', args=['--enviar'], obrigatorio=False)

    # ==================== RESUMO ====================
    tempo_total = (datetime.now() - inicio).total_seconds() / 60

    print()
    print('=' * 60)
    print('✅ PIPELINE COMPLETO FINALIZADO')
    print('=' * 60)
    print(f'⏱️  Tempo total: {tempo_total:.1f} minutos')
    print()
    print('📋 Próximo passo: rodar o dashboard')
    print('   python -m streamlit run dashboard/app.py')


if __name__ == '__main__':
    main()