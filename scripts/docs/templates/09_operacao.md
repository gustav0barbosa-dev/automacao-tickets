# 09 — Operação e Manutenção

**Documento:** Guia de Operação, Monitoramento e Manutenção
**Versão:** 2.0
**Público-alvo:** Operadores, DevOps, Suporte

---

## 1. Ciclo Diário de Operação

### 1.1 Manhã (antes de rodar)

1. **Atualizar a Tabela fato** com as respostas do dia anterior
2. **Salvar em `~/Downloads/Tickets - Tabela fato.xlsx`**
3. **Verificar se não há processos travados** (ver seção 4)

### 1.2 Executar o pipeline

```powershell
cd C:\...\automacao-tickets
python main.py
O que responder:

Pergunta	Resposta
"Deseja processar a Tabela fato?"	s
"Executar programa1_download?"	s
"Executar programa2_filtrar?"	s
"Executar programa3_abrir?"	s
"Dias para retroceder?"	2 (ou conforme necessidade)
1.3 Tratar os tickets
O Chrome abrirá as abas. Trate cada ticket e, ao final do dia, atualize a Tabela fato.

1.4 Fim do dia
Atualizar Tabela fato com as respostas dadas

Salvar para uso no dia seguinte

(Opcional) Fazer backup do tickets.db

2. Comandos Essenciais
2.1 Executar pipeline completo
powershell
python main.py
2.2 Executar etapa individual
powershell
cd src
python programa0_preprocessar.py
python programa1_download.py
python programa2_filtrar.py
python programa3_abrir.py
2.3 Rodar em modo dry-run
powershell
python scripts\teste.py
Replica a lógica do Programa2 sem abrir nada.

2.4 Gerar documentação
powershell
python scripts\gerar_docs.py
3. Monitoramento
3.1 Logs
Por padrão, os logs vão para o terminal. Para persistir:

powershell
python main.py > dados\logs\execucao_20260914.log 2>&1
3.2 Arquivos gerados a cada execução
Arquivo	O que indica
~/Downloads/tickets.xlsx	Download bem-sucedido
~/Downloads/tickets_com_respondido.xlsx	Tabela fato processada
~/Downloads/acompanhamento.xlsx	Filtragem bem-sucedida
dados/tickets.db	Persistência funcionando
3.3 Verificações rápidas
powershell
# Ver tamanho dos arquivos
Get-Item ~\Downloads\tickets.xlsx | Select-Object Name, Length, LastWriteTime
Get-Item ~\Downloads\acompanhamento.xlsx | Select-Object Name, Length, LastWriteTime

# Ver últimas linhas do log
Get-Content dados\logs\*.log -Tail 50
4. Troubleshooting
4.1 Erros comuns
Sintoma	Causa provável	Solução
"Nenhum ticket foi aberto"	Filtros muito restritivos	Rodar teste.py para ver onde travou
"FileNotFoundError: tickets.xlsx"	Programa1 falhou	Verificar se o download funcionou
"WebDriverException"	ChromeDriver desatualizado	pip install --upgrade webdriver-manager
Chrome trava ao abrir abas	Muitos tickets de uma vez	Aumentar delay em settings.yaml
Timeout no login	Site lento	Aumentar timeout_segundos
Datas invertidas (mês/dia)	Formato US no Excel	Verificar dayfirst=True no utils
4.2 Diagnóstico por sintoma
"Abrimos tickets de meses atrás"
Causa mais provável: filtro F2 (Em Atendimento) só considera Previsão, não Alterado Data.

Diagnóstico:

python
import pandas as pd, os
df = pd.read_excel(os.path.join(os.path.expanduser('~'), 'Downloads', 'tickets.xlsx'))
# Verificar se os tickets antigos são "Em atendimento"
print(df[df['Alterado Data'] < '2026-08-01']['Status'].value_counts())
Solução: adicionar Alterado Data >= hoje - N na regra_em_atendimento.

"Nenhum ticket aparece"
Causa: tickets_com_respondido.xlsx marcando tudo como respondido.

Diagnóstico:

python
import pandas as pd, os
df = pd.read_excel(os.path.join(os.path.expanduser('~'), 'Downloads', 'tickets_com_respondido.xlsx'))
print("Com data:", df['Data Respondido'].notna().sum())
print("Sem data:", df['Data Respondido'].isna().sum())
Esperado: maioria COM data. Se 100% sem data, algo errado.

"Erro de importação"
Causa: rodando de pasta errada.

Solução: sempre rodar main.py da raiz do projeto.

4.3 Como pedir ajuda
Ao reportar problema, incluir:

Comando executado

Saída completa do terminal (com traceback se houver)

Arquivos envolvidos (tamanho, data de modificação)

Screenshot do erro (se aplicável)

Passos para reproduzir

5. Manutenção
5.1 Backup
powershell
# Backup do banco
Copy-Item dados\tickets.db dados\backup\tickets_$(Get-Date -Format "yyyyMMdd").db

# Backup dos arquivos Excel
Copy-Item ~\Downloads\tickets.xlsx dados\backup\tickets_$(Get-Date -Format "yyyyMMdd").xlsx
Frequência recomendada: semanal.

5.2 Limpeza de logs
powershell
# Remover logs com mais de 30 dias
Get-ChildItem dados\logs\*.log | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item
5.3 Atualização de dependências
powershell
pip install -r requirements.txt --upgrade
5.4 Atualização do código
powershell
git pull
6. Recuperação de Falhas
6.1 Se o Programa1 falhar
O tickets.xlsx pode estar incompleto. Verifique:

powershell
Get-Item ~\Downloads\tickets.xlsx | Select-Object Length, LastWriteTime
Se o tamanho for suspeito (< 100 KB), não rode o Programa2. Rode o Programa1 novamente.

6.2 Se o Programa2 falhar
O acompanhamento.xlsx não foi gerado. Verifique:

powershell
Test-Path ~\Downloads\acompanhamento.xlsx
Se False, veja o traceback no terminal.

6.3 Se o Programa3 travar
Feche o Chrome forçadamente:

powershell
Get-Process chrome | Stop-Process -Force
6.4 Se o banco corromper
Restaure do backup:

powershell
Copy-Item dados\backup\tickets_20260901.db dados\tickets.db
7. Boas Práticas
7.1 ✅ Fazer
Rodar o pipeline sempre no mesmo horário

Fazer backup semanal do banco

Atualizar a Tabela fato todos os dias

Verificar logs após cada execução

Usar a mesma máquina (evita inconsistências)

7.2 ❌ Não fazer
Rodar de máquinas diferentes em paralelo

Deixar arquivos Excel abertos durante a execução

Fechar o terminal durante o pipeline

Ignorar warnings de importação

Rodar em produção sem testar em homologação

8. Contatos e Escalação
Situação	Contato
Bug no pipeline	Equipe de Automação
Site Help360 fora do ar	TI Help360
Acesso negado	Gestor imediato
Suspeita de vazamento	Segurança da Informação
9. Referências
08_Instalacao_e_Config.md

10_Testes.md

11_Roadmap.md
"""

