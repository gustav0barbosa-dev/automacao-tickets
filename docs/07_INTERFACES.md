# 07 — Interfaces

**Documento:** Contratos de Interfaces e Integrações
**Versão:** 3.0
**Última atualização:** Setembro/2026
**Público-alvo:** Desenvolvedores, Integradores

---

## 1. Introdução

Este documento descreve **todas as interfaces** do sistema:

- **Arquivos** (entrada/saída entre programas)
- **URLs** (integração com Help360)
- **Endpoints internos** (comunicação entre módulos)
- **Contratos de dados** (schemas, formatos)

---

## 2. Interfaces Externas

### 2.1 Site Help360

| Aspecto | Valor |
|---|---|
| **URL base** | `https://spprev.help360.com.br` |
| **Login** | `https://spprev.help360.com.br/users/sign_in` |
| **Ticket individual** | `https://spprev.help360.com.br/tickets/{id}` |
| **Exportar histórico** | `https://spprev.help360.com.br/export_ticket_histories/{id}.xlsx` |
| **Área de tickets** | Menu lateral → li[4] |
| **Botão de exportar** | `//*[@id="div_list_tickets"]/.../a/i` |
| **Protocolo** | HTTPS |
| **Autenticação** | Login + senha (@sp.gov.br) |

### 2.2 Endpoints Consumidos

| Método | URL | Uso |
|---|---|---|
| GET | `/users/sign_in` | Página de login |
| POST | `/users/sign_in` | Enviar credenciais |
| GET | `/tickets` | Lista de tickets |
| GET | `/tickets/{id}` | Ticket individual |
| GET | `/tickets/export` | Exportação em massa |
| GET | `/export_ticket_histories/{id}.xlsx` | Histórico do ticket |

**⚠️ Nota:** o Help360 **não expõe API REST pública**. Tudo é via Selenium (scraping) + requests com cookies.

### 2.3 Detecção de Backlog

A página HTML do ticket pode conter a mensagem:

```html
<span style="background-color:#1bab94;color:#fff;...">
    Este ticket se tornou um Backlog
</span>
Palavras-chave detectadas:

se tornou um backlog

se tornou backlog

em backlog

aguardando backlog

ticket backlog

3. Interfaces Internas — Arquivos
3.1 tickets.xlsx (base completa)
Gerado por: programa1_download.py
Consumido por: programa2_filtrar.py, programa4_persistir.py
Localização: ~/Downloads/tickets.xlsx

Schema:

Coluna	Tipo	Descrição
ID	int	ID do ticket
Status	string	Status atual
Criado Data	datetime	Data de criação
Alterado Data	datetime	Última movimentação
Previsão	datetime	SLA
Responsável	string	Analista atual
Categoria	string	Categoria
Subcategoria	string	Subcategoria
Título	string	Título
Prioridade	string	Prioridade
Solicitante	string	Quem abriu
Data do Resolvido	datetime	Resolução
Data do 1°resolvido	datetime	1º atendimento
3.2 tickets_com_respondido.xlsx
Gerado por: programa0_preprocessar.py
Consumido por: programa2_filtrar.py, marcar_respondidos.py
Localização: ~/Downloads/tickets_com_respondido.xlsx

Schema:

Coluna	Tipo	Descrição
ID	string	ID do ticket
Data Respondido	datetime ou NaT	Data da última resposta
3.3 acompanhamento.xlsx
Gerado por: programa2_filtrar.py
Consumido por: programa3_abrir.py
Localização: ~/Downloads/acompanhamento.xlsx

Schema: Mesmas colunas de tickets.xlsx, filtradas.

3.4 Tickets - Tabela fato.xlsx
Entrada manual (operador)
Consumido por: programa0_preprocessar.py
Localização: ~/Downloads/Tickets - Tabela fato.xlsx

Abas:

Aba Status
Coluna	Conteúdo
ID	ID do ticket
Demais	Histórico de mudanças de status
Aba Acompanhamento
Coluna	Conteúdo
ID	ID do ticket
Demais	Texto livre com data + observação
Valores possíveis:

0, -, #N/A, vazio

Texto com data ("04/09/2026 - 14:03: Enviado...")

Timestamp nativo

3.5 usuario_empresa.xlsx NOVO
Entrada manual (lista de analistas)
Consumido por: carregar_analistas.py
Localização: dados/usuario_empresa.xlsx

Schema:

Coluna	Tipo	Descrição
id	int	ID do usuário
Usuário	string	Nome completo
email	string	Email (@sp.gov.br ou @atlanticsolutions.com.br)
Empresa	string	Lista de empresas (multivalor)
total_empresa	int	Quantidade de empresas
Classificação resultante:

python
if '@atlanticsolutions.com.br' in email: return 'Atlantic'
if '@sp.gov.br' in email:                return 'SPPREV'
return 'Outro'
3.6 tickets.db (SQLite)
Gerado por: programa4_persistir.py
Consumido por: Todo o pipeline + dashboard
Localização: dados/tickets.db

Tabelas: ver 04_Modelo_Dados.md.

3.7 dados/migrations/*.sql NOVO
Aplicadas por: scripts/aplicar_migration.py

Arquivo	O que faz
001_add_colunas_extras.sql	Adiciona classificacao, area, empresa, solucao, sistema
002_sprint_features.sql	Adiciona backlog, respondido, diagnostico, acao_interna, pendente_usuario, responsavel_empresa + tabela analistas
003_add_classificacao.sql	Reforça classificacao
004_fix_analistas.sql	Corrige analistas.empresa_tipo
4. Interfaces entre Programas
4.1 Fluxo da Camada 1
text
┌─────────────────────┐
│ Tabela fato.xlsx    │
└──────────┬──────────┘
           │ (entrada manual)
           ▼
    ┌──────────────┐
    │ Programa 0   │ → tickets_com_respondido.xlsx
    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ Programa 2   │ → acompanhamento.xlsx
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
    ┌──────────────┐          ┌──────────────┐
    │ Programa 3   │          │ (via Camada 2)│
    │ (navegador)  │          └──────────────┘
    └──────────────┘

    Site Help360
        │
        │ (Selenium)
        ▼
    ┌──────────────┐
    │ Programa 1   │ → tickets.xlsx
    └──────────────┘
        │
        ▼
    (consumido pelo Programa 2)
4.2 Fluxo das Camadas 2 e 3
text
tickets.xlsx
    │
    ▼
┌──────────────┐
│ Programa 4   │ → SQLite (tickets)
└──────────────┘
    │
    ▼
┌──────────────┐
│ Programa 5   │ → SQLite (movimentacoes, mensagens, backlog)
└──────────────┘
    │
    ▼
┌────────────────────┐
│ carregar_analistas │ → SQLite (analistas)
└────────────────────┘
    │
    ▼
┌────────────────────┐
│ marcar_respondidos │ → SQLite (respondido)
└────────────────────┘
    │
    ▼
┌────────────────────────────┐
│ marcar_empresa_responsavel │ → SQLite (responsavel_empresa)
└────────────────────────────┘
    │
    ▼
┌────────────────────────┐
│ diagnosticar_tickets   │ → SQLite (diagnostico, acao_interna)
└────────────────────────┘
    │
    ▼
┌────────────────┐
│   Dashboard    │
└────────────────┘
4.3 Contratos de Chamada
De	Para	Método	Parâmetros	Retorno
main.py	programa0..5	subprocess.run	--dias N	exit code
programa2	utils	import	tratar_datas_excel(df)	df
programa2	utils	import	filtrar_categoria(df)	df
programa3	utils	import	criar_navegador()	navegador
dashboard/app.py	views/*.py	import	render(df)	—
dashboard/*	data.py	import	carregar_tickets()	df
dashboard/*	components.py	import	kpi(), hbar_list(), callout()	HTML
5. Contratos de Dados
5.1 Tipos Primitivos
Tipo	Representação	Exemplo
Data	datetime	2026-09-14 14:30:00
Texto	str	"Enviado para análise"
Inteiro	int	111005
Booleano	bool (convertido de INTEGER no SQLite)	True
Nulo	NaT (data) ou None	—
5.2 Formatos de Data
Contexto	Formato
Excel (importação)	DD/MM/AAAA ou DD/MM/AAAA HH:MM
Excel Help360	DD/MM/AAAA HH:MM (sem hífen)
SQLite	ISO: YYYY-MM-DD HH:MM:SS
Exibição	DD/MM/AAAA HH:MM
5.3 ID de Ticket
Formato: inteiro positivo

Exemplo: 111005

Representação em arquivo: string

Representação no banco: INTEGER

6. Interfaces de Saída
6.1 Dashboard
Recurso	Descrição
URL local	http://localhost:8501
Porta	8501
Stack	Streamlit + Plotly
Autenticação	Nenhuma (uso local)
Cache	@st.cache_data(ttl=300)
6.2 Páginas do Dashboard
Página	Conteúdo
Visão Geral	KPIs gerais
Tempo de Resposta	Distribuição
SLA	Cumprimento
Produtividade	Ranking por analista
Backlog	Aging, top antigos
Roteamento	Pulos, gargalos
Reincidência	Solicitantes recorrentes
Diagnóstico	Matriz de verdade
6.3 Relatórios
Tipo	Status
Excel	⏳ Roadmap
PDF	⏳ Roadmap
Email	⏳ Roadmap
7. Configuração
7.1 config/settings.yaml
yaml
urls:
  base: "https://spprev.help360.com.br"
  login: "https://spprev.help360.com.br/users/sign_in"
  ticket: "https://spprev.help360.com.br/tickets/{id}"
  historico: "https://spprev.help360.com.br/export_ticket_histories/{id}.xlsx"

credenciais:
  usuario: "gsilva@sp.gov.br"

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
7.2 config/categorias_fora.txt
Lista de categorias ignoradas (uma por linha).

7.3 Variáveis de Ambiente
Variável	Uso
HELP360_USUARIO	Login
HELP360_SENHA	Senha (não implementado)
8. Segurança das Interfaces
Aspecto	Medida
Credenciais	Nunca commitadas
Senha no terminal	getpass (sem eco)
Banco de dados	Local, sem rede
Dashboard	Restrito ao time
Dados sensíveis	Anonimizados antes de sair
9. Diagrama de Sequência — Execução Diária
text
Operador   main.py   Prog0  Prog1  Prog2  Prog3  Prog4  Prog5  Dash
   │          │        │      │      │      │      │      │      │
   │─────────>│        │      │      │      │      │      │      │
   │          │───────>│      │      │      │      │      │      │
   │          │        │──────│      │      │      │      │      │
   │          │        │      │      │      │      │      │      │
   │          │───────>│      │      │      │      │      │      │
   │          │        │──────│      │      │      │      │      │
   │          │───────────────>│      │      │      │      │      │
   │          │        │      │──────>│      │      │      │      │
   │          │──────────────────────>│      │      │      │      │
   │          │        │      │      │──────>│      │      │      │
   │          │        │      │      │      │──────>│      │      │
   │          │        │      │      │      │      │──────>│      │
   │          │        │      │      │      │      │      │──────>│
   │<─────────│────────│──────│──────│──────│──────│──────│──────│
10. Referências
03_Arquitetura.md

04_Modelo_Dados.md

05_Regras_de_Negocio.md

08_Instalacao_e_Config.md

Site Help360