# 07 — Interfaces

**Documento:** Contratos de Interfaces e Integrações
**Versão:** 2.0
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
| **Área de tickets** | Menu lateral → li[4] |
| **Botão de exportar** | `//*[@id="div_list_tickets"]/.../a/i` |
| **Protocolo** | HTTPS |
| **Autenticação** | Login + senha (@sp.gov.br) |

### 2.2 Endpoints consumidos

| Método | URL | Uso |
|---|---|---|
| GET | `/users/sign_in` | Página de login |
| POST | `/users/sign_in` | Enviar credenciais |
| GET | `/tickets` | Lista de tickets |
| GET | `/tickets/{id}` | Ticket individual |
| GET | `/tickets/export` | Exportação em massa |

**⚠️ Nota:** o Help360 **não expõe API REST pública**. Tudo é feito via Selenium (scraping).

---

## 3. Interfaces Internas — Arquivos

### 3.1 `tickets.xlsx`

**Gerado por:** `programa1_download.py`
**Consumido por:** `programa2_filtrar.py`

**Localização:** `~/Downloads/tickets.xlsx`

**Schema:**

| Coluna | Tipo | Descrição |
|---|---|---|
| `ID` | int | ID do ticket |
| `Status` | string | Status atual |
| `Criado Data` | datetime | Data de criação |
| `Alterado Data` | datetime | Última movimentação |
| `Previsão` | datetime | SLA |
| `Responsável` | string | Analista atual |
| `Categoria` | string | Categoria |
| `Subcategoria` | string | Subcategoria |
| `Título` | string | Título |
| `Prioridade` | string | Prioridade |
| `Solicitante` | string | Quem abriu |
| `Data do Resolvido` | datetime | Data de resolução |
| `Data do 1°resolvido` | datetime | Data do 1º atendimento |

---

### 3.2 `tickets_com_respondido.xlsx`

**Gerado por:** `programa0_preprocessar.py`
**Consumido por:** `programa2_filtrar.py`

**Localização:** `~/Downloads/tickets_com_respondido.xlsx`

**Schema:**

| Coluna | Tipo | Descrição |
|---|---|---|
| `ID` | string | ID do ticket |
| `Data Respondido` | datetime ou NaT | Data da última resposta |

---

### 3.3 `acompanhamento.xlsx`

**Gerado por:** `programa2_filtrar.py`
**Consumido por:** `programa3_abrir.py` + `programa4_persistir.py`

**Localização:** `~/Downloads/acompanhamento.xlsx`

**Schema:** Mesmas colunas de `tickets.xlsx`, filtradas.

---

### 3.4 `Tickets - Tabela fato.xlsx`

**Entrada manual** (operador)
**Consumido por:** `programa0_preprocessar.py`

**Localização:** `~/Downloads/Tickets - Tabela fato.xlsx`

**Abas:**

#### Aba `Status`

| Coluna | Conteúdo |
|---|---|
| `ID` | ID do ticket |
| Demais | Histórico de mudanças de status |

#### Aba `Acompanhamento`

| Coluna | Conteúdo |
|---|---|
| `ID` | ID do ticket |
| Demais | Texto livre com data + observação |

**Valores possíveis nas células:**
- `0` (não respondido)
- `-` (não se aplica)
- `#N/A` (erro)
- Texto com data (`"04/09/2026 - 14:03: Enviado..."`)
- Vazio

---

### 3.5 `tickets.db` (SQLite)

**Gerado por:** `programa4_persistir.py`
**Consumido por:** `programa5_enriquecer.py`, `programa6_analises.py`, `programa7_alertas.py`, `dashboard.py`

**Localização:** `dados/tickets.db`

**Tabelas:** ver [04_Modelo_Dados.md](04_MODELO_DADOS.md).

---

## 4. Interfaces entre Programas

### 4.1 Fluxo da Camada 1
┌─────────────────────┐
│ Tabela fato.xlsx │
└──────────┬──────────┘
│ (entrada manual)
▼
┌──────────────┐
│ Programa 0 │ → tickets_com_respondido.xlsx
└──────────────┘
│
▼
┌──────────────┐
│ Programa 2 │ → acompanhamento.xlsx
└──────┬───────┘
│
┌────────────┴────────────┐
▼ ▼
┌──────────────┐ ┌──────────────┐
│ Programa 3 │ │ Programa 4 │
│ (navegador) │ │ (SQLite) │
└──────────────┘ └──────────────┘

Site Help360
│
│ (Selenium)
▼
┌──────────────┐
│ Programa 1 │ → tickets.xlsx
└──────────────┘
│
▼
(consumido pelo Programa 2)

text

### 4.2 Contratos de chamada

| De | Para | Método | Parâmetros | Retorno |
|---|---|---|---|---|
| `main.py` | `programa0` | `subprocess.run` | — | exit code |
| `main.py` | `programa1` | `subprocess.run` | — | exit code |
| `main.py` | `programa2` | `subprocess.run` | `dias_antecipar` (input) | exit code |
| `main.py` | `programa3` | `subprocess.run` | — | exit code |
| `programa2` | `utils` | `import` | `tratar_datas_excel(df)` | `df` |
| `programa2` | `utils` | `import` | `filtrar_categoria(df)` | `df` |
| `programa3` | `utils` | `import` | `criar_navegador()` | `navegador` |

---

## 5. Contratos de Dados

### 5.1 Tipos primitivos

| Tipo | Representação em Python | Exemplo |
|---|---|---|
| Data | `datetime` | `2026-09-14 14:30:00` |
| Texto | `str` | `"Enviado para análise"` |
| Inteiro | `int` | `111005` |
| Booleano | `bool` (convertido de `INTEGER` no SQLite) | `True` |
| Nulo | `NaT` (data) ou `None` | — |

### 5.2 Formatos de data

| Contexto | Formato |
|---|---|
| Excel (importação) | `DD/MM/AAAA` ou `DD/MM/AAAA HH:MM` |
| SQLite | ISO: `YYYY-MM-DD HH:MM:SS` |
| Exibição | `DD/MM/AAAA HH:MM` |

### 5.3 ID de ticket

- **Formato:** inteiro positivo
- **Exemplo:** `111005`
- **Representação em arquivo:** string (para evitar notação científica)
- **Representação no banco:** INTEGER

---

## 6. Interfaces de Saída

### 6.1 Relatórios Excel

| Arquivo | Gerado por | Frequência |
|---|---|---|
| `relatorios/resumo_semanal.xlsx` | `programa6_analises.py` | Semanal |
| `relatorios/sla_mensal.xlsx` | `programa6_analises.py` | Mensal |
| `relatorios/gargalos.xlsx` | `programa6_analises.py` | Diária |

### 6.2 Relatórios PDF

| Arquivo | Gerado por | Frequência |
|---|---|---|
| `relatorios/supervisao.pdf` | `programa6_analises.py` | Semanal |

### 6.3 Notificações

| Canal | Quando | Via |
|---|---|---|
| Email | Alertas de SLA | `smtplib` |
| Email | Gargalos | `smtplib` |
| Teams | Alertas críticos | Webhook HTTP |

---

## 7. Interface com o Usuário (Dashboard)

### 7.1 Stack

- **Framework:** Streamlit
- **Porta local:** 8501
- **Acesso:** `http://localhost:8501`

### 7.2 Páginas do dashboard

| Página | Conteúdo |
|---|---|
| **Home** | KPIs gerais, últimos snapshots |
| **Tempo de Resposta** | Histogramas, evolução |
| **SLA** | Semáforo, ranking |
| **Produtividade** | Ranking por analista |
| **Roteamento** | Grafo de fluxo |
| **Gargalos** | Ranking de não retorno |
| **Backlog** | Aging, projeção |

### 7.3 Filtros disponíveis

- Período (data inicial, data final)
- Categoria
- Responsável
- Área
- Status

---

## 8. Configuração

### 8.1 Arquivo `config/settings.yaml`

```yaml
urls:
  base: "https://spprev.help360.com.br"
  login: "https://spprev.help360.com.br/users/sign_in"
  ticket: "https://spprev.help360.com.br/tickets/{id}"

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
8.2 Arquivo config/categorias_fora.txt
Lista de categorias ignoradas, uma por linha.

8.3 Variáveis de ambiente
Variável	Uso
HELP360_USUARIO	Login
HELP360_SENHA	Senha (alternativa ao getpass)
9. Segurança das Interfaces
Aspecto	Medida
Credenciais	Nunca commitadas
Senha no terminal	getpass (sem eco)
Banco de dados	Local, sem rede
Dashboard	Restrito ao time
Dados sensíveis	Anonimizados antes de sair
10. Diagrama de Sequência — Execução Diária
text
Operador    main.py   Prog0   Prog1   Prog2   Prog3
   │           │        │       │       │       │
   │──────────>│        │       │       │       │
   │           │───────>│       │       │       │
   │           │        │──────>│       │       │ (lê Tabela fato)
   │           │        │<──────│       │       │
   │           │        │       │       │       │
   │           │───────>│       │       │       │
   │           │        │──────>│       │       │ (baixa do site)
   │           │        │<──────│       │       │
   │           │        │       │       │       │
   │           │───────────────>│       │       │
   │           │        │       │──────>│       │ (filtra)
   │           │        │       │<──────│       │
   │           │        │       │       │       │
   │           │───────────────────────>│       │
   │           │        │       │       │──────>│ (abre abas)
   │<──────────│────────│───────│───────│───────│
11. Referências
03_Arquitetura.md

04_Modelo_Dados.md

05_Regras_de_Negocio.md

Site Help360
"""

