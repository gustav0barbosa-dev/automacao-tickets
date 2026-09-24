"""
Gera hash bcrypt para senhas de usuários do dashboard.
Uso: python scripts/gerar_hash_senha.py
"""
import bcrypt
import getpass


def main():
    print('=' * 60)
    print('GERADOR DE HASH DE SENHA (bcrypt)')
    print('=' * 60)
    print()

    usuario = input('Usuário (ex: gustavo): ').strip()
    senha = getpass.getpass('Senha: ')
    senha_confirm = getpass.getpass('Confirma a senha: ')

    if senha != senha_confirm:
        print('❌ As senhas não batem!')
        return

    if len(senha) < 8:
        print('❌ A senha precisa ter pelo menos 8 caracteres!')
        return

    hash_bytes = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
    hash_str = hash_bytes.decode('utf-8')

    print()
    print('=' * 60)
    print('HASH GERADO — cole no .streamlit/secrets.toml')
    print('=' * 60)
    print()
    print(f'{usuario} = "{hash_str}"')
    print()
    print('=' * 60)


if __name__ == '__main__':
    main()