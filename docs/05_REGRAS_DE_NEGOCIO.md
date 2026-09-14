# 05 — Regras de Negócio

**Documento:** Regras do Domínio Help360
**Versão:** 2.0
**Público-alvo:** Desenvolvedores, QA, Product Owner

---

## 1. Introdução

Este documento define **todas as regras de negócio** aplicadas pelo sistema,
independente de implementação. Serve como **fonte da verdade** para:

- Desenvolvedores (implementação)
- QA (testes)
- Product Owner (validação)
- Novos membros (onboarding)

---

## 2. Glossário de Termos

| Termo | Definição |
|---|---|
| **Ticket** | Chamado registrado no Help360 |
| **Tabela fato** | Planilha manual com respostas dos tickets |
| **Data Respondido** | Data da última resposta na Tabela fato |
| **Alterado Data** | Data da última movimentação no Help360 |
| **Acompanhamento** | Arquivo final com tickets que devem ser abertos |
| **SLA** | Service Level Agreement |
| **Previsão** | Data limite para resolução (SLA do ticket) |

---

## 3. Regra Central — Exibição de Ticket

### 3.1 Um ticket DEVE SER ABERTO se:

| # | Condição | Fórmula |
|---|---|---|
| 1 | Nunca foi respondido | `Data Respondido IS NULL` |
| 2 | Foi respondido, mas voltou a ter movimentação | `Data Respondido <= Alterado Data` |
| 3 | Status temporal recente | `Status ∈ {Resolvido, Aguardando}` **E** `Alterado Data >= hoje - N` |
| 4 | Em atendimento com previsão vigente | `Status = 'Em atendimento'` **E** `Previsão` dentro da janela |

### 3.2 Um ticket NÃO DEVE SER ABERTO se:

| # | Condição | Fórmula |
|---|---|---|
| 1 | Já respondido, sem movimentação posterior | `Data Respondido > Alterado Data` |
| 2 | Fora da janela temporal | `Alterado Data < hoje - N` |
| 3 | Previsão muito antiga | `Previsão < hoje - 365 dias` |
| 4 | Categoria não monitorada | `Categoria ∈ CATEGORIAS_FORA` |

---

## 4. Os 6 Filtros em Cascata (Programa2)

### Filtro F1 — Status Temporais

```python
Status IN ('Resolvido', 'Aguardando confirmação do usuário')
AND Alterado Data >= (hoje - N dias)
Filtro F2 — Em Atendimento
python
Status = 'Em atendimento'
AND Previsão <= (hoje + dias_postergar)
AND Previsão >= (hoje - 365 dias)
Filtro F3 — Categoria
python
Categoria NOT IN CATEGORIAS_FORA
Filtros F4a / F4b / F4c — Respondidos
Filtro	Condição	Ação
F4a	Data Respondido IS NULL	Mantém
F4b	Data Respondido <= Alterado Data	Mantém
F4c	Data Respondido > Alterado Data	Remove
5. Convenção de Células na Tabela Fato
Conteúdo	Significado	Ação
0	Não respondido	NaT → abre
-	Não se aplica	NaT → abre
#N/A	Erro	NaT → abre
'' (vazio)	Sem informação	NaT → abre
"04/09/2026 - 14:03: Enviado..."	Respondido em 04/09 14:03	Data extraída
"31/08: Enviado..."	Respondido em 31/08 (ano atual)	Data extraída
6. Categorias Ignoradas
text
1ª Etapa Censo
Alteração de Grupo de Pagamento
Alterações Bancárias
Aplicações Folha
Cancelar Protocolo
Cálculo da Média
Composição
Consignatárias
Deploy - Homologação
Extinção
Extinção - Correção Monetária
Extinção - Divergência de Valores
Extinção - Participação Resultados (PR)
Folha de Pagamento
Monitoramento Folha
Parametrização Folha
Processamento Folha
Reabertura de Protocolo
Reajuste
Recadastramento
Reenvio Bancário
Reprocessamento Folha
Retorno de Tarefa
Rubricas
Rubricas Judiciais Base Duplicadas
Rúbricas Concomitantes
Task
Vínculos
Visita domiciliar
7. Status Monitorados
7.1 Abertos
Status	Quando abre
Em atendimento	Previsão vigente
Resolvido	Alterado recentemente
Aguardando confirmação do usuário	Alterado recentemente
7.2 NÃO abertos
Status	Motivo
Fechado	Já encerrado
Cancelado	Não requer ação
Duplicado	Já tratado em outro ticket
8. Regras de SLA
8.1 Definição
O SLA de cada ticket é definido no campo Previsão, calculado pelo Help360.

8.2 Cálculo de Cumprimento
Status	Fórmula
Cumprido	data_resolvido <= previsao
Estourado	data_resolvido > previsao
Em andamento	data_resolvido IS NULL
Em risco	previsao < hoje + 1 dia e status != Resolvido
9. LGPD e Privacidade
9.1 Dados Sensíveis
Campo	Tipo de dado
tickets.solicitante	Nome, CPF, matrícula
tickets.descricao	Texto livre
mensagens.conteudo	Texto livre
9.2 Medidas Aplicadas
Medida	Aplicação
Anonimização em relatórios	Regex substitui CPF/email/telefone
Banco local	Sem exposição em rede
Acesso restrito	Só o operador
Retenção	Sugestão: 5 anos
Auditoria	Log de toda manipulação
9.3 Função de Anonimização
python
def anonimizar_dados_lgpd(texto):
    padrao_cpf = r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'
    padrao_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    padrao_telefone = r'\b(?:\(?\d{2}\)?\s?)?(?:9?\d{4})-?\d{4}\b'

    texto = re.sub(padrao_cpf, '<CPF>', texto)
    texto = re.sub(padrao_email, '<EMAIL>', texto)
    texto = re.sub(padrao_telefone, '<TELEFONE>', texto)
    return texto
10. Regras de Roteamento
10.1 Encaminhamento Correto
Um encaminhamento é correto se o destino resolveu o ticket.

10.2 Encaminhamento Incorreto
Um encaminhamento é incorreto se o ticket voltou da área.

10.3 Cálculo de Pulos
text
pulos = count(encaminhamentos no histórico)
Um ticket ideal tem 0-1 pulos. Tickets com 3+ pulos indicam roteamento ruim.

11. Regras de Análise
11.1 Tempo de Resposta
text
tempo_resposta = data_resolvido - criado_data
11.2 Tempo até 1ª Ação
text
tempo_1a_acao = primeira_mensagem_do_responsavel - recebimento
Se > 48h, o ticket é "esquecido".

11.3 Produtividade
⚠️ Cuidado: produtividade não é só volume.

11.4 Reincidência
Mesmo solicitante abre 3+ tickets em 30 dias.

12. Ciclo de Vida do Ticket
text
ABERTO → EM ATENDIMENTO → AGUARDANDO CONFIRMAÇÃO → RESOLVIDO → FECHADO
              ↑                                            │
              └──────────── (reabertura) ──────────────────┘
13. Referências
02_Requisitos.md

04_Modelo_Dados.md

06_Analises_e_Metricas.md

text

---
