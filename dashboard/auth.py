# ============================================================
# dashboard/auth.py — Autenticação via Neon Auth (Better Auth)
# ============================================================
"""
Autenticação do dashboard usando a Neon Auth (Better Auth) via HTTP.

Fluxo:
    1. POST {NEON_AUTH_URL}/sign-in/email
       corpo: {"email": "...", "password": "..."}
    2. Em caso de 200 OK, extrai o cookie de sessão da resposta
       (normalmente `better-auth.session_token`).
    3. GET {NEON_AUTH_URL}/get-session enviando esse cookie.
    4. O JWT só é exposto no cabeçalho `Set-Auth-Jwt` dessa segunda
       resposta; ele é salvo em st.session_state["jwt_token"] e usado
       pela Neon Data API em dashboard/data.py.

As permissões de dados NÃO são definidas aqui: a Data API apenas repassa
o JWT ao PostgreSQL, que aplica RLS e GRANTs. Veja o comentário de RLS
no topo de dashboard/data.py.
"""

import os
from pathlib import Path

import requests
import streamlit as st

_TIMEOUT_LOGIN = 20


def _carregar_env_local() -> None:
    """
    Carrega variáveis de um arquivo .env na raiz do projeto, sem depender
    de python-dotenv. Variáveis já presentes no ambiente têm prioridade.
    """
    caminho = Path(__file__).resolve().parent.parent / '.env'
    if not caminho.exists():
        return

    try:
        for linha in caminho.read_text(encoding='utf-8-sig').splitlines():
            linha = linha.strip()
            if not linha or linha.startswith('#') or '=' not in linha:
                continue

            if linha.startswith('export '):
                linha = linha[len('export '):].strip()

            chave, _, valor = linha.partition('=')
            chave = chave.strip()
            valor = valor.strip().strip('"').strip("'")

            if chave and chave not in os.environ:
                os.environ[chave] = valor
    except OSError:
        # O .env é opcional; se não puder ser lido, seguimos com o ambiente.
        pass


_carregar_env_local()


def obter_config(nome: str) -> str | None:
    """
    Obtém uma configuração do ambiente ou dos secrets do Streamlit.

    Ordem de prioridade:
        1. Variável de ambiente (inclui o .env carregado acima)
        2. st.secrets (Streamlit Cloud / secrets.toml)
    """
    valor = os.environ.get(nome)
    if valor and valor.strip():
        return valor.strip()

    try:
        valor = st.secrets.get(nome)
    except Exception:
        valor = None

    if valor and str(valor).strip():
        return str(valor).strip()

    return None


def _auth_url() -> str | None:
    """Retorna a URL base da Neon Auth, sem barra final."""
    url = obter_config('NEON_AUTH_URL')
    return url.rstrip('/') if url else None


def _extrair_cookies_sessao(resposta: requests.Response) -> dict[str, str]:
    """
    Extrai os cookies de sessão do Better Auth da resposta de login.

    O nome pode variar conforme o ambiente (`better-auth.session_token`,
    `__Secure-better-auth.session_token`, cookies fatiados como
    `better-auth.session_token.0`, além do `better-auth.session_data`).
    Se nenhum cookie relacionado a sessão for encontrado, envia todos os
    cookies recebidos como fallback.
    """
    try:
        cookies = resposta.cookies.get_dict()
    except Exception:
        return {}

    if not cookies:
        return {}

    cookies_sessao = {
        nome: valor
        for nome, valor in cookies.items()
        if 'session' in nome.lower()
    }
    return cookies_sessao or cookies


def fazer_login(email: str, senha: str) -> bool:
    """
    Autentica o usuário na Neon Auth e guarda o JWT na sessão.

    Retorna True em caso de sucesso. Em caso de falha, exibe uma mensagem
    amigável com st.error e retorna False.
    """
    email = (email or '').strip().lower()

    if not email or not senha:
        st.error('Preencha e-mail e senha.')
        return False

    auth_url = _auth_url()
    if not auth_url:
        st.error(
            '⚠️ NEON_AUTH_URL não configurada. '
            'Defina a variável no .env ou nos secrets do Streamlit.'
        )
        return False

    url = f'{auth_url}/sign-in/email'

    try:
        resposta = requests.post(
            url,
            json={'email': email, 'password': senha},
            timeout=_TIMEOUT_LOGIN,
        )
    except requests.exceptions.Timeout:
        st.error('⏱️ Tempo esgotado ao contatar o serviço de autenticação.')
        return False
    except requests.exceptions.RequestException as exc:
        st.error(f'🌐 Falha de rede ao autenticar: {exc}')
        return False

    if resposta.status_code in (400, 401, 403):
        st.error('❌ E-mail ou senha inválidos.')
        return False

    if resposta.status_code != 200:
        st.error(
            f'❌ Serviço de autenticação retornou HTTP {resposta.status_code}.'
        )
        return False

    # ---------- ETAPA 2: extrair o cookie de sessão ----------
    cookies_sessao = _extrair_cookies_sessao(resposta)
    if not cookies_sessao:
        st.error(
            '⚠️ Login aceito, mas a sessão não foi criada '
            '(cookie `better-auth.session_token` ausente). '
            'Verifique a configuração de cookies da Neon Auth.'
        )
        return False

    # ---------- ETAPA 3: buscar o JWT em /get-session ----------
    # A Neon Auth não envia o JWT no login direto: ele só aparece no
    # cabeçalho Set-Auth-Jwt da resposta de /get-session.
    try:
        resposta_sessao = requests.get(
            f'{auth_url}/get-session',
            cookies=cookies_sessao,
            headers={'Accept': 'application/json'},
            timeout=_TIMEOUT_LOGIN,
        )
    except requests.exceptions.Timeout:
        st.error('⏱️ Tempo esgotado ao validar a sessão.')
        return False
    except requests.exceptions.RequestException as exc:
        st.error(f'🌐 Falha de rede ao validar a sessão: {exc}')
        return False

    if resposta_sessao.status_code in (401, 403):
        st.error(
            '🔒 Sessão não reconhecida pela Neon Auth. Faça login novamente.'
        )
        return False

    if resposta_sessao.status_code != 200:
        st.error(
            '❌ Não foi possível validar a sessão '
            f'(HTTP {resposta_sessao.status_code}).'
        )
        return False

    # requests.Headers é case-insensitive, então "Set-Auth-Jwt" funciona
    # independentemente da capitalização enviada pelo servidor.
    jwt = resposta_sessao.headers.get('Set-Auth-Jwt')
    if not jwt:
        st.error(
            '⚠️ Sessão válida, mas o servidor não retornou o token JWT '
            '(cabeçalho Set-Auth-Jwt). Verifique se o plugin JWT está '
            'habilitado na Neon Auth.'
        )
        return False

    st.session_state['jwt_token'] = jwt
    st.session_state['autenticado'] = True
    st.session_state['usuario'] = email
    return True


def tela_login():
    """
    Renderiza a tela de login.
    Retorna True se o usuário está autenticado.
    """
    # Sessão válida exige autenticação E token. Sessões antigas (criadas
    # antes da migração, sem JWT) precisam fazer login novamente.
    if st.session_state.get('autenticado') and st.session_state.get('jwt_token'):
        return True

    st.session_state.pop('autenticado', None)
    st.session_state.pop('jwt_token', None)
    st.session_state.pop('usuario', None)

    # Centraliza o formulário
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            '<h1 style="text-align:center; color:#c9a666;">🔒 HELP360</h1>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p style="text-align:center; color:#9299a6;">'
            'Dashboard de Análise — Acesso Restrito</p>',
            unsafe_allow_html=True,
        )
        st.markdown('')

        with st.form('login_form'):
            email = st.text_input('E-mail', key='login_user')
            senha = st.text_input('Senha', type='password', key='login_pass')
            submit = st.form_submit_button('Entrar', use_container_width=True)

            if submit:
                if fazer_login(email, senha):
                    st.rerun()
                else:
                    # Delay para dificultar brute force
                    import time
                    time.sleep(1)

    return False


def logout() -> None:
    """Encerra a sessão, descartando o JWT e os dados do usuário."""
    st.session_state.clear()
    st.rerun()


def usuario_atual() -> str:
    """Retorna o e-mail do usuário logado."""
    return st.session_state.get('usuario', 'desconhecido')
