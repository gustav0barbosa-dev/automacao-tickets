#!/usr/bin/env python
# ============================================================
# backend/migrar_sqlite_para_postgres.py
# ============================================================
"""
Compatibilidade com o backend Flask (/atualizar).

A implementação canônica da migração está em
scripts/migrar_sqlite_para_postgres.py. Este arquivo apenas delega a
ela, para que o backend continue funcionando sem duplicar código.

Regras preservadas (sem DROP/CREATE/TRUNCATE, idempotência via
ON CONFLICT DO NOTHING).
"""

import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / 'scripts'

# Carrega a implementação canônica sem cair em import circular, pois os
# dois arquivos têm o mesmo nome (migrar_sqlite_para_postgres.py).
CAMINHO_CANONICO = SCRIPTS / 'migrar_sqlite_para_postgres.py'
if not CAMINHO_CANONICO.exists():
    raise FileNotFoundError(
        f'Script canônico não encontrado: {CAMINHO_CANONICO}'
    )

_spec = importlib.util.spec_from_file_location(
    'migrar_sqlite_para_postgres_canonico', CAMINHO_CANONICO
)
_modulo = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _modulo
_spec.loader.exec_module(_modulo)

main = _modulo.main

if __name__ == '__main__':
    sys.exit(main())
