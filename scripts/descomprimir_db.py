"""
Descomprime o banco de dados SEMPRE, sobrescrevendo qualquer versão antiga.
Roda automaticamente no Railway durante o deploy.
"""
import gzip
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DB = RAIZ / 'dados' / 'tickets.db'
DB_GZ = RAIZ / 'dados' / 'tickets.db.gz'

if not DB_GZ.exists():
    print(f'❌ {DB_GZ} não existe! Verifique o repositório.')
    raise SystemExit(1)

# SEMPRE sobrescreve (garante que o banco do deploy é o mais recente)
print(f'📦 Descomprimindo {DB_GZ} (sobrescrevendo {DB})...')
DB.parent.mkdir(parents=True, exist_ok=True)
with gzip.open(DB_GZ, 'rb') as f_in:
    with open(DB, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

print(f'✅ Banco pronto: {DB} ({DB.stat().st_size / 1e6:.1f} MB)')

# Diagnóstico: confirma quantas movimentações têm data
import sqlite3
c = sqlite3.connect(DB)
try:
    total = c.execute('SELECT COUNT(*) FROM movimentacoes').fetchone()[0]
    com_data = c.execute('SELECT COUNT(*) FROM movimentacoes WHERE data_movimentacao IS NOT NULL').fetchone()[0]
    com_de = c.execute('SELECT COUNT(*) FROM movimentacoes WHERE de_status IS NOT NULL').fetchone()[0]
    print(f'📊 Movimentações — total: {total}, com data: {com_data}, com de_status: {com_de}')
finally:
    c.close()