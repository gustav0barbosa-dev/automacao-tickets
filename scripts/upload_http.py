# ============================================================
# upload_http.py
# ============================================================
# Envia os CSVs para o backend do Railway via HTTP (porta 443).
# Funciona dentro da rede SPPREV (firewall libera apenas 80/443).
#
# Uso:
#     $env:BACKEND_URL = "https://automacao-tickets-production.up.railway.app"
#     python scripts/upload_http.py
# ============================================================

import os
import sys
from pathlib import Path

import requests


RAIZ = Path(__file__).resolve().parent.parent
PASTA_CSV = RAIZ / 'dados' / 'export_csv'


def enviar_csv(backend_url, tabela, caminho_csv):
    """Envia um CSV para o backend."""
    try:
        with open(caminho_csv, 'rb') as f:
            files = {'file': (f'{tabela}.csv', f, 'text/csv')}
            data = {'tabela': tabela}

            response = requests.post(
                f'{backend_url}/upload',
                files=files,
                data=data,
                timeout=180,  # 3 minutos
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

    if not backend_url:
        print('❌ Variável BACKEND_URL não configurada.')
        print()
        print('   No PowerShell:')
        print('   $env:BACKEND_URL = "https://automacao-tickets-production.up.railway.app"')
        print()
        print('   Ou passe como argumento:')
        print('   python scripts/upload_http.py "https://..."')
        if len(sys.argv) > 1:
            backend_url = sys.argv[1]
        else:
            return 1

    print('=' * 60)
    print('UPLOAD VIA HTTP → RAILWAY → NEON')
    print('=' * 60)
    print(f'📁 CSVs: {PASTA_CSV}')
    print(f'🌐 Backend: {backend_url}')
    print()

    if not PASTA_CSV.exists():
        print(f'❌ Pasta não encontrada: {PASTA_CSV}')
        print('   Rode primeiro: python scripts/banco.py')
        return 1

    # 1. Testa conexão com o backend
    print('🔌 Testando backend...')
    try:
        r = requests.get(f'{backend_url}/health', timeout=10)
        if r.status_code == 200:
            dados = r.json()
            if dados.get('status') == 'healthy':
                print(f'   ✅ Backend OK: {dados}')
            else:
                print(f'   ⚠️  Backend respondeu: {dados}')
                print('   Continuando mesmo assim...')
        else:
            print(f'   ❌ Backend retornou HTTP {r.status_code}')
            return 1
    except Exception as e:
        print(f'   ❌ Erro ao conectar: {e}')
        return 1

    # 2. Ordem de upload (respeita FKs)
    ordem = ['areas', 'analistas', 'tickets', 'movimentacoes', 'mensagens', 'snapshots']

    total = 0
    erros = 0

    for tabela in ordem:
        caminho = PASTA_CSV / f'{tabela}.csv'

        if not caminho.exists():
            print(f'\n⏭️  {tabela}.csv não encontrado')
            continue

        # Ignora CSVs vazios
        if caminho.stat().st_size < 10:
            print(f'\n⏭️  {tabela}.csv vazio')
            continue

        print(f'\n📤 {tabela}...')
        print(f'   Tamanho: {caminho.stat().st_size / 1024:.1f} KB')

        ok, n, erro = enviar_csv(backend_url, tabela, caminho)

        if ok:
            print(f'   ✅ {n} registros enviados')
            total += n
        else:
            print(f'   ❌ {erro}')
            erros += 1

    print()
    print('=' * 60)
    print(f'✅ {total} registros enviados')
    if erros > 0:
        print(f'⚠️  {erros} tabela(s) com erro')
    print('=' * 60)

    # 3. Verifica status final
    if erros == 0:
        print('\n📊 Verificando status final no servidor...')
        try:
            r = requests.get(f'{backend_url}/status', timeout=10)
            if r.status_code == 200:
                print(r.json())
        except Exception:
            pass

    return 0 if erros == 0 else 1


if __name__ == '__main__':
    sys.exit(main())