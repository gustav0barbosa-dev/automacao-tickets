# ============================================================
# upload_http.py
# ============================================================
# Envia os CSVs para o backend do Railway via HTTP (porta 443).
#
# Uso:
#     $env:BACKEND_URL = "https://seu-backend.up.railway.app"
#     $env:API_KEY = "sua-chave"
#     python scripts/upload_http.py
# ============================================================

import os
import sys
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
PASTA_CSV = RAIZ / 'dados' / 'export_csv'


def enviar_csv(backend_url, api_key, tabela, caminho_csv):
    """Envia um CSV para o backend (com autenticação)."""
    try:
        with open(caminho_csv, 'rb') as f:
            files = {'file': (f'{tabela}.csv', f, 'text/csv')}
            data = {'tabela': tabela}
            headers = {'X-API-Key': api_key}

            response = requests.post(
                f'{backend_url}/upload',
                headers=headers,
                files=files,
                data=data,
                timeout=180,
            )

        if response.status_code == 200:
            resultado = response.json()
            return True, resultado.get('linhas_inseridas', 0), None
        else:
            return False, 0, f'HTTP {response.status_code}: {response.text[:200]}'

    except requests.exceptions.Timeout:
        return False, 0, 'Timeout (>3 min)'
    except Exception as e:
        return False, 0, str(e)[:200]


def main():
    backend_url = os.environ.get('BACKEND_URL')
    api_key = os.environ.get('API_KEY')

    if not backend_url:
        print('❌ Variável BACKEND_URL não configurada.')
        print('   Configure com: $env:BACKEND_URL = "https://..."')
        return 1

    if not api_key:
        print('❌ Variável API_KEY não configurada.')
        print('   Configure com: $env:API_KEY = "sua-chave"')
        return 1

    print('=' * 60)
    print('UPLOAD HTTP — CSV → Backend → Neon')
    print('=' * 60)
    print(f'🌐 Backend: {backend_url}')
    print(f'🔑 API key: {api_key[:8]}...')
    print(f'📁 CSVs: {PASTA_CSV}')
    print()

    if not PASTA_CSV.exists():
        print(f'❌ Pasta não encontrada: {PASTA_CSV}')
        return 1

    tabelas = ['tickets', 'movimentacoes', 'mensagens', 'analistas', 'snapshots']
    total = 0
    erros = 0

    for tabela in tabelas:
        caminho = PASTA_CSV / f'{tabela}.csv'
        if not caminho.exists():
            print(f'⚠️  {tabela}.csv não encontrado')
            continue

        if caminho.stat().st_size < 10:
            print(f'⚠️  {tabela}.csv vazio')
            continue

        print(f'📤 {tabela} ({caminho.stat().st_size / 1024:.1f} KB)...', end=' ')
        ok, n, erro = enviar_csv(backend_url, api_key, tabela, caminho)

        if ok:
            print(f'✅ {n} registros')
            total += n
        else:
            print(f'❌ {erro}')
            erros += 1

    print()
    print('=' * 60)
    print(f'✅ Total: {total} registros')
    print(f'❌ Erros: {erros}')
    print('=' * 60)

    return 0 if erros == 0 else 1


if __name__ == '__main__':
    sys.exit(main())