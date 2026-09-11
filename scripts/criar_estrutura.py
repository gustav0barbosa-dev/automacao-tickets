import os

estrutura = {
    'automacao-tickets': {
        'src': {},
        'scripts': {},
        'config': {},
        'dados': {
            'logs': {},
            'snapshots': {},
        },
        'relatorios': {},
        'docs': {},
        'tests': {},
    }
}

arquivos_base = [
    'README.md',
    'requirements.txt',
    '.gitignore',
    'src/__init__.py',
    'config/settings.yaml',
    'config/categorias_fora.txt',
    'dados/.gitkeep',
    'relatorios/.gitkeep',
    'tests/.gitkeep',
]


def criar(raiz, estrutura):
    for pasta, subpastas in estrutura.items():
        caminho = os.path.join(raiz, pasta)
        os.makedirs(caminho, exist_ok=True)
        if subpastas:
            criar(caminho, subpastas)


def criar_arquivos(raiz, arquivos):
    for arquivo in arquivos:
        caminho = os.path.join(raiz, arquivo)
        os.makedirs(os.path.dirname(caminho) or '.', exist_ok=True)
        if not os.path.exists(caminho):
            open(caminho, 'w', encoding='utf-8').close()
            print(f"✅ {arquivo}")


if __name__ == "__main__":
    raiz = os.getcwd()
    criar(raiz, estrutura)
    criar_arquivos(raiz, arquivos_base)
    print("\n🌳 Estrutura criada em:", raiz)