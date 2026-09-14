# 08 — Instalação e Configuração

**Documento:** Guia de Instalação e Configuração
**Versão:** 2.0
**Público-alvo:** Operadores, Desenvolvedores, DevOps

---

## 1. Pré-requisitos

### 1.1 Sistema Operacional

| Item | Versão mínima |
|---|---|
| Windows | 10 ou 11 |
| Arquitetura | 64 bits |
| RAM | 8 GB (recomendado) |
| Disco | 500 MB livres |

### 1.2 Software

| Software | Versão | Como verificar |
|---|---|---|
| Python | 3.10+ | `python --version` |
| Google Chrome | Atualizado | Menu → Sobre |
| Git | 2.30+ | `git --version` |

### 1.3 Acesso

- Conta @sp.gov.br ativa
- Acesso ao Help360 (`spprev.help360.com.br`)
- Permissão de leitura na pasta `~/Downloads`

---

## 2. Instalação

### 2.1 Clonar o repositório

```powershell
cd C:\Users\seu_usuario\Documents
git clone https://github.com/gustav0barbosa-dev/automacao-tickets.git
cd automacao-tickets
2.2 Instalar dependências
As dependências estão em requirements.txt:

powershell
pip install -r requirements.txt
Pacotes instalados:

Pacote	Uso
pandas	Manipulação de dados
openpyxl	Leitura/escrita de Excel
selenium	Automação web
webdriver-manager	Gerencia o ChromeDriver
2.3 Verificar instalação
powershell
python -c "import pandas; print('pandas', pandas.__version__)"
python -c "import openpyxl; print('openpyxl', openpyxl.__version__)"
python -c "import selenium; print('selenium', selenium.__version__)"
Deve imprimir a versão de cada pacote sem erro.

3. Configuração
3.1 Arquivo config/settings.yaml
yaml
urls:
  base: "https://spprev.help360.com.br"
  login: "https://spprev.help360.com.br/users/sign_in"
  ticket: "https://spprev.help360.com.br/tickets/{id}"

credenciais:
  usuario: "seu.email@sp.gov.br"

filtros:
  dias_antecipar_default: 1
  dias_postergar:
    sexta: 4
    outros: 2
  data_minima_previsao_dias: 365

navegador:
  headless: false
  timeout_segundos: 30
  delay_entre_abas: 1.5
⚠️ Nunca coloque a senha no arquivo. Ela é solicitada em tempo real via getpass.

3.2 Arquivo config/categorias_fora.txt
Lista de categorias ignoradas, uma por linha:

text
1ª Etapa Censo
Alteração de Grupo de Pagamento
Alterações Bancárias
...
3.3 Variáveis de ambiente (opcional)
Para rodar em modo agendado (sem interação):

powershell
$env:HELP360_USUARIO = "seu.email@sp.gov.br"
$env:HELP360_SENHA   = "sua_senha"
⚠️ Cuidado: variáveis ficam visíveis na sessão. Prefira getpass.

4. Estrutura de Pastas
text
automacao-tickets/
├── main.py                    # Orquestrador
├── requirements.txt           # Dependências
├── README.md
│
├── src/                       # Código-fonte
│   ├── programa0_preprocessar.py
│   ├── programa1_download.py
│   ├── programa2_filtrar.py
│   ├── programa3_abrir.py
│   └── utils_help360.py
│
├── config/                    # Configurações
│   ├── settings.yaml
│   └── categorias_fora.txt
│
├── dados/                     # Dados (runtime)
│   ├── tickets.db
│   ├── logs/
│   └── snapshots/
│
├── relatorios/                # Relatórios gerados
├── docs/                      # Documentação
├── scripts/                   # Utilitários
└── tests/                     # Testes
5. Primeira Execução
5.1 Rodar o pipeline
powershell
cd C:\Users\seu_usuario\Documents\automacao-tickets
python main.py
O que esperar:

Verifica se utils_help360.py existe

Detecta se a Tabela fato está presente

Pergunta se quer processá-la (s/n)

Executa Programa1, 2 e 3

Pede senha (via getpass)

Abre o Chrome com os tickets

5.2 Verificar arquivos gerados
Depois da primeira execução, devem existir em ~/Downloads/:

tickets.xlsx

tickets_com_respondido.xlsx

acompanhamento.xlsx

6. Configuração do Chrome
O webdriver-manager baixa automaticamente o ChromeDriver compatível.

6.1 Verificar se o Chrome está atualizado
Abra o Chrome → Menu (⋮) → Ajuda → Sobre o Google Chrome.

Se estiver desatualizado, atualize antes de rodar o pipeline.

6.2 Modo headless
Para rodar sem abrir a janela do Chrome, edite settings.yaml:

yaml
navegador:
  headless: true
⚠️ Não recomendado na primeira execução — você precisa ver o que está acontecendo.

7. Agendamento (Windows)
7.1 Criar tarefa agendada
Abra Agendador de Tarefas

Criar Tarefa Básica

Nome: Automação Help360

Disparador: Diariamente às 08:00

Ação: Iniciar um programa

Programa: C:\caminho\para\python.exe

Argumentos: C:\caminho\para\automacao-tickets\main.py

Iniciar em: C:\caminho\para\automacao-tickets

7.2 ⚠️ Senha em modo agendado
O getpass não funciona em tarefas agendadas (não há terminal). Use variáveis de ambiente:

yaml
credenciais:
  usuario: "seu.email@sp.gov.br"
  senha_env: "HELP360_SENHA"    # nome da variável de ambiente
8. Atualização
8.1 Atualizar o código
powershell
cd C:\...\automacao-tickets
git pull
8.2 Atualizar dependências
powershell
pip install -r requirements.txt --upgrade
8.3 ⚠️ Antes de atualizar
Faça backup do dados/tickets.db

Verifique o CHANGELOG.md para mudanças que quebram compatibilidade

9. Desinstalação
powershell
# Remover pasta do projeto
Remove-Item -Recurse -Force C:\...\automacao-tickets

# (Opcional) Remover cache de pacotes
pip cache purge
10. Solução de Problemas de Instalação
Erro	Causa	Solução
python não reconhecido	Python não está no PATH	Reinstalar marcando "Add to PATH"
pip não reconhecido	Idem	Usar python -m pip
ModuleNotFoundError	Dependência não instalada	pip install -r requirements.txt
ChromeDriver desatualizado	Chrome atualizou	pip install --upgrade webdriver-manager
Timeout ao baixar	Rede lenta	Aumentar timeout em settings.yaml
11. Checklist de Instalação
□ Python 3.10+ instalado
□ Git instalado
□ Chrome atualizado
□ Repositório clonado
□ pip install -r requirements.txt executado com sucesso
□ config/settings.yaml configurado com seu usuário
□ Primeira execução do main.py bem-sucedida
□ Arquivos gerados em ~/Downloads/
12. Referências
01_Visao_e_Escopo.md

09_Operacao_e_Manutencao.md

Python Downloads

Git for Windows
"""