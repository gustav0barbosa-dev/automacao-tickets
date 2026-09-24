"""
Verifica quantos registros tem no Postgres e se estão anonimizados.
"""
from pathlib import Path

from sqlalchemy import create_engine, text

RAIZ = Path(__file__).resolve().parent.parent
secrets = RAIZ / '.streamlit' / 'secrets.toml'

# Lê a URL do secrets.toml
url = None
if secrets.exists():
    with open(secrets, 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if linha.startswith('url') and '=' in linha:
                valor = linha.split('=', 1)[1].strip()
                # Remove aspas (simples ou duplas)
                valor = valor.strip('"').strip("'")
                if valor.startswith('postgresql://'):
                    url = valor
                    break

if not url:
    print('❌ URL do Postgres não encontrada no secrets.toml')
    exit(1)

print(f'✅ URL: {url[:60]}...')
print()

# Conecta e verifica
engine = create_engine(url, pool_pre_ping=True)

with engine.connect() as conn:
    for tabela in ['tickets', 'movimentacoes', 'mensagens']:
        try:
            r = conn.execute(text(f'SELECT COUNT(*) FROM {tabela}')).scalar()
            print(f'{tabela}: {r} registros')
        except Exception as e:
            print(f'{tabela}: ERRO — {e}')

    # Verifica se ainda tem CPF nos dados
    print()
    print('=== BUSCA POR DADOS PESSOAIS ===')
    for tabela, campo in [('tickets', 'titulo'),
                          ('tickets', 'descricao'),
                          ('mensagens', 'conteudo')]:
        try:
            q = f"""
                SELECT COUNT(*) FROM {tabela}
                WHERE {campo} ~ '\\d{{3}}\\.?\\d{{3}}\\.?\\d{{3}}-?\\d{{2}}'
            """
            r = conn.execute(text(q)).scalar()
            print(f'  {tabela}.{campo}: {r} registros com CPF')
        except Exception as e:
            print(f'  {tabela}.{campo}: ERRO — {e}')

engine.dispose()