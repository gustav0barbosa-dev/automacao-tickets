# ============================================================
# programa5_enriquecer.py (v4 — COMPLETO)
# ============================================================
"""
Programa 5 — Enriquecimento de Tickets.

Para cada ticket que mudou no período:
  1. Abre /tickets/{id} e raspa os detalhes
  2. Baixa /export_ticket_histories/{id}.xlsx (movimentações)
  3. Extrai as mensagens da seção HTML feed-activity-list
  4. Persiste em tickets + movimentacoes + mensagens
  5. Marca ticket como 'enriquecido = 1'

Uso:
    python src/programa5_enriquecer.py                # últimos 30 dias
    python src/programa5_enriquecer.py --dias 7       # últimos 7 dias
    python src/programa5_enriquecer.py --ticket 111005
    python src/programa5_enriquecer.py --desde 2026-01-01
    python src/programa5_enriquecer.py --limite 10
"""

import argparse
import sqlite3
import sys
import time
from datetime import datetime
from getpass import getpass
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from selenium.webdriver.common.by import By

# ==================== PATHS ====================
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROJETO / 'src'))

from utils_help360 import criar_navegador, realizar_login


# ==================== CONFIGURAÇÃO ====================
PASTA_DADOS = RAIZ_PROJETO / 'dados'
PASTA_LOGS = PASTA_DADOS / 'logs'
CAMINHO_BANCO = PASTA_DADOS / 'tickets.db'
PASTA_HISTORICOS = PASTA_DADOS / 'historicos'

URL_TICKET = 'https://spprev.help360.com.br/tickets/{id}'
URL_HISTORICO = 'https://spprev.help360.com.br/export_ticket_histories/{id}.xlsx'

DELAY_ENTRE_TICKETS = 2
USUARIO_PADRAO = None  # lê do config/settings.yaml ou pergunta
MAX_FALHAS_SEGUIDAS = 5


# ==================== LOG ====================
def log(mensagem, nivel='INFO'):
    agora = datetime.now().strftime('%H:%M:%S')
    emoji = {'INFO': 'ℹ️', 'OK': '✅', 'AVISO': '⚠️', 'ERRO': '❌'}.get(nivel, '•')
    linha = f'[{agora}] {emoji} {mensagem}'
    print(linha)

    PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    arquivo = PASTA_LOGS / f'programa5_{datetime.now():%Y-%m-%d}.log'
    with open(arquivo, 'a', encoding='utf-8') as f:
        f.write(linha + '\n')


# ==================== BANCO ====================
def conectar():
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def listar_tickets(conn, limite=None, ticket_id=None, dias=None,
                   desde=None, todos=False):
    """Lista tickets para enriquecer (só os com enriquecido=0)."""
    if ticket_id:
        cur = conn.execute('SELECT id FROM tickets WHERE id = ?', (int(ticket_id),))
        return [r[0] for r in cur.fetchall()]

    sql = 'SELECT id FROM tickets WHERE enriquecido = 0'
    params = []

    if not todos:
        if dias is not None:
            sql += " AND alterado_data >= date('now', ?)"
            params.append(f'-{dias} days')
        elif desde:
            sql += ' AND alterado_data >= ?'
            params.append(desde)

    sql += ' ORDER BY alterado_data DESC'
    if limite:
        sql += ' LIMIT ?'
        params.append(limite)

    cur = conn.execute(sql, params)
    return [r[0] for r in cur.fetchall()]


def marcar_skip(conn, ticket_id):
    """Marca ticket como 'tentou e falhou' (enriquecido=3)."""
    conn.execute('UPDATE tickets SET enriquecido = 3 WHERE id = ?', (ticket_id,))
    conn.commit()


def salvar_historico_local(ticket_id, df):
    PASTA_HISTORICOS.mkdir(parents=True, exist_ok=True)
    df.to_excel(PASTA_HISTORICOS / f'{ticket_id}.xlsx', index=False)


# ==================== HELPERS ====================
def parsear_data_br(texto):
    """Parseia datas em vários formatos BR."""
    if texto is None:
        return None

    if hasattr(texto, 'year'):
        return pd.Timestamp(texto)

    texto = str(texto).strip()
    if not texto or texto.lower() in ('nan', 'nat', 'none', ''):
        return None

    for fmt in (
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y - %H:%M',
        '%d/%m/%Y %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%d/%m/%Y',
    ):
        try:
            return pd.to_datetime(texto, format=fmt)
        except Exception:
            continue

    try:
        return pd.to_datetime(texto, dayfirst=True, errors='coerce')
    except Exception:
        return None


def parsear_data_hora_br(texto):
    """Parseia '14/08/2026 às 13:45' ou variações."""
    if not texto:
        return None
    texto = texto.replace(' às ', ' ').replace('às', ' ').strip()
    texto = ' '.join(texto.split())

    for fmt in ('%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y'):
        try:
            return pd.to_datetime(texto, format=fmt)
        except Exception:
            continue
    return None


# ==================== PARSER: DETALHES ====================
def extrair_campo(navegador, label_texto):
    try:
        xpath = (
            f"//label[contains(normalize-space(text()), '{label_texto}')]"
            f"/following-sibling::div[contains(@class, 'col-sm')]"
        )
        el = navegador.find_element(By.XPATH, xpath)
        txt = el.text.strip()
        return None if txt in ('', '-', '--') else txt
    except Exception:
        return None


def extrair_detalhes(navegador):
    mapa = {
        'titulo':        'Título',
        'descricao':     'Descrição',
        'criado_data':   'Criado em',
        'alterado_data': 'Alterado em',
        'responsavel':   'Responsável',
        'previsao':      'Previsão para solução',
        'categoria':     'Categoria',
        'empresa':       'Empresa',              
        'prioridade':    'Prioridade',
        'solicitante':   'Solicitante',
        'status':        'Status',
        'area':          'Área',                 
        'sistema':       'Sistema',              
        'solucao':       'Solução',              
        'classificacao': 'Classificação',        
    }
    return {k: extrair_campo(navegador, v) for k, v in mapa.items()}


# ==================== PARSER: MOVIMENTAÇÕES (Excel) ====================
def baixar_historico(navegador, ticket_id):
    try:
        cookies = {c['name']: c['value'] for c in navegador.get_cookies()}
        r = requests.get(URL_HISTORICO.format(id=ticket_id),
                         cookies=cookies, timeout=30)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


def parsear_historico(conteudo_bytes, ticket_id):
    try:
        df = pd.read_excel(BytesIO(conteudo_bytes))
        df.columns = [str(c).strip() for c in df.columns]
        salvar_historico_local(ticket_id, df)
        return df
    except Exception:
        return None


def persistir_movimentacoes(conn, ticket_id, df_hist):
    """Persiste movimentações extraídas do Excel, ordenando por data
    e preenchendo de_status com o status anterior."""
    if df_hist is None or df_hist.empty:
        return 0

    conn.execute('DELETE FROM movimentacoes WHERE ticket_id = ?', (ticket_id,))

    # Ordena por data (mais antiga primeiro)
    df = df_hist.copy()
    df['_data_ordem'] = df['Alterado Data'].apply(parsear_data_br)
    df = df.sort_values('_data_ordem', ascending=True).reset_index(drop=True)

    inseridos = 0
    status_anterior = None

    from utils_anonimizacao import anonimizar_texto

    # ... (código anterior)

    # Anonimiza antes de inserir
    for campo in ['autor', 'comentario']:
        if campo in df.columns:
            df[campo] = df[campo].apply(
                lambda x: anonimizar_texto(x) if pd.notna(x) else x
            )

    for _, row in df.iterrows():
        try:
            data_mov = parsear_data_br(row.get('Alterado Data'))

            status = row.get('Status')
            status = str(status).strip() if pd.notna(status) else None

            autor = row.get('Alterado por')
            autor = str(autor).strip() if pd.notna(autor) else None

            responsavel = row.get('Responsável')
            responsavel = str(responsavel).strip() if pd.notna(responsavel) else None

            conn.execute('''
                INSERT INTO movimentacoes
                    (ticket_id, data_movimentacao, autor, tipo, de_status, para_status, comentario)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticket_id,
                data_mov.strftime('%Y-%m-%d %H:%M:%S') if data_mov is not None else None,
                autor,
                'historico',
                status_anterior,
                status,
                f'Responsável: {responsavel}' if responsavel else None,
            ))
            inseridos += 1

            if status:
                status_anterior = status
        except Exception as e:
            log(f'Erro persistindo mov. do #{ticket_id}: {e}', 'AVISO')

    conn.commit()
    return inseridos


# ==================== PARSER: MENSAGENS (HTML) ====================
def extrair_mensagens(navegador):
    """
    Extrai mensagens da seção HTML:
        <div class="feed-activity-list">
            <div class="feed-element">
                <div class="media-body">
                    <strong>AUTOR</strong> escreveu em
                    <small>DD/MM/AAAA às HH:MM</small>
                    <div class="well">CONTEÚDO</div>
                </div>
            </div>
        </div>
    """
    mensagens = []
    try:
        elementos = navegador.find_elements(
            By.CSS_SELECTOR, '.feed-activity-list .feed-element'
        )

        for el in elementos:
            try:
                autor = el.find_element(By.CSS_SELECTOR, 'strong').text.strip()
            except Exception:
                autor = None

            try:
                data_str = el.find_element(By.CSS_SELECTOR, 'small').text.strip()
                data_hora = parsear_data_hora_br(data_str)
            except Exception:
                data_hora = None

            try:
                conteudo = el.find_element(By.CSS_SELECTOR, '.well').text.strip()
            except Exception:
                conteudo = ''

            anexo = None
            try:
                anexo = el.find_element(By.CSS_SELECTOR, '.fa-paperclip a').text.strip()
            except Exception:
                pass

            if autor:
                mensagens.append({
                    'autor': autor,
                    'data_hora': data_hora,
                    'conteudo': conteudo,
                    'anexo': anexo,
                })
    except Exception as e:
        log(f'Erro extraindo mensagens: {e}', 'AVISO')

    return mensagens


def persistir_mensagens(conn, ticket_id, mensagens):
    if not mensagens:
        return 0

    conn.execute('DELETE FROM mensagens WHERE ticket_id = ?', (ticket_id,))

    inseridos = 0

    for m in mensagens:
        m['autor'] = anonimizar_texto(m.get('autor'))
        m['conteudo'] = anonimizar_texto(m.get('conteudo'))

    for m in mensagens:
        try:
            data_str = (m['data_hora'].strftime('%Y-%m-%d %H:%M:%S')
                        if m['data_hora'] is not None else None)
            conteudo = m['conteudo']
            if m.get('anexo'):
                conteudo = f'[Anexo: {m["anexo"]}] {conteudo}'

            conn.execute('''
                INSERT INTO mensagens
                    (ticket_id, data_hora, autor, tipo, conteudo)
                VALUES (?, ?, ?, ?, ?)
            ''', (ticket_id, data_str, m['autor'], 'comentario', conteudo))
            inseridos += 1
        except Exception as e:
            log(f'Erro salvando mensagem: {e}', 'AVISO')

    conn.commit()
    return inseridos


# ==================== ATUALIZAÇÃO DE TICKET ====================
def atualizar_ticket(conn, ticket_id, detalhes):
    """Atualiza os campos do ticket, incluindo os novos (classificacao, area, etc)."""
    prev = parsear_data_br(detalhes.get('previsao'))
    prev_str = prev.strftime('%Y-%m-%d %H:%M:%S') if prev is not None else None

    # Anonimiza os campos antes do UPDATE
    for campo in ['titulo', 'descricao', 'solucao', 'diagnostico']:
        if campo in detalhes and detalhes[campo]:
            detalhes[campo] = anonimizar_texto(detalhes[campo])

    conn.execute('''
        UPDATE tickets SET
            titulo            = COALESCE(?, titulo),
            descricao         = COALESCE(?, descricao),
            categoria         = COALESCE(?, categoria),
            status            = COALESCE(?, status),
            prioridade        = COALESCE(?, prioridade),
            responsavel_atual = COALESCE(?, responsavel_atual),
            solicitante       = COALESCE(?, solicitante),
            previsao          = COALESCE(?, previsao),
            classificacao     = COALESCE(?, classificacao),
            area              = COALESCE(?, area),
            empresa           = COALESCE(?, empresa),
            solucao           = COALESCE(?, solucao),
            sistema           = COALESCE(?, sistema),
            backlog           = COALESCE(?, backlog),         -- ← NOVO
            enriquecido       = 1,
            atualizado_em     = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (
        detalhes.get('titulo'),
        detalhes.get('descricao'),
        detalhes.get('categoria'),
        detalhes.get('status'),
        detalhes.get('prioridade'),
        detalhes.get('responsavel'),
        detalhes.get('solicitante'),
        prev_str,
        detalhes.get('classificacao'),
        detalhes.get('area'),
        detalhes.get('empresa'),
        detalhes.get('solucao'),
        detalhes.get('sistema'),
        detalhes.get('backlog', 0),                                # ← NOVO
        ticket_id,
    ))
    conn.commit()


# ==================== PROCESSAMENTO ====================
def processar_ticket(navegador, conn, ticket_id):
    """Retorna (sucesso, num_movs, num_msgs, motivo)."""
    try:
        navegador.get(URL_TICKET.format(id=ticket_id))
        time.sleep(2)

        if 'sign_in' in (navegador.current_url or '').lower():
            return (False, 0, 0, 'caiu em login')

        detalhes = extrair_detalhes(navegador)
        if not detalhes.get('titulo'):
            return (False, 0, 0, 'sem título')

        # ---------- NOVO: detecta backlog ----------
        eh_backlog = detectar_backlog(navegador)

        # Adiciona ao dicionário de detalhes
        detalhes['backlog'] = 1 if eh_backlog else 0

        atualizar_ticket(conn, ticket_id, detalhes)

        # Movimentações (Excel)
        movs = 0
        conteudo = baixar_historico(navegador, ticket_id)
        if conteudo:
            df_hist = parsear_historico(conteudo, ticket_id)
            movs = persistir_movimentacoes(conn, ticket_id, df_hist)

        # Mensagens (HTML)
        msgs = 0
        mensagens = extrair_mensagens(navegador)
        if mensagens:
            msgs = persistir_mensagens(conn, ticket_id, mensagens)

        return (True, movs, msgs, None)

    except Exception as e:
        return (False, 0, 0, f'exceção: {type(e).__name__}')

# ==================== detecta backlogs ====================
def detectar_backlog(navegador):
    """
    Detecta se o ticket possui a mensagem 'Este ticket se tornou um Backlog'
    ou variações.

    Retorna:
        True se for backlog, False caso contrário
    """
    try:
        # Busca em todo o HTML/texto visível
        page_text = navegador.find_element(By.TAG_NAME, 'body').text

        # Palavras-chave que indicam backlog
        keywords = [
            'se tornou um backlog',
            'se tornou backlog',
            'em backlog',
            'aguardando backlog',
            'ticket backlog',
        ]

        page_lower = page_text.lower()
        for kw in keywords:
            if kw in page_lower:
                return True

        return False
    except Exception:
        return False

# ==================== MAIN ====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limite', type=int)
    parser.add_argument('--ticket', type=str)
    parser.add_argument('--dias', type=int, default=30)
    parser.add_argument('--desde', type=str)
    parser.add_argument('--todos', action='store_true')
    parser.add_argument('--usuario', type=str, default=USUARIO_PADRAO)
    args = parser.parse_args()

    inicio = datetime.now()

    print('=' * 60)
    print('PROGRAMA 5 — ENRIQUECIMENTO DE TICKETS')
    print('=' * 60)
    print(f'📁 Banco: {CAMINHO_BANCO}')

    if not CAMINHO_BANCO.exists():
        log('Banco não encontrado. Rode o Programa4 primeiro.', 'ERRO')
        return False

    conn = conectar()

    if args.todos:
        conn.execute('UPDATE tickets SET enriquecido = 0')
        conn.commit()
        log('Flag "enriquecido" resetada para TODOS.', 'AVISO')

    if args.ticket:
        modo = f'ticket específico #{args.ticket}'
    elif args.todos:
        modo = 'TODOS'
    elif args.desde:
        modo = f'alterados desde {args.desde}'
    else:
        modo = f'alterados nos últimos {args.dias} dias'

    print(f'🎯 Modo: {modo}')

    ids = listar_tickets(conn, args.limite, args.ticket,
                         args.dias, args.desde, args.todos)

    if not ids:
        log('Nenhum ticket para enriquecer.', 'OK')
        conn.close()
        return True

    print()
    log(f'{len(ids)} ticket(s) a processar')

    # Navegador + login
    log('Abrindo navegador...')
    navegador = criar_navegador()
    senha = getpass('Digite sua senha: ')
    realizar_login(navegador, usuario=args.usuario, senha=senha)
    time.sleep(3)

    if 'sign_in' in (navegador.current_url or '').lower():
        log('❌ Login falhou. Abortando.', 'ERRO')
        navegador.quit()
        conn.close()
        return False

    log(f'✅ Login OK: {navegador.current_url}')

    # Contadores
    stats = {'ok': 0, 'skip': 0, 'erro': 0, 'movs': 0, 'msgs': 0}
    falhas_seguidas = 0

    try:
        for i, tid in enumerate(ids, 1):
            log(f'[{i}/{len(ids)}] #{tid}')

            ok, movs, msgs, motivo = processar_ticket(navegador, conn, tid)

            if ok:
                stats['ok'] += 1
                stats['movs'] += movs
                stats['msgs'] += msgs
                falhas_seguidas = 0
                print(f'      └─ {movs} movimentações, {msgs} mensagens')
            else:
                marcar_skip(conn, tid)
                stats['skip'] += 1
                falhas_seguidas += 1
                print(f'      └─ pulado ({motivo})')

                if falhas_seguidas >= MAX_FALHAS_SEGUIDAS:
                    log(f'❌ {MAX_FALHAS_SEGUIDAS} falhas seguidas. Abortando.', 'ERRO')
                    break

            if i < len(ids):
                time.sleep(DELAY_ENTRE_TICKETS)

    except KeyboardInterrupt:
        log('Interrompido pelo usuário.', 'AVISO')
    except Exception as e:
        log(f'Erro inesperado: {e}', 'ERRO')
    finally:
        try:
            navegador.quit()
        except Exception:
            pass
        conn.close()

    tempo_total = (datetime.now() - inicio).total_seconds()
    print()
    print('=' * 60)
    print('✅ ENRIQUECIMENTO CONCLUÍDO')
    print('=' * 60)
    print(f'   Processados   : {stats["ok"]}')
    print(f'   Pulados       : {stats["skip"]}')
    print(f'   Movimentações : {stats["movs"]}')
    print(f'   Mensagens     : {stats["msgs"]}')
    print(f'   Tempo total   : {tempo_total:.1f}s')

    return True


if __name__ == '__main__':
    sucesso = main()
    sys.exit(0 if sucesso else 1)