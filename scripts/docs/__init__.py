# ============================================================
# Pacote de geradores de documentação
# ============================================================
"""
Cada módulo gerar_XX_*.py contém uma função `gerar(forcar=False)`
que escreve um arquivo .md na pasta docs/.

O orquestrador em scripts/gerar_docs.py importa todos e roda em ordem.
"""

# Lista dos geradores (na ordem)
GERADORES = [
    'gerar_00_readme',
    'gerar_01_visao_e_escopo',
    'gerar_02_requisitos',
    'gerar_03_arquitetura',
    'gerar_04_modelo_dados',
    'gerar_05_regras_negocio',
    'gerar_06_analises',
    'gerar_07_interfaces',
    'gerar_08_instalacao',
    'gerar_09_operacao',
    'gerar_10_testes',
    'gerar_11_roadmap',
    'gerar_12_glossario',
    'gerar_13_changelog',
]