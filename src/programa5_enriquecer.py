# ============================================================
# programa5_enriquecer.py (v7 — HISTÓRICO VIA HTML)
# ============================================================
"""
Programa 5 — Enriquecimento de Tickets.

MUDANÇAS v7:
  - Extrai o HISTÓRICO completo direto do HTML (não do Excel)
  - Captura Solução, Mensagem e Comentário interno
  - Captura Alterado por, Status, Prioridade
  - Persiste movimentações com conteúdo REAL
"""

import argparse
import re
import sqlite3
import sys
import time
from datetime import datetime
from getpass import getpass
from pathlib import Path

import pandas as pd
from selenium.webdriver.common.by import By

# ==================== PATHS ====================
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROJETO / 'src'))
sys.path.insert(0, str(RAIZ_PROJETO / 'scripts'))

from utils_help360 import criar_navegador, realizar_login
from utils_anonimizacao import anonimizar_texto


# ==================== CONFIGURAÇÃO ====================
PASTA_DADOS = RAIZ_PROJETO / 'dados'
PASTA_LOGS = PASTA_DADOS / 'logs'
CAMINHO_BANCO = PASTA_DADOS / 'tickets.db'
PASTA_DEBUG = PASTA_DADOS / 'debug_html'

URL_TICKET = 'https://spprev.help360.com.br/tickets/{id}'

DELAY_ENTRE_TICKETS = 2
USUARIO_PADRAO = None
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
    conn.execute('UPDATE tickets SET enriquecido = 3 WHERE id = ?', (ticket_id,))
    conn.commit()


# ==================== HELPERS ====================
def parsear_data_br(texto):
    if texto is None:
        return None
    if hasattr(texto, 'year'):
        return pd.Timestamp(texto)

    texto = str(texto).strip()
    if not texto or texto.lower() in ('nan', 'nat', 'none', ''):
        return None

    # Tenta pegar "01/10/2026 - 17:08"
    for fmt in (
        '%d/%m/%Y - %H:%M',
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y - %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y',
    ):
        try:
            return pd.to_datetime(texto, format=fmt)
        except Exception:
            continue

    # Fallback: tenta achar a data no texto
    match = re.search(r'(\d{2}/\d{2}/\d{4})[\s-]+(\d{2}:\d{2})', texto)
    if match:
        try:
            return pd.to_datetime(f'{match.group(1)} {match.group(2)}',
                                   format='%d/%m/%Y %H:%M')
        except Exception:
            pass

    try:
        return pd.to_datetime(texto, dayfirst=True, errors='coerce')
    except Exception:
        return None


def parsear_data_hora_br(texto):
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


# ==================== PARSER: HISTÓRICO (HTML) ====================
def extrair_historico_html(navegador, ticket_id=None):
    """
    Extrai o histórico do ticket direto do HTML.
    Corrige soluções acumuladas do Help360.
    """
    def limpar_conteudo(texto):
        """Remove conteúdo acumulado (soluções/mensagens anteriores)."""
        if not texto:
            return texto
        # Separador com espaços (Selenium remove \n)
        for sep in ['-- - -', '--\n-\n-', '\n\n\n']:
            if sep in texto:
                texto = texto.split(sep)[0]
        return texto.strip()

    historico = []

    try:
        tabela = None
        tabelas = navegador.find_elements(By.CSS_SELECTOR, 'table.table-striped')

        for t in tabelas:
            try:
                thead = t.find_element(By.CSS_SELECTOR, 'thead')
                if 'prioridade' in thead.text.lower() and 'alterado por' in thead.text.lower():
                    tabela = t
                    break
            except Exception:
                continue

        if tabela is None:
            return []

        linhas = tabela.find_elements(By.CSS_SELECTOR, 'tbody tr')
        mov_atual = None
        ultima_solucao = None
        ultima_mensagem = None

        for linha in linhas:
            try:
                cells = linha.find_elements(By.CSS_SELECTOR, 'td')
                if not cells:
                    continue

                primeira_cell = cells[0].text.strip()

                # ==================== SOLUÇÃO ====================
                if 'Solução:' in primeira_cell:
                    if mov_atual and len(cells) >= 2:
                        texto = cells[1].text.strip()
                        texto_limpo = limpar_conteudo(texto)
                        
                        # ⬇️ SÓ adiciona se o status for "Resolvido" ou "Fechado"
                        if mov_atual.get('status') in ('Resolvido', 'Fechado'):
                            if texto_limpo != ultima_solucao:
                                mov_atual['solucao'] = texto_limpo
                                ultima_solucao = texto_limpo
                    continue

                # ==================== MENSAGEM ====================
                if 'Mensagem:' in primeira_cell:
                    if mov_atual and len(cells) >= 2:
                        texto = cells[1].text.strip()
                        texto_limpo = limpar_conteudo(texto)
                        
                        if texto_limpo != ultima_mensagem:
                            mov_atual['mensagem'] = texto_limpo
                            ultima_mensagem = texto_limpo
                    continue

                # ==================== COMENTÁRIO INTERNO ====================
                if 'Comentário interno:' in primeira_cell:
                    if mov_atual and len(cells) >= 2:
                        mov_atual['comentario_interno'] = limpar_conteudo(cells[1].text.strip())
                    continue

                # ==================== CABEÇALHO ====================
                if len(cells) >= 5:
                    if mov_atual is not None:
                        historico.append(mov_atual)

                    mov_atual = {
                        'prioridade':       cells[0].text.strip(),
                        'titulo':           cells[1].text.strip() if len(cells) > 1 else None,
                        'criado em':        cells[2].text.strip() if len(cells) > 2 else None,
                        'alterado em':      cells[3].text.strip() if len(cells) > 3 else None,
                        'status':           cells[4].text.strip() if len(cells) > 4 else None,
                        'categoria':        cells[5].text.strip() if len(cells) > 5 else None,
                        'empresa':          cells[6].text.strip() if len(cells) > 6 else None,
                        'responsavel':      cells[7].text.strip() if len(cells) > 7 else None,
                        'alterado por':     cells[8].text.strip() if len(cells) > 8 else None,
                        'solucao':          None,
                        'mensagem':         None,
                        'comentario_interno': None,
                    }

            except Exception:
                continue

        if mov_atual is not None:
            historico.append(mov_atual)

        return historico

    except Exception as e:
        log(f'Erro extraindo histórico HTML: {e}', 'AVISO')
        return []


def salvar_html_debug(navegador, ticket_id):
    """Salva o HTML pra debug."""
    try:
        PASTA_DEBUG.mkdir(parents=True, exist_ok=True)
        html = navegador.page_source
        arquivo = PASTA_DEBUG / f'{ticket_id}.html'
        arquivo.write_text(html, encoding='utf-8')
    except Exception as e:
        log(f'Erro salvando HTML debug: {e}', 'AVISO')


def persistir_movimentacoes(conn, ticket_id, historico):
    """Persiste movimentações extraídas do HTML."""
    if not historico:
        return 0

    conn.execute('DELETE FROM movimentacoes WHERE ticket_id = ?', (ticket_id,))

    inseridos = 0
    status_anterior = None

    for mov in historico:
        try:
            # Data
            data_str = mov.get('alterado em') or mov.get('criado em')
            data_mov = parsear_data_br(data_str)

            # Autor
            autor = mov.get('alterado por')

            # Status
            status = mov.get('status')

            # Comentário: junta solução + mensagem + comentário
            partes = []
            if mov.get('solucao'):
                partes.append(f"Solução: {mov['solucao']}")
            if mov.get('mensagem'):
                partes.append(f"Mensagem: {mov['mensagem']}")
            if mov.get('comentario_interno'):
                partes.append(f"Comentário: {mov['comentario_interno']}")

            comentario = ' | '.join(partes) if partes else None

            # Anonimiza
            if comentario:
                comentario = anonimizar_texto(comentario)

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
                comentario,
            ))
            inseridos += 1

            if status:
                status_anterior = status

        except Exception as e:
            log(f'Erro persistindo mov do #{ticket_id}: {e}', 'AVISO')

    conn.commit()
    return inseridos


# ==================== PARSER: MENSAGENS (HTML) ====================
def extrair_mensagens(navegador):
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
        try:
            data_str = (m['data_hora'].strftime('%Y-%m-%d %H:%M:%S')
                        if m['data_hora'] is not None else None)
            conteudo = m['conteudo']
            if m.get('anexo'):
                conteudo = f'[Anexo: {m["anexo"]}] {conteudo}'

            conteudo = anonimizar_texto(conteudo)

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
    prev = parsear_data_br(detalhes.get('previsao'))
    prev_str = prev.strftime('%Y-%m-%d %H:%M:%S') if prev is not None else None

    for campo in ['titulo', 'descricao', 'solucao', 'diagnostico']:
        if detalhes.get(campo):
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
        ticket_id,
    ))
    conn.commit()


# ==================== DETECTA BACKLOG ====================
def detectar_backlog(navegador):
    try:
        page_text = navegador.find_element(By.TAG_NAME, 'body').text
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


# ==================== PROCESSAMENTO ====================
def processar_ticket(navegador, conn, ticket_id):
    try:
        navegador.get(URL_TICKET.format(id=ticket_id))
        time.sleep(3)

        if 'sign_in' in (navegador.current_url or '').lower():
            return (False, 0, 0, 'caiu em login')

        # Salva HTML pra debug (primeiros 5 tickets)
        if ticket_id in (110506, 110522, 110557, 110688, 111186):
            salvar_html_debug(navegador, ticket_id)

        detalhes = extrair_detalhes(navegador)
        if not detalhes.get('titulo'):
            return (False, 0, 0, 'sem título')

        eh_backlog = detectar_backlog(navegador)
        detalhes['backlog'] = 1 if eh_backlog else 0

        atualizar_ticket(conn, ticket_id, detalhes)

        # ⬇️ HISTÓRICO VIA HTML
        historico = extrair_historico_html(navegador, ticket_id)
        movs = persistir_movimentacoes(conn, ticket_id, historico)

        # Mensagens (HTML)
        msgs = 0
        mensagens = extrair_mensagens(navegador)
        if mensagens:
            msgs = persistir_mensagens(conn, ticket_id, mensagens)

        return (True, movs, msgs, None)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (False, 0, 0, f'exceção: {type(e).__name__}: {e}')


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
    print('PROGRAMA 5 — ENRIQUECIMENTO (v7 — HTML)')
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

    # Login
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