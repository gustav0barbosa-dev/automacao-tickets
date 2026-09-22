# ============================================================
# upload_neon_api.py
# ============================================================
"""
Sobe os CSVs para o Neon via Data API (HTTP/HTTPS - porta 443).
Não precisa da porta 5432.

Uso:
    $env:NEON_API_URL = "https://ep-xxx.apirest.us-east-2.aws.neon.tech/neondb/rest/v1"
    $env:NEON_API_KEY = "sua_api_key_aqui"
    python scripts upload_neon_api.py
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests


RAIZ = Path(__file__).resolve().parent.parent
PASTA_CSV = RAIZ / 'dados' / 'export_csv'


def enviar_batch(api_url, api_key, tabela, registros):
    """Envia lote de registros via API."""
    url = f'{api_url}/{tabela}'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    }

    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(registros, default=str),
        timeout=60,
    )

    if response.status_code in (200, 201, 204):
        return True, None
    else:
        return False, f'HTTP {response.status_code}: {response.text[:200]}'


def limpar_registro(registro):
    """Remove NaN e converte tipos."""
    limpo = {}
    for k, v in registro.items():
        if pd.isna(v):
            limpo[k] = None
        elif isinstance(v, pd.Timestamp):
            limpo[k] = v.isoformat()
        else:
            limpo[k] = v
    return limpo


def main():
    api_url = os.environ.get('NEON_API_URL')
    api_key = os.environ.get('NEON_API_KEY')

    if not api_url or not api_key:
        print('❌ Variáveis não configuradas:')
        print('   $env:NEON_API_URL = "https://..."')
        print('   $env:NEON_API_KEY = "..."')
        return 1

    print('=' * 60)
    print('UPLOAD VIA NEON DATA API')
    print('=' * 60)
    print(f'📁 CSVs: {PASTA_CSV}')
    print(f'🔗 API: {api_url[:60]}')
    print()

    if not PASTA_CSV.exists():
        print(f'❌ Pasta não encontrada: {PASTA_CSV}')
        return 1

    ordem = ['areas', 'analistas', 'tickets', 'movimentacoes', 'mensagens', 'snapshots']
    total = 0

    for tabela in ordem:
        caminho = PASTA_CSV / f'{tabela}.csv'
        if not caminho.exists():
            print(f'⏭️  {tabela}.csv não encontrado')
            continue

        df = pd.read_csv(caminho)
        n = len(df)

        if n == 0:
            print(f'⏭️  {tabela}: vazio')
            continue

        print(f'\n📤 {tabela}: {n} registros')

        # Limpa dados
        registros = [limpar_registro(r) for r in df.to_dict('records')]

        # Envia em lotes de 500
        enviados = 0
        erros = 0

        for i in range(0, n, 500):
            lote = registros[i:i+500]
            ok, erro = enviar_batch(api_url, api_key, tabela, lote)
            if ok:
                enviados += len(lote)
                print(f'   Lote {i//500 + 1}: {len(lote)} OK')
            else:
                erros += len(lote)
                print(f'   Lote {i//500 + 1}: ERRO - {erro[:150]}')

        total += enviados

    print()
    print('=' * 60)
    print(f'✅ {total} registros enviados')
    print('=' * 60)


if __name__ == '__main__':
    sys.exit(main())