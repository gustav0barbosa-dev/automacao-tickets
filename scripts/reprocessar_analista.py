"""
Re-processa um conjunto específico de tickets, forçando
re-raspagem da fonte original e aplicação da anonimização nova.
"""
import sqlite3
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))

from getpass import getpass
from utils_help360 import criar_navegador, realizar_login
from programa5_enriquecer import (
    conectar, processar_ticket, CAMINHO_BANCO, URL_TICKET
)

# IDs dos 27 tickets da analista
IDS_ANALISTA = [
    110388, 110506, 110522, 110557, 110688, 110711, 110852, 111156,
    111161, 111180, 111186, 111231, 111232, 111233, 111234, 111418,
    111532, 111703, 111757, 111835, 111910, 112126, 112134, 112265,
    112313, 112328, 112372,
]


def main():
    print('=' * 60)
    print('RE-PROCESSAMENTO DOS 27 TICKETS DA ANALISTA')
    print('=' * 60)

    conn = conectar()

    # Verifica quais existem no banco
    ids_existentes = []
    for tid in IDS_ANALISTA:
        cur = conn.execute('SELECT id FROM tickets WHERE id = ?', (tid,))
        if cur.fetchone():
            ids_existentes.append(tid)
        else:
            print(f'⚠️  Ticket {tid} não existe no banco')

    print(f'\n✅ {len(ids_existentes)} tickets encontrados\n')

    # Reseta a flag enriquecido
    placeholders = ','.join('?' * len(ids_existentes))
    conn.execute(
        f'UPDATE tickets SET enriquecido = 0 WHERE id IN ({placeholders})',
        ids_existentes
    )
    conn.commit()

    # Login
    print('Abrindo navegador...')
    navegador = criar_navegador()
    senha = getpass('Digite sua senha do Help360: ')
    realizar_login(navegador, senha=senha)
    time.sleep(3)

    if 'sign_in' in (navegador.current_url or '').lower():
        print('❌ Login falhou.')
        navegador.quit()
        conn.close()
        return

    print(f'✅ Login OK\n')

    stats = {'ok': 0, 'erro': 0, 'movs': 0, 'msgs': 0}

    try:
        for i, tid in enumerate(ids_existentes, 1):
            print(f'[{i}/{len(ids_existentes)}] #{tid}')
            ok, movs, msgs, motivo = processar_ticket(navegador, conn, tid)
            if ok:
                stats['ok'] += 1
                stats['movs'] += movs
                stats['msgs'] += msgs
                print(f'      └─ {movs} movs, {msgs} msgs')
            else:
                stats['erro'] += 1
                print(f'      └─ ERRO: {motivo}')

            if i < len(ids_existentes):
                time.sleep(2)
    finally:
        navegador.quit()
        conn.close()

    print('\n' + '=' * 60)
    print(f'✅ Processados: {stats["ok"]}')
    print(f'❌ Erros: {stats["erro"]}')
    print(f'   Movs: {stats["movs"]}')
    print(f'   Msgs: {stats["msgs"]}')


if __name__ == '__main__':
    main()