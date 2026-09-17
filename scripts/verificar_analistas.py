import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'

conn = sqlite3.connect(BANCO)

print('=' * 60)
print('SCHEMA DA TABELA `analistas`')
print('=' * 60)

cols = conn.execute('PRAGMA table_info(analistas)').fetchall()
if not cols:
    print('❌ Tabela NÃO existe')
else:
    print(f'Total de colunas: {len(cols)}\n')
    for col in cols:
        print(f'  [{col[0]}] {col[1]:<25} {col[2]:<12} notnull={col[3]} default={col[4]}')

    print()
    print('Registros:', conn.execute('SELECT COUNT(*) FROM analistas').fetchone()[0])

print()
print('=' * 60)
print('TENTATIVA DE INSERT DE TESTE')
print('=' * 60)
try:
    conn.execute("""
        INSERT INTO analistas (nome, email, empresa_tipo)
        VALUES ('__TESTE__', 'teste@test.com', 'Outro')
    """)
    conn.commit()
    print('✅ INSERT com empresa_tipo funcionou')
    conn.execute("DELETE FROM analistas WHERE nome = '__TESTE__'")
    conn.commit()
except Exception as e:
    print(f'❌ INSERT falhou: {e}')

conn.close()