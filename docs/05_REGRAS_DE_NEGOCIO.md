# 05 — Regras de Negócio

**Documento:** Regras do Domínio Help360
**Versão:** 3.0
**Última atualização:** Setembro/2026
**Público-alvo:** Desenvolvedores, QA, Product Owner, Supervisores

---

## 1. Introdução

Este documento define **todas as regras de negócio** aplicadas pelo sistema. É a **fonte da verdade** para implementação, testes e validação.

### 1.1 Glossário de Termos

| Termo | Definição |
|---|---|
| **Ticket** | Chamado registrado no Help360 |
| **Tabela fato** | Planilha manual com respostas dos tickets |
| **Data Respondido** | Data da última resposta na Tabela fato |
| **Alterado Data** | Data da última movimentação no Help360 |
| **Acompanhamento** | Arquivo final com tickets que devem ser abertos |
| **SLA** | Acordo de nível de serviço |
| **Previsão** | Data limite para resolução |
| **SPPREV** | Servidores internos (`@sp.gov.br`) |
| **Atlantic** | Funcionários da terceirizada (`@atlanticsolutions.com.br`) |
| **Backlog** | Fila interna de tickets pendentes |
| **Ação interna** | Quando `responsável == alterado_por` |
| **Ticket travado** | Ticket em aberto sem ação real por > 3 dias |

---

## 2. Classificação de Empresa

### 2.1 Regra

Toda pessoa é classificada em 4 tipos, com base no **domínio do email**:

```python
if '@atlanticsolutions.com.br' in email: return 'Atlantic'
if '@sp.gov.br' in email:                return 'SPPREV'
return 'Outro'
2.2 Regra adicional
Nomes que não estão na tabela analistas (nem no usuario_empresa.xlsx):

text
→ Classificados como 'Externo'
Motivo: muitos são analistas antigos, terceirizados de outras empresas, ou contas genéricas.

2.3 Distribuição esperada
Tipo	Comportamento
SPPREV	Gera alerta de ticket travado
Atlantic	Não gera alerta (não compete ao SPPREV)
Externo	Não gera alerta
Outro	Não gera alerta
3. Detecção de Backlog
3.1 Regra
Um ticket é considerado em backlog se a página HTML do Help360 contém:

"Este ticket se tornou um Backlog"

"Se tornou backlog"

"Em backlog"

"Aguardando backlog"

"Ticket backlog"

3.2 Comportamento
Campo backlog	Significado	Gera alerta?
0	Não está em backlog	✅ Sim (se outras regras baterem)
1	Está em backlog	❌ NÃO — é fila controlada
3.3 Motivo
Tickets em backlog são esperados — não indicam problema. Suprimi-los reduz drasticamente os falsos positivos.

4. Matriz de Verdade (12 Cenários)
4.1 Variáveis
Variável	Valores possíveis
Responsável	SPPREV, Atlantic, Outro, Externo
Alterado por	SPPREV, Atlantic, Outro, Externo
Status	Aguardando confirmação, Em atendimento, Resolvido
4.2 Cenários
ID	Responsável	Alterado por	Status	Interpretação
CEN-01	SPPREV	SPPREV	Aguardando	SPPREV ativo, aguardando usuário
CEN-02	SPPREV	Atlantic	Aguardando	⚠️ Atlantic mexeu em ticket SPPREV
CEN-03	SPPREV	SPPREV	Em atendimento	✅ Ação interna em andamento
CEN-04	SPPREV	Atlantic	Em atendimento	⚠️ Atlantic interveio
CEN-05	SPPREV	SPPREV	Resolvido	✅ SPPREV resolveu
CEN-06	SPPREV	Atlantic	Resolvido	⚠️ Atlantic resolveu ticket SPPREV
CEN-07	Atlantic	SPPREV	Aguardando	SPPREV encaminhou para Atlantic
CEN-08	Atlantic	Atlantic	Aguardando	✅ Atlantic ativo, aguardando usuário
CEN-09	Atlantic	SPPREV	Em atendimento	SPPREV encaminhou
CEN-10	Atlantic	Atlantic	Em atendimento	✅ Atlantic ativo
CEN-11	Atlantic	SPPREV	Resolvido	SPPREV resolveu para Atlantic
CEN-12	Atlantic	Atlantic	Resolvido	✅ Atlantic resolveu
4.3 Categorias fora da matriz
Valor	Significado
OUTRO	Tem movimentação, mas status fora dos 3 mapeados (Fechado, Cancelado, etc.)
SEM_DADOS	Ainda não foi enriquecido (não tem movimentação capturada)
5. Ação Interna
5.1 Regra
python
acao_interna = (responsavel_atual == ultimo_autor_movimentacao)
Valor	Significado
1	O responsável foi quem mexeu por último
0	Outra pessoa mexeu
NULL	Sem movimentação capturada (SEM_DADOS)
5.2 Interpretação
acao_interna	status	Significado
1	Em atendimento	✅ Andamento normal
1	Aguardando	⚠️ Pode ser travado
0	Em atendimento	⚠️ Outro mexeu (backlog? encaminhamento?)
0	Aguardando	✅ Aguardando usuário externo
6. Tickets Travados
6.1 Definição
Um ticket é considerado travado se TODAS as condições:

text
1. Status em aberto (não Resolvido/Fechado/Cancelado/Duplicado)
2. responsavel_empresa == 'SPPREV'      ← Só SPPREV gera alerta
3. acao_interna == 1                     ← Resp. foi quem mexeu
4. backlog == 0                          ← Não está em fila controlada
5. dias_aberto > 3                       ← Mais de 3 dias sem ação
6.2 Comportamento
Situação	Ação
SPPREV travado	⚠️ Alerta — supervisor deve cobrar
Atlantic travado	ℹ️ Informativo — não gera alerta
Externo travado	ℹ️ Informativo
Em backlog	✅ Suprimido — é esperado
6.3 Motivo da regra SPPREV
Tickets com responsável Atlantic são geridos pela própria terceirizada — não competem ao SPPREV cobrar. O SPPREV só deve se preocupar com tickets de seus próprios servidores.

7. Filtros do Dashboard
7.1 Filtros Globais (sidebar)
Filtro	Valores	Aplicação
Período	Data inicial/final	Por criado_data
Status	Todos	Filtra por status
Categoria	Todas	Filtra por categoria
Responsável	Todos	Filtra por responsável
Tipo de Empresa	SPPREV/Atlantic/Externo/Outro	Por responsavel_empresa
Status de Resposta	Todos/Respondidos/Não respondidos	Por respondido
Backlog	Todos/Em backlog/Fora do backlog	Por backlog
Ação Interna	Todos/Resp.=Alt./Resp.≠Alt.	Por acao_interna
7.2 Combinações Úteis
Objetivo	Filtros
Ver só tickets SPPREV travados	Empresa=SPPREV + Ação Interna=Resp.=Alt. + Backlog=Fora
Ver tickets aguardando usuário	Status=Aguardando confirmação
Ver tickets respondidos	Status Resposta=Respondidos
Ver SPPREV sem resposta	Empresa=SPPREV + Status Resposta=Não respondidos
8. Ciclo de Vida do Ticket
text
┌─────────┐
│ ABERTO  │
└────┬────┘
     │
     ▼
┌──────────────┐
│ EM ATENDIMENTO│◄─────┐
└──────┬───────┘      │
       │              │
       ▼              │
┌──────────────┐      │
│ AGUARDANDO   │      │
│ CONFIRMAÇÃO  │──────┘ (reabertura)
└──────┬───────┘
       │
       ▼
┌──────────┐    ┌───────────┐
│ RESOLVIDO│───▶│  BACKLOG  │
└────┬─────┘    └───────────┘
     │               │
     ▼               ▼
┌──────────┐    ┌───────────┐
│ FECHADO  │    │ Retorna a │
└──────────┘    │ atendimento│
                └───────────┘
9. Regras de SLA
9.1 Definição
O SLA é definido pelo campo previsao, calculado pelo Help360 com base em:

Categoria (SLAs diferentes por área)

Prioridade (Alta, Média, Baixa)

Tipo de solicitante (interno, externo)

9.2 Cálculo
Status	Fórmula
Cumprido	data_resolvido <= previsao
Estourado	data_resolvido > previsao
Em andamento	data_resolvido IS NULL
Em risco	previsao < hoje + 1 dia e status != Resolvido
9.3 SLA por Criticidade (regra de negócio externa)
Criticidade	Prazo	Ação
Urgente	3 dias úteis	Fechamento automático
Alta	5 dias úteis	Fechamento automático
Média 1 e 2	10 dias úteis	Fechamento automático
Baixa 1 e 2	15 dias úteis	Fechamento automático
⚠️ Nota: este cálculo em dias úteis ainda não está implementado — atualmente usamos dias corridos.

10. Convenção de Células na Tabela Fato
A Tabela fato é preenchida manualmente pelos operadores. Cada célula pode ter:

Conteúdo	Significado	Ação
0	Não respondido	NaT → abre
-	Não se aplica	NaT → abre
#N/A	Erro	NaT → abre
'' (vazio)	Sem informação	NaT → abre
"04/09/2026 - 14:03: Enviado..."	Respondido em 04/09 14:03	Data extraída
"31/08: Enviado..."	Respondido em 31/08 (ano atual)	Data extraída
10.1 Regra de Extração
Se for Timestamp nativo → usa direto

Se for número → converte série do Excel (mas ignora 0)

Se for string:

Ignora '', '0', '0.0', '-', '#N/A', '#VALUE!', 'nan', 'None'

Procura todas as datas via regex (DD/MM/AAAA e DD/MM)

Retorna a MAIOR

Se nada → NaT

11. Categorias Ignoradas
Lista definida em utils_help360.py (constante CATEGORIAS_FORA):

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
Motivo: são tratadas por outras equipes, fora do escopo da DIO/SPRO.

12. Status Monitorados
12.1 Abertos (geram alerta)
Status	Quando
Em atendimento	Previsão vigente
Resolvido	Alterado recentemente
Aguardando confirmação do usuário	Alterado recentemente
12.2 Fechados (não geram alerta)
Status	Motivo
Fechado	Já encerrado
Cancelado	Não requer ação
Duplicado	Já tratado
Aguardando Deploy	Fila controlada
13. LGPD e Privacidade
13.1 Dados Sensíveis
Campo	Tipo
tickets.solicitante	Nome, CPF, matrícula
tickets.descricao	Texto livre
mensagens.conteudo	Texto livre
13.2 Medidas
Medida	Aplicação
Anonimização	Regex substitui CPF/email/telefone
Banco local	Sem exposição em rede
Acesso restrito	Só o operador
Retenção	Sugestão: 5 anos
Auditoria	Log de toda manipulação
13.3 Função de Anonimização
python
def anonimizar_dados_lgpd(texto):
    padrao_cpf = r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'
    padrao_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    padrao_telefone = r'\b(?:\(?\d{2}\)?\s?)?(?:9?\d{4})-?\d{4}\b'

    texto = re.sub(padrao_cpf, '<CPF>', texto)
    texto = re.sub(padrao_email, '<EMAIL>', texto)
    texto = re.sub(padrao_telefone, '<TELEFONE>', texto)
    return texto
13.4 Boas Práticas
❌ Nunca commitar .db para o Git

❌ Nunca exportar relatórios com CPF completo

✅ Sempre anonimizar antes de compartilhar

✅ Sempre usar getpass para senhas

14. Referências
04_Modelo_Dados.md

06_Analises_e_Metricas.md

LGPD - Lei 13.709/2018