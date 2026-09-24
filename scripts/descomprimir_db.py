"""
Descomprime o banco de dados (se o .gz existir).
NUNCA crasha — sempre retorna sucesso.
"""
import gzip
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DB = RAIZ / 'dados' / 'tickets.db'
DB_GZ = RAIZ / 'dados' / 'tickets.db.gz'

if DB.exists() and DB.stat().st_size > 1_000_000:
    print(f'OK: Banco SQLite ja existe: {DB}')
elif DB_GZ.exists():
    print(f'Descomprimindo {DB_GZ}...')
    DB.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(DB_GZ, 'rb') as f_in:
        with open(DB, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    print(f'OK: Banco pronto: {DB}')
else:
    print(f'INFO: Nem {DB} nem {DB_GZ} existem.')
    print(f'INFO: Esperado no Railway - o dashboard le do PostgreSQL.')
    print(f'INFO: Seguindo em frente.')

sys.exit(0)