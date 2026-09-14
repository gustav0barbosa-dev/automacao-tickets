# 📚 Documentação Técnica — Automação Help360

**Versão:** 2.0
**Última atualização:** Setembro/2026
**Mantenedores:** Equipe de Automação — DIO/SPRO
**Repositório:** github.com/gustav0barbosa-dev/automacao-tickets

---

## 📖 Sobre esta Documentação

Este conjunto de documentos descreve **todos os aspectos técnicos** da Automação Help360,
no padrão de engenharia de software. O objetivo é que qualquer desenvolvedor, analista
ou gestor consiga **entender, manter, evoluir e replicar** o sistema sem depender de
conhecimento tribal.

### Como Navegar

**Se você é...**

| Perfil | Comece por |
|---|---|
| 🧑‍💼 **Gestor / Product Owner** | [01](01_VISAO_E_ESCOPO.md) → [02](02_REQUISITOS.md) → [11](11_ROADMAP.md) |
| 🧑‍💻 **Desenvolvedor novo no projeto** | [01](01_VISAO_E_ESCOPO.md) → [03](03_ARQUITETURA.md) → [04](04_MODELO_DADOS.md) → [08](08_INSTALACAO_E_CONFIG.md) |
| 🔧 **DevOps / Infraestrutura** | [08](08_INSTALACAO_E_CONFIG.md) → [09](09_OPERACAO_E_MANUTENCAO.md) → [10](10_TESTES.md) |
| 🧪 **QA / Testes** | [02](02_REQUISITOS.md) → [05](05_REGRAS_DE_NEGOCIO.md) → [10](10_TESTES.md) |
| 📊 **Analista de Dados** | [04](04_MODELO_DADOS.md) → [06](06_ANALISES_E_METRICAS.md) |
| 🆕 **Operador diário** | [08](08_INSTALACAO_E_CONFIG.md) → [09](09_OPERACAO_E_MANUTENCAO.md) |

---

## 📑 Sumário

### Parte I — Contexto

| # | Documento | Conteúdo |
|---|---|---|
| 01 | [Visão e Escopo](01_VISAO_E_ESCOPO.md) | Objetivo, problema, público, limites |
| 02 | [Requisitos](02_REQUISITOS.md) | Funcionais e não funcionais |

### Parte II — Design Técnico

| # | Documento | Conteúdo |
|---|---|---|
| 03 | [Arquitetura](03_ARQUITETURA.md) | Camadas, componentes, fluxos |
| 04 | [Modelo de Dados](04_MODELO_DADOS.md) | Schema SQLite, tabelas, views |
| 05 | [Regras de Negócio](05_REGRAS_DE_NEGOCIO.md) | Regras do domínio |
| 06 | [Análises e Métricas](06_ANALISES_E_METRICAS.md) | Catálogo de análises |
| 07 | [Interfaces](07_INTERFACES.md) | APIs, arquivos, contratos |

### Parte III — Operação

| # | Documento | Conteúdo |
|---|---|---|
| 08 | [Instalação e Configuração](08_INSTALACAO_E_CONFIG.md) | Setup do ambiente |
| 09 | [Operação e Manutenção](09_OPERACAO_E_MANUTENCAO.md) | Execução, monitoramento, troubleshooting |
| 10 | [Testes](10_TESTES.md) | Estratégia de testes |

### Parte IV — Evolução

| # | Documento | Conteúdo |
|---|---|---|
| 11 | [Roadmap](11_ROADMAP.md) | Fases incrementais |
| 12 | [Glossário](12_GLOSSARIO.md) | Termos técnicos e de domínio |
| 13 | [Changelog](13_CHANGELOG.md) | Histórico de versões |

---

## 🎯 Resumo Executivo

**O que é:** Uma plataforma de automação, monitoramento e análise de tickets do
sistema Help360 (SPPREV).

**O que faz:**

1. **Coleta** a base de tickets do site via Selenium
2. **Enriquece** os tickets com descrição e histórico de mensagens
3. **Persiste** em banco de dados para análise histórica
4. **Filtra** os tickets que precisam de ação
5. **Abre** os tickets no navegador para o operador
6. **Analisa** tempo de resposta, SLA, produtividade, roteamento e gargalos
7. **Alerta** sobre anomalias e SLA em risco
8. **Visualiza** em dashboard web

**Stack:** Python + Selenium + Pandas + SQLite + Streamlit

**Status:** Em evolução — ver [Roadmap](11_ROADMAP.md)

---

## 🔗 Links Úteis

- [Repositório GitHub](https://github.com/gustav0barbosa-dev/automacao-tickets)
- [Sistema Help360](https://spprev.help360.com.br)
- [Issues / Bug Tracker](https://github.com/gustav0barbosa-dev/automacao-tickets/issues)

---

## 📞 Contato

| Papel | Nome | Email |
|---|---|---|
| Product Owner | (a definir) | — |
| Tech Lead | (a definir) | — |
| Mantenedores | Equipe DIO/SPRO | — |

---

## ⚖️ Licença e Confidencialidade

Uso interno SPPREV. Dados de tickets são protegidos por LGPD.
Ver [05_Regras_de_Negocio.md](05_REGRAS_DE_NEGOCIO.md#9-lgpd-e-privacidade).
