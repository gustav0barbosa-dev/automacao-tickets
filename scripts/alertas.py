# ============================================================
# alertas.py
# ============================================================
"""
Envia alertas para o Microsoft Teams via Workflow Webhook.

Regras implementadas:
    A1 - SLA em risco (< 1 dia)
    A2 - SLA estourado
    A3 - Ticket travado SPPREV (> 3 dias sem ação)
    A4 - Backlog elevado
    A5 - Reincidência (mesmo solicitante 3+ tickets abertos)

Uso:
    python scripts/alertas.py                    # dry-run
    python scripts/alertas.py --enviar           # envia para Teams
    python scripts/alertas.py --regra A3         # só uma regra
"""

import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import yaml


# ==================== CONFIGURAÇÃO ====================
RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / 'dados' / 'tickets.db'
CONFIG = RAIZ / 'config' / 'settings.yaml'
LOG = RAIZ / 'dados' / 'logs' / 'alertas.log'


# ==================== LOG ====================
def log(mensagem, nivel='INFO'):
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    emoji = {'INFO': 'ℹ️', 'OK': '✅', 'AVISO': '⚠️', 'ERRO': '❌'}.get(nivel, '•')
    linha = f'[{agora}] {emoji} {mensagem}'
    print(linha)

    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(linha + '\n')


# ==================== CARREGA CONFIG ====================
def carregar_webhook():
    """Lê webhook de settings.yaml ou variável de ambiente."""
    # 1. Variável de ambiente
    webhook = os.environ.get('TEAMS_WEBHOOK')
    if webhook:
        return webhook

    # 2. Config YAML
    if CONFIG.exists():
        with open(CONFIG, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get('teams', {}).get('webhook_url')

    return None


# ==================== CONEXÃO ====================
def conectar():
    return sqlite3.connect(BANCO)


# ==================== REGRAS ====================
def regra_a1_sla_em_risco(conn):
    """SLA em risco: previsão < hoje + 1 dia."""
    df = pd.read_sql('''
        SELECT id, titulo, responsavel_atual, previsao
        FROM tickets
        WHERE status NOT IN ('Resolvido', 'Fechado', 'Cancelado')
          AND previsao IS NOT NULL
          AND previsao > datetime('now')
          AND previsao < datetime('now', '+1 day')
        ORDER BY previsao ASC
        LIMIT 20
    ''', conn)

    if df.empty:
        return None

    return {
        'codigo': 'A1',
        'titulo': f'🚨 SLA em Risco: {len(df)} ticket(s)',
        'resumo': f'{len(df)} tickets vão estourar o SLA nas próximas 24h',
        'df': df,
        'qtd': len(df),
    }


def regra_a2_sla_estourado(conn):
    """SLA estourado."""
    df = pd.read_sql('''
        SELECT id, titulo, responsavel_atual, previsao
        FROM tickets
        WHERE status NOT IN ('Resolvido', 'Fechado', 'Cancelado')
          AND previsao IS NOT NULL
          AND previsao <= datetime('now')
        ORDER BY previsao ASC
        LIMIT 20
    ''', conn)

    if df.empty:
        return None

    return {
        'codigo': 'A2',
        'titulo': f'🔴 SLA Estourado: {len(df)} ticket(s)',
        'resumo': f'{len(df)} tickets com SLA estourado',
        'df': df,
        'qtd': len(df),
    }


def regra_a3_ticket_travado(conn):
    """Ticket travado SPPREV."""
    df = pd.read_sql('''
        SELECT id, titulo, responsavel_atual,
               CAST(julianday('now') - julianday(criado_data) AS INTEGER) AS dias_aberto
        FROM tickets
        WHERE status IN ('Em atendimento', 'Aguardando confirmação do usuário')
          AND responsavel_empresa = 'SPPREV'
          AND acao_interna = 1
          AND backlog = 0
          AND (julianday('now') - julianday(criado_data)) > 3
        ORDER BY dias_aberto DESC
        LIMIT 20
    ''', conn)

    if df.empty:
        return None

    return {
        'codigo': 'A3',
        'titulo': f'⚠️ Tickets Travados SPPREV: {len(df)} caso(s)',
        'resumo': f'{len(df)} tickets sem ação real há mais de 3 dias',
        'df': df,
        'qtd': len(df),
    }


def regra_a4_backlog_grande(conn):
    """Backlog elevado."""
    df = pd.read_sql('''
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE backlog = 1
          AND status NOT IN ('Resolvido', 'Fechado', 'Cancelado')
    ''', conn)

    total = int(df['total'].iloc[0])
    if total < 10:
        return None

    return {
        'codigo': 'A4',
        'titulo': f'📊 Backlog Elevado: {total} ticket(s)',
        'resumo': f'{total} tickets na fila do backlog',
        'df': None,
        'qtd': total,
    }


def regra_a5_reincidencia(conn):
    """Solicitantes com 3+ tickets abertos."""
    df = pd.read_sql('''
        SELECT solicitante, COUNT(*) AS total
        FROM tickets
        WHERE status NOT IN ('Resolvido', 'Fechado', 'Cancelado')
          AND solicitante IS NOT NULL
          AND solicitante != ''
        GROUP BY solicitante
        HAVING COUNT(*) >= 3
        ORDER BY total DESC
        LIMIT 20
    ''', conn)

    if df.empty:
        return None

    return {
        'codigo': 'A5',
        'titulo': f'🔁 Reincidência: {len(df)} solicitante(s)',
        'resumo': f'{len(df)} solicitantes com 3+ tickets abertos',
        'df': df,
        'qtd': len(df),
    }


# ==================== REGISTRO ====================
REGRAS = {
    'A1': ('SLA em Risco',    regra_a1_sla_em_risco),
    'A2': ('SLA Estourado',   regra_a2_sla_estourado),
    'A3': ('Ticket Travado',  regra_a3_ticket_travado),
    'A4': ('Backlog Elevado', regra_a4_backlog_grande),
    'A5': ('Reincidência',    regra_a5_reincidencia),
}


# ==================== MONTAGEM DA MENSAGEM ====================
def montar_card(alerta):
    """
    Monta o payload de Adaptive Card aceito pelo webhook
    de Fluxos de Trabalho do Teams.
    """
    df = alerta.get('df')

    # Cor do tema por tipo
    cor_titulo = {
        'A1': 'Warning',
        'A2': 'Attention',
        'A3': 'Attention',
        'A4': 'Accent',
        'A5': 'Good',
    }.get(alerta['codigo'], 'Default')

    # Corpo do card
    body = [
        {
            "type": "TextBlock",
            "text": alerta['titulo'],
            "size": "Large",
            "weight": "Bolder",
            "color": cor_titulo,
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": alerta['resumo'],
            "size": "Medium",
            "wrap": True,
            "spacing": "Small",
        },
        {
            "type": "TextBlock",
            "text": f"🕐 {datetime.now():%d/%m/%Y · %H:%M}",
            "size": "Small",
            "color": "Light",
            "spacing": "Small",
        },
    ]

    # Adiciona tabela se tiver dados
    if df is not None and len(df) > 0:
        linhas = []
        for _, r in df.head(5).iterrows():
            tid = r.get('id', '—')
            titulo = str(r.get('titulo', r.get('solicitante', '—')))[:50]
            resp = r.get('responsavel_atual', r.get('solicitante', '—'))

            extra = ''
            if 'dias_aberto' in r:
                extra = f"{r['dias_aberto']}d"
            elif 'previsao' in r:
                extra = str(r['previsao'])[:16]
            elif 'total' in r and 'solicitante' in r:
                extra = f"{r['total']} tickets"

            linhas.append({
                "type": "TableRow",
                "cells": [
                    {"type": "TableCell", "items": [
                        {"type": "TextBlock", "text": str(tid), "size": "Small"}
                    ]},
                    {"type": "TableCell", "items": [
                        {"type": "TextBlock", "text": titulo, "size": "Small", "wrap": True}
                    ]},
                    {"type": "TableCell", "items": [
                        {"type": "TextBlock", "text": str(resp)[:25], "size": "Small"}
                    ]},
                    {"type": "TableCell", "items": [
                        {"type": "TextBlock", "text": extra, "size": "Small"}
                    ]},
                ]
            })

        body.append({"type": "TextBlock", "text": " ", "spacing": "Small"})
        body.append({
            "type": "Table",
            "columns": [{"width": 1}, {"width": 4}, {"width": 2}, {"width": 1}],
            "rows": linhas,
        })

        if len(df) > 5:
            body.append({
                "type": "TextBlock",
                "text": f"... e mais {len(df) - 5} tickets",
                "size": "Small",
                "color": "Light",
                "spacing": "Small",
            })

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body,
                },
            }
        ],
    }


# ==================== ENVIO ====================
def enviar_teams(webhook_url, alerta, dry_run=True):
    """Envia alerta para o Teams."""
    payload = montar_card(alerta)

    if dry_run:
        log(f'📢 [DRY-RUN] Enviaria para Teams: {alerta["titulo"]}')
        return True

    if not webhook_url:
        log('❌ Webhook não configurado', 'ERRO')
        return False

    try:
        r = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=15,
        )
        if r.status_code in (200, 202):
            log(f'✅ Alerta enviado: {alerta["titulo"]}')
            return True
        else:
            log(f'❌ HTTP {r.status_code}: {r.text[:200]}', 'ERRO')
            return False
    except Exception as e:
        log(f'❌ Erro ao enviar: {e}', 'ERRO')
        return False


# ==================== MAIN ====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--enviar', action='store_true',
                        help='Envia para o Teams (sem isso, só simula)')
    parser.add_argument('--regra', type=str,
                        help='Executa só uma regra (A1..A5)')
    args = parser.parse_args()

    print('=' * 60)
    print('ALERTAS HELP360 → TEAMS')
    print('=' * 60)
    print(f'📁 Banco: {BANCO}')
    print(f'📢 Modo: {"ENVIO REAL" if args.enviar else "DRY-RUN"}')

    webhook = carregar_webhook()
    if webhook:
        print(f'🔗 Webhook: {webhook[:70]}...')
    else:
        print('⚠️  Webhook NÃO configurado')
    print()

    if not BANCO.exists():
        log('❌ Banco não encontrado', 'ERRO')
        return 1

    conn = conectar()

    regras_executar = (
        [args.regra.upper()] if args.regra else list(REGRAS.keys())
    )

    total = 0

    for codigo in regras_executar:
        if codigo not in REGRAS:
            log(f'⚠️ Regra {codigo} não existe', 'AVISO')
            continue

        nome, func = REGRAS[codigo]
        log(f'▶️  Rodando {codigo} — {nome}')

        try:
            alerta = func(conn)
            if alerta is None:
                log(f'   Sem ocorrências')
                continue

            total += 1
            log(f'   {alerta["qtd"]} ocorrência(s)')

            enviar_teams(webhook, alerta, dry_run=not args.enviar)
        except Exception as e:
            log(f'   ❌ Erro: {e}', 'ERRO')

    conn.close()

    print()
    print('=' * 60)
    print(f'✅ {total} alerta(s) processado(s)')
    print('=' * 60)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())