"""
Autenticação simples para o dashboard.
Usa bcrypt + secrets do Streamlit.
"""
import os
import json
import bcrypt
import streamlit as st


def _obter_usuarios() -> dict:
    """Lê usuários dos secrets OU de variável de ambiente."""
    # 1. Tenta secrets
    try:
        usuarios = dict(st.secrets.get('usuarios', {}))
        if usuarios:
            return usuarios
    except Exception:
        pass

    # 2. Tenta variável de ambiente
    usuarios_json = os.environ.get('DASHBOARD_USERS')
    if usuarios_json:
        try:
            return json.loads(usuarios_json)
        except Exception:
            pass

    return {}


def verificar_login(usuario: str, senha: str) -> bool:
    """
    Verifica usuário/senha contra os hashes armazenados.
    Retorna True se autenticado, False caso contrário.
    """
    usuarios = _obter_usuarios()
    if not usuarios:
        st.error('⚠️ Nenhum usuário configurado em secrets.toml.')
        return False

    usuario = usuario.strip().lower()

    if usuario not in usuarios:
        return False

    hash_armazenado = usuarios[usuario]
    try:
        return bcrypt.checkpw(
            senha.encode('utf-8'),
            hash_armazenado.encode('utf-8'),
        )
    except Exception:
        return False


def tela_login():
    """
    Renderiza a tela de login.
    Retorna True se o usuário está autenticado.
    """
    # Se já está logado na sessão, retorna True
    if st.session_state.get('autenticado'):
        return True

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
            usuario = st.text_input('Usuário', key='login_user')
            senha = st.text_input('Senha', type='password', key='login_pass')
            submit = st.form_submit_button('Entrar', use_container_width=True)

            if submit:
                if not usuario or not senha:
                    st.error('Preencha usuário e senha.')
                elif verificar_login(usuario, senha):
                    st.session_state['autenticado'] = True
                    st.session_state['usuario'] = usuario.strip().lower()
                    st.rerun()
                else:
                    st.error('❌ Usuário ou senha inválidos.')
                    # Delay para dificultar brute force
                    import time
                    time.sleep(1)

    return False


def logout():
    """Faz logout do usuário."""
    st.session_state['autenticado'] = False
    st.session_state['usuario'] = None
    st.rerun()


def usuario_atual() -> str:
    """Retorna o nome do usuário logado."""
    return st.session_state.get('usuario', 'desconhecido')