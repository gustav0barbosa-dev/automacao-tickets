"""
Descomprime o banco de dados E roda a migração para o Postgres.
Roda automaticamente no Railway durante o deploy.
"""
import gzip
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DB = RAIZ / 'dados' / 'tickets.db'
DB_GZ = RAIZ / 'dados' / 'tickets.db.gz'
SCRIPT_MIGRAR = RAIZ / 'scripts' / 'migrar_sqlite_para_postgres.py'

# ---------- PARTE 1: Descomprimir ----------
if not DB_GZ.exists():
    print(f'❌ {DB_GZ} não existe!')
    raise SystemExit(1)

print(f'📦 Descomprimindo {DB_GZ} (sobrescrevendo {DB})...')
DB.parent.mkdir(parents=True, exist_ok=True)
with gzip.open(DB_GZ, 'rb') as f_in:
    with open(DB, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

print(f'✅ Banco pronto: {DB} ({DB.stat().st_size / 1e6:.1f} MB)')

# ---------- PARTE 2: Diagnóstico ----------
import sqlite3
c = sqlite3.connect(DB)
try:
    total = c.execute('SELECT COUNT(*) FROM movimentacoes').fetchone()[0]
    com_data = c.execute('SELECT COUNT(*) FROM movimentacoes WHERE data_movimentacao IS NOT NULL').fetchone()[0]
    com_de = c.execute('SELECT COUNT(*) FROM movimentacoes WHERE de_status IS NOT NULL').fetchone()[0]
    print(f'📊 Movimentações — total: {total}, com data: {com_data}, com de_status: {com_de}')
finally:
    c.close()

# ---------- PARTE 3: Migração para o Postgres ----------
if SCRIPT_MIGRAR.exists():
    print('\n' + '=' * 60)
    print('🔁 Rodando migração para Postgres...')
    print('=' * 60)
    resultado = subprocess.run(
        [sys.executable, str(SCRIPT_MIGRAR)],
        capture_output=False,  # deixa a saída aparecer no log
    )
    if resultado.returncode == 0:
        print('✅ Migração concluída')
    else:
        print(f'⚠️ Migração falhou com código {resultado.returncode}')
else:
    print(f'ℹ️ Script de migração não encontrado: {SCRIPT_MIGRAR}')