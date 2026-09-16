# ============================================================
# explorar_ticket.py
# ============================================================
"""
Script exploratório: abre um ticket no Help360 e extrai
tudo que encontra (texto, links, seções, possíveis mensagens).

⚠️  IMPORTANTE: Tudo que é salvo em disco passa por anonimização
     (CPF, email, telefone e nomes conhecidos) para conformidade com
     a LGPD.

Uso:
    python scripts/explorar_ticket.py --id 111005
    python scripts/explorar_ticket.py --id 111005 --salvar-html
    python scripts/explorar_ticket.py --id 111005 --nomes "João Silva,Maria Souza"
    python scripts/explorar_ticket.py --id 111005 --sem-anonimizar
"""

import argparse
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Adiciona src/ ao path
_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ / 'src'))

from selenium.webdriver.common.by import By

from utils_help360 import criar_navegador, realizar_login


# ==================== CONFIGURAÇÃO ====================
PASTA_SAIDA = _RAIZ / 'dados' / 'exploracao'
BANCO = _RAIZ / 'dados' / 'tickets.db'
URL_TICKET = 'https://spprev.help360.com.br/tickets/{id}'


# ============================================================
# ANONIMIZAÇÃO
# ============================================================
class Anonimizador:
    """
    Responsável por anonimizar texto antes de salvar em disco.

    Regras:
      - CPF           → <CPF>
      - Email         → <EMAIL>
      - Telefone      → <TELEFONE>
      - Nomes         → <NOME_1>, <NOME_2>, ...
      - IDs longos    → <ID>
    """

    def __init__(self, nomes_extras=None, usar_banco=True):
        self.nomes_conhecidos = {}  # nome → placeholder
        self._proximo_id = 1

        # 1. Carrega nomes do banco (analistas + solicitantes)
        if usar_banco and BANCO.exists():
            self._carregar_nomes_do_banco()

        # 2. Adiciona nomes extras (via CLI)
        if nomes_extras:
            for nome in nomes_extras:
                self._registrar_nome(nome.strip())

        # 3. Adiciona nomes "comuns" que sempre aparecem
        for nome in ['Administrador', 'Suporte', 'Sistema', 'Atendimento']:
            self._registrar_nome(nome)

    # ---------- REGISTRO ----------
    def _registrar_nome(self, nome):
        """Registra um nome para ser anonimizado."""
        if not nome or len(nome) < 4:
            return
        if nome in self.nomes_conhecidos:
            return
        placeholder = f'<NOME_{self._proximo_id}>'
        self.nomes_conhecidos[nome] = placeholder
        self._proximo_id += 1

    def _carregar_nomes_do_banco(self):
        """Carrega nomes únicos do banco (analistas + solicitantes)."""
        try:
            conn = sqlite3.connect(BANCO)

            # Analistas
            try:
                rows = conn.execute(
                    'SELECT DISTINCT responsavel_atual FROM tickets '
                    'WHERE responsavel_atual IS NOT NULL'
                ).fetchall()
                for (nome,) in rows:
                    self._registrar_nome(nome)
            except Exception:
                pass

            # Solicitantes
            try:
                rows = conn.execute(
                    'SELECT DISTINCT solicitante FROM tickets '
                    'WHERE solicitante IS NOT NULL'
                ).fetchall()
                for (nome,) in rows:
                    self._registrar_nome(nome)
            except Exception:
                pass

            # Analistas cadastrados
            try:
                rows = conn.execute('SELECT nome FROM analistas').fetchall()
                for (nome,) in rows:
                    self._registrar_nome(nome)
            except Exception:
                pass

            conn.close()
        except Exception as e:
            print(f'   ⚠️ Erro ao carregar nomes do banco: {e}')

    # ---------- APLICAÇÃO ----------
    def anonimizar(self, texto):
        """Aplica todas as regras de anonimização."""
        if not texto or not isinstance(texto, str):
            return texto

        # 1. CPF
        padrao_cpf = r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'
        texto = re.sub(padrao_cpf, '<CPF>', texto)

        # 2. Email
        padrao_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        texto = re.sub(padrao_email, '<EMAIL>', texto)

        # 3. Telefone
        padrao_tel = r'\b(?:\(?\d{2}\)?\s?)?(?:9?\d{4})-?\d{4}\b'
        texto = re.sub(padrao_tel, '<TELEFONE>', texto)

        # 4. Nomes conhecidos (ordem: mais longos primeiro para não quebrar)
        for nome in sorted(self.nomes_conhecidos.keys(),
                           key=len, reverse=True):
            placeholder = self.nomes_conhecidos[nome]
            # Regex para nome completo (case-insensitive, com limite de palavra)
            padrao = r'(?<!\w)' + re.escape(nome) + r'(?!\w)'
            texto = re.sub(padrao, placeholder, texto, flags=re.IGNORECASE)

        # 5. Matrículas (7 dígitos seguidos, comuns no serviço público)
        padrao_matricula = r'\b\d{7}\b'
        texto = re.sub(padrao_matricula, '<MATRICULA>', texto)

        return texto

    def relatorio(self):
        """Retorna um resumo dos nomes registrados."""
        return {
            'total_nomes': len(self.nomes_conhecidos),
            'nomes': list(self.nomes_conhecidos.keys()),
        }


# ============================================================
# HELPERS
# ============================================================
def separador(titulo=''):
    print()
    print('=' * 70)
    if titulo:
        print(f'  {titulo}')
        print('=' * 70)


def subseparador(titulo):
    print(f'\n▸ {titulo}')


def salvar_arquivo(nome, conteudo):
    """Salva um arquivo em PASTA_SAIDA (o conteúdo já deve vir anonimizado)."""
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_SAIDA / nome
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    return caminho


def truncar(texto, limite=200):
    """Trunca um texto para exibição."""
    if not texto:
        return ''
    texto = texto.strip()
    return texto if len(texto) <= limite else texto[:limite] + '...'


# ============================================================
# EXPLORAÇÃO
# ============================================================
def explorar_ticket(ticket_id: str,
                    salvar_html: bool = False,
                    nomes_extras=None,
                    sem_anonimizar: bool = False):
    """Abre um ticket e extrai tudo que encontra."""

    separador(f'EXPLORANDO TICKET #{ticket_id}')

    # ==================== ANONIMIZADOR ====================
    if sem_anonimizar:
        print('⚠️  MODO SEM ANONIMIZAÇÃO — os arquivos conterão dados brutos!')
        print('   Use apenas em ambiente controlado.\n')
        anon = None
    else:
        print('🔒 Carregando anonimizador...')
        anon = Anonimizador(nomes_extras=nomes_extras, usar_banco=True)
        rel = anon.relatorio()
        print(f'   ✅ {rel["total_nomes"]} nomes registrados para anonimização')

    def anonimizar(texto):
        """Wrapper local: aplica anon se existir, senão retorna como está."""
        if anon is None:
            return texto
        return anon.anonimizar(texto)

    # 1. Inicia navegador + login
    print('\n🌐 Abrindo navegador...')
    navegador = criar_navegador()
    realizar_login(navegador)

    # 2. Navega até o ticket
    url = URL_TICKET.format(id=ticket_id)
    print(f'📄 Acessando: {url}')
    navegador.get(url)

    # Aguarda a página carregar
    print('⏳ Aguardando carregamento...')
    time.sleep(5)

    # 3. Info básica
    separador('INFORMAÇÕES DA PÁGINA')
    print(f'  Título da aba : {anonimizar(navegador.title)}')
    print(f'  URL atual     : {navegador.current_url}')
    print(f'  Tamanho HTML  : {len(navegador.page_source):,} caracteres')

    # 4. Salva HTML completo (anonimizado)
    if salvar_html:
        html_anonimizado = anonimizar(navegador.page_source)
        html_path = salvar_arquivo(f'ticket_{ticket_id}.html', html_anonimizado)
        print(f'  HTML salvo em : {html_path}')
        if anon:
            print(f'                  🔒 (anonimizado)')

    # 5. Salva texto visível (anonimizado)
    try:
        body_text = navegador.find_element(By.TAG_NAME, 'body').text
    except Exception:
        body_text = ''

    body_text_anon = anonimizar(body_text)
    texto_path = salvar_arquivo(f'ticket_{ticket_id}.txt', body_text_anon)
    print(f'  Texto salvo em: {texto_path}')
    print(f'  Texto total   : {len(body_text):,} caracteres')
    if anon:
        print(f'                  🔒 (anonimizado)')

    # 6. Procura por seções conhecidas
    separador('BUSCA POR SEÇÕES CONHECIDAS')

    candidatos = {
        'Descrição'   : ['descrição', 'descricao', 'description'],
        'Mensagens'   : ['mensagem', 'mensagens', 'histórico', 'historico'],
        'Acompanha.'  : ['acompanhamento', 'andamento', 'movimentação'],
        'Timeline'    : ['timeline', 'linha do tempo', 'fluxo'],
        'Anexos'      : ['anexo', 'anexos', 'arquivos'],
        'Comentários' : ['comentário', 'comentario', 'comentários'],
    }

    for tipo, palavras in candidatos.items():
        subseparador(f'Procurando "{tipo}"')
        encontrado = False

        for palavra in palavras:
            xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÇÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÝ', 'abcdefghijklmnopqrstuvwxyzaaaaaaceeeeiiiiooooouuuuy'), '{palavra}')]"
            try:
                elementos = navegador.find_elements(By.XPATH, xpath)
                titulos = [el for el in elementos
                           if el.text and len(el.text.strip()) < 100]
                if titulos:
                    encontrado = True
                    for el in titulos[:3]:
                        texto = anonimizar(el.text.strip())
                        tag = el.tag_name
                        classes = el.get_attribute('class') or ''
                        print(f'   [{tag}] "{truncar(texto, 60)}"')
                        print(f'         id="{el.get_attribute("id")}" class="{truncar(classes, 60)}"')
                    break
            except Exception as e:
                print(f'   ⚠️ Erro buscando "{palavra}": {e}')

        if not encontrado:
            print(f'   ❌ Nada encontrado')

    # 7. Lista todos os elementos com ID
    separador('ELEMENTOS COM ID (candidatos a seletor)')
    try:
        com_id = navegador.find_elements(By.XPATH, '//*[@id]')
        ids_unicos = {}
        for el in com_id:
            el_id = el.get_attribute('id')
            if el_id and el_id not in ids_unicos:
                texto = truncar(anonimizar(el.text), 40)
                ids_unicos[el_id] = (el.tag_name, texto)

        print(f'  Total com ID: {len(ids_unicos)}\n')
        for el_id, (tag, texto) in list(ids_unicos.items())[:40]:
            print(f'   #{el_id:<35} <{tag}> "{texto}"')
    except Exception as e:
        print(f'  ⚠️ Erro: {e}')

    # 8. Procura por padrões de data
    separador('PROCURA POR PADRÕES DE DATA/MENSAGEM')

    padroes = {
        'DD/MM/AAAA'       : r'\d{2}/\d{2}/\d{4}',
        'DD/MM/AAAA HH:MM' : r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}',
        'DD/MM/AA HH:MM'   : r'\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}',
    }

    for nome, padrao in padroes.items():
        matches = re.findall(padrao, body_text)
        if matches:
            print(f'  ▸ Padrão "{nome}": {len(matches)} ocorrências')
            unicos = list(dict.fromkeys(matches))[:5]
            for m in unicos:
                print(f'      "{m}"')

    # 9. Divs principais
    separador('DIVS PRINCIPAIS (candidatas a container)')
    try:
        divs = navegador.find_elements(
            By.XPATH,
            '//div[contains(@class, "ticket") or contains(@class, "message") '
            'or contains(@class, "history") or contains(@class, "timeline") '
            'or contains(@class, "note")]'
        )
        print(f'  Total: {len(divs)}\n')
        for div in divs[:15]:
            classes = div.get_attribute('class') or ''
            texto = truncar(anonimizar(div.text), 80)
            print(f'   <div class="{truncar(classes, 60)}">')
            print(f'     "{texto}"')
    except Exception as e:
        print(f'  ⚠️ Erro: {e}')

    # 10. Salva HTML estruturado (anonimizado)
    separador('SALVANDO HTML FORMATADO')

    try:
        main = navegador.find_element(By.TAG_NAME, 'main')
    except Exception:
        main = navegador.find_element(By.TAG_NAME, 'body')

    html_estruturado = anonimizar(main.get_attribute('outerHTML'))
    caminho = salvar_arquivo(f'ticket_{ticket_id}_main.html', html_estruturado)
    print(f'  ✅ Conteúdo principal salvo em: {caminho}')
    print(f'     Tamanho: {len(html_estruturado):,} caracteres')
    if anon:
        print(f'     🔒 (anonimizado)')

    # Final
    separador('EXPLORAÇÃO CONCLUÍDA')
    print(f'\n📂 Arquivos salvos em: {PASTA_SAIDA}')

    if anon:
        rel = anon.relatorio()
        print(f'\n🔒 ANONIMIZAÇÃO: {rel["total_nomes"]} nomes registrados')
        print('   Todos os dados pessoais foram substituídos por placeholders.')

    print()
    print('💡 Próximos passos:')
    print('   1. Abra o arquivo .txt e .html para ver o que foi capturado')
    print('   2. Copie as partes mais relevantes (descrição, mensagens)')
    print('   3. Me mande um trecho para eu escrever o parser específico')

    input('\n⏸️  Pressione ENTER para fechar o navegador...')
    navegador.quit()


# ==================== MAIN ====================
def main():
    parser = argparse.ArgumentParser(description='Explora um ticket no Help360.')
    parser.add_argument('--id', required=True, help='ID do ticket (ex: 111005)')
    parser.add_argument('--salvar-html', action='store_true',
                        help='Salva também o HTML completo')
    parser.add_argument('--nomes', type=str, default=None,
                        help='Nomes adicionais a anonimizar (separados por vírgula)')
    parser.add_argument('--sem-anonimizar', action='store_true',
                        help='⚠️ Desativa anonimização (use apenas em ambiente controlado)')
    args = parser.parse_args()

    nomes_extras = None
    if args.nomes:
        nomes_extras = [n.strip() for n in args.nomes.split(',') if n.strip()]

    try:
        explorar_ticket(
            args.id,
            salvar_html=args.salvar_html,
            nomes_extras=nomes_extras,
            sem_anonimizar=args.sem_anonimizar,
        )
    except KeyboardInterrupt:
        print('\n\n⚠️ Interrompido pelo usuário.')
    except Exception as e:
        print(f'\n❌ Erro: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()