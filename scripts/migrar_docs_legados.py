# ============================================================
# migrar_docs_legados.py
# ============================================================
"""
Converte os geradores 00-03 (que usam CONTEUDO = \"\"\"...\"\"\")
para o formato de templates .md.

Uso:
    python scripts/migrar_docs_legados.py
"""

import os
import re
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_DOCS_SCRIPTS = os.path.join(_RAIZ, 'scripts', 'docs')
PASTA_TEMPLATES = os.path.join(PASTA_DOCS_SCRIPTS, 'templates')


# Mapeamento: script antigo → (arquivo template, nome de saída)
MAPEAMENTO = {
    'gerar_00_readme.py':          ('00_readme.md',          'README'),
    'gerar_01_visao_e_escopo.py':  ('01_visao_e_escopo.md',  '01_VISAO_E_ESCOPO'),
    'gerar_02_requisitos.py':      ('02_requisitos.md',      '02_REQUISITOS'),
    'gerar_03_arquitetura.py':     ('03_arquitetura.md',     '03_ARQUITETURA'),
}


def extrair_conteudo(caminho_script):
    """Extrai o conteúdo markdown de um script antigo."""
    with open(caminho_script, 'r', encoding='utf-8') as f:
        texto = f.read()

    # Regex: pega tudo entre CONTEUDO = """..."""
    match = re.search(r'CONTEUDO\s*=\s*"""(.*?)"""', texto, re.DOTALL)
    if not match:
        return None

    return match.group(1)


def gerar_script_novo(nome_template, nome_saida):
    """Gera o conteúdo do novo script no formato de template."""
    return f'''# ============================================================
# {nome_template.replace('.md', '.py')}
# ============================================================

import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from scripts.docs._base import gerar_de_template, rodar_sozinho


def gerar(forcar=False):
    return gerar_de_template(
        '{nome_template}',
        '{nome_saida}',
        forcar=forcar
    )


if __name__ == '__main__':
    rodar_sozinho(gerar)
'''


def main():
    os.makedirs(PASTA_TEMPLATES, exist_ok=True)

    print('=' * 60)
    print('MIGRAÇÃO DE GERADORES LEGADOS (00-03)')
    print('=' * 60)
    print(f'📁 Scripts: {PASTA_DOCS_SCRIPTS}')
    print(f'📁 Templates: {PASTA_TEMPLATES}')
    print()

    for nome_script, (nome_template, nome_saida) in MAPEAMENTO.items():
        caminho_script = os.path.join(PASTA_DOCS_SCRIPTS, nome_script)

        if not os.path.exists(caminho_script):
            print(f'⏭️  {nome_script} não encontrado. Pulando.')
            continue

        # 1. Extrair conteúdo markdown
        conteudo_md = extrair_conteudo(caminho_script)
        if not conteudo_md:
            print(f'❌ {nome_script}: não foi possível extrair CONTEUDO.')
            continue

        # 2. Salvar template
        caminho_template = os.path.join(PASTA_TEMPLATES, nome_template)
        with open(caminho_template, 'w', encoding='utf-8') as f:
            f.write(conteudo_md)
        print(f'✅ Template criado: {nome_template}')

        # 3. Reescrever script no formato novo
        novo_conteudo = gerar_script_novo(nome_template, nome_saida)
        with open(caminho_script, 'w', encoding='utf-8') as f:
            f.write(novo_conteudo)
        print(f'✅ Script migrado: {nome_script}')

    print()
    print('=' * 60)
    print('✅ Migração concluída!')
    print('=' * 60)
    print('\n💡 Agora rode:')
    print('   python scripts\\gerar_docs.py --forcar')


if __name__ == '__main__':
    main()