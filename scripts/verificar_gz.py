"""Verifica o total de tickets no .gz."""
import gzip
import shutil
import sqlite3
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GZ = RAIZ / 'dados' / 'tickets.db.gz'

tmp = Path(tempfile.gettempdir()) / 'check.db'
with gzip.open(GZ, 'rb') as f_in, open(tmp, 'wb') as f_out:
    shutil.copyfileobj(f_in, f_out)

conn = sqlite3.connect(tmp)
n = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
conn.close()

print(f'.gz: {n} tickets')

# Limpa
tmp.unlink()