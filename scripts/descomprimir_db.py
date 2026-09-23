"""
Descomprime o banco de dados antes do dashboard iniciar.
Roda automaticamente no Railway durante o deploy.
"""
import gzip
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DB = RAIZ / 'dados' / 'tickets.db'
DB_GZ = RAIZ / 'dados' / 'tickets.db.gz'

# Se o banco já existe (do banco commitado ou de execução anterior), não faz nada
if DB.exists() and DB.stat().st_size > 1_000_000:
    print(f'✅ Banco já existe: {DB} ({DB.stat().st_size / 1e6:.1f} MB)')
    raise SystemExit(0)

if DB_GZ.exists():
    print(f'📦 Descomprimindo {DB_GZ}...')
    DB.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(DB_GZ, 'rb') as f_in:
        with open(DB, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    print(f'✅ Banco pronto: {DB} ({DB.stat().st_size / 1e6:.1f} MB)')
else:
    print(f'❌ Nem {DB} nem {DB_GZ} existem! Verifique o repositório.')
    raise SystemExit(1)