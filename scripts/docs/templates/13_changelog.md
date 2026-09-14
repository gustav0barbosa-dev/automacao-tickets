# 13 — Changelog

**Documento:** Histórico de Versões
**Versão:** 2.0
**Público-alvo:** Todos os envolvidos

---

## Formato

Este changelog segue o padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

### Tipos de mudança

| Categoria | Significado |
|---|---|
| **Adicionado** | Nova funcionalidade |
| **Modificado** | Mudança em funcionalidade existente |
| **Descontinuado** | Funcionalidade em vias de remoção |
| **Removido** | Funcionalidade removida |
| **Corrigido** | Bug fixado |
| **Segurança** | Correção relacionada a vulnerabilidades |

---

## [Não lançado]

### Planejado
- Fase 1 — Persistência em SQLite (`programa4_persistir.py`)
- Fase 2 — Enriquecimento de tickets (`programa5_enriquecer.py`)
- Fase 3 — Análises básicas (`programa6_analises.py`)

---

## [2.0.0] — 2026-09-14

### Adicionado
- Documentação técnica completa em `docs/` (13 documentos)
- Geradores automáticos de documentação em `scripts/docs/`
- Sistema de templates `.md` para os documentos
- Script `migrar_docs_legados.py` para converter geradores antigos
- Estrutura modular no `src/`
- Configuração externalizada em `config/settings.yaml`
- Lista de categorias em `config/categorias_fora.txt`

### Modificado
- Pipeline refatorado com `main.py` + 4 programas separados
- Todos os caminhos migrados para `os.path.expanduser('~')` (portabilidade)
- `Programa0` deixou de gerar `tickets.xlsx` (é responsabilidade do Programa1)
- `Programa0` corrigiu extração de datas — ignora `0`, `-`, `#N/A`
- `utils_help360.tratar_datas_excel` agora usa `dayfirst=True` + `format='mixed'`
- `utils_help360.anonimizar_dados_lgpd` corrigiu typo `isinstante` → `isinstance`

### Corrigido
- Falha de merge entre `tickets.xlsx` e `tickets_com_respondido.xlsx` por tipo de ID
- Filtro de respondidos no `Programa2` (comparação com `Alterado Data`)
- Caminho absoluto no `Programa3` (agora busca em `~/Downloads`)
- Filtro de previsão no `Programa2` que estava no bloco errado
- Data mínima de previsão dinâmica (`hoje - 365 dias`)

### Segurança
- Credenciais nunca hardcoded
- Senha via `getpass`
- Anonimização de CPF/email/telefone em relatórios
- `.gitignore` configurado para não versionar `.xlsx`, `.log`, `.db`

---

## [1.5.0] — 2026-08-15

### Adicionado
- `Programa3` — abertura automática de tickets no Chrome
- `Programa2` — filtro de "não retorno" (respondidos sem movimentação)
- `utils_help360.verificar_arquivo`

### Modificado
- `Programa1` agora valida colunas obrigatórias
- `Programa0` extrai a **maior** data encontrada na célula

### Corrigido
- Duplicação de cabeçalho no `tickets_com_respondido.xlsx`
- Tratamento de `NaT` no filtro de respondidos

---

## [1.0.0] — 2026-07-01

### Adicionado
- Versão inicial do pipeline
- `Programa0` — processamento da Tabela fato
- `Programa1` — download de tickets via Selenium
- `Programa2` — filtragem com regras básicas
- Biblioteca compartilhada `utils_help360.py`

### Estrutura inicial
producao/
├── main.py
├── Programa0_preprocessar.py
├── Programa1.py
├── Programa2.py
├── Programa3.py
└── utils_help360.py

text

---

## Versionamento Semântico

Este projeto segue [SemVer](https://semver.org/lang/pt-BR/):
MAJOR.MINOR.PATCH
│ │ │
│ │ └── Correções compatíveis (bug fixes)
│ └──────── Novas funcionalidades compatíveis
└────────────── Mudanças que quebram compatibilidade

text

### Exemplos

| Versão | Quando usar |
|---|---|
| `2.0.0` | Reestruturação completa |
| `1.5.0` | Nova funcionalidade (ex: persistência) |
| `1.5.1` | Correção de bug |

---

## Como Registrar uma Mudança

Ao fazer um commit que merece entrar no changelog:

1. Adicionar uma entrada em `[Não lançado]`
2. Escolher a categoria (`Adicionado`, `Modificado`, `Corrigido`, etc.)
3. Escrever em **linguagem clara**, não técnica
4. Fazer o commit

**Exemplo:**

```bash
git add .
git commit -m "Adiciona Programa4 — persistência em SQLite

- Nova tabela 'snapshots' para controle de execuções
- Backup automático do banco antes de cada carga
- Corrige encoding UTF-8 nos logs"
Referências
Keep a Changelog

Semantic Versioning

11_Roadmap.md
"""

