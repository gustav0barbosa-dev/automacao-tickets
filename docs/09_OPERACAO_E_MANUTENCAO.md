# 09 — Operação e Manutenção

**Documento:** Guia de Operação, Monitoramento e Manutenção
**Versão:** 3.0
**Última atualização:** Setembro/2026
**Público-alvo:** Operadores, DevOps, Suporte

---

## 1. Ciclo Diário de Operação

### 1.1 Manhã (antes de rodar)

1. **Atualizar a Tabela fato** com as respostas do dia anterior
2. **Salvar em** `~/Downloads/Tickets - Tabela fato.xlsx`
3. **Verificar se não há processos travados** (ver seção 6)

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
1.3 Após o pipeline — atualizar o banco
Novo passo (Sprint 2): atualizar o banco com os dados do dia.

powershell
# 1. Persistir tickets no banco
python src\programa4_persistir.py

# 2. Enriquecer os tickets que mudaram (últimos 7 dias)
python src\programa5_enriquecer.py --dias 7

# 3. Marcar respondidos (conforme Tabela fato)
python scripts\marcar_respondidos.py

# 4. Marcar empresa dos responsáveis
python scripts\marcar_empresa_responsavel.py

# 5. Aplicar matriz de verdade
python scripts\diagnosticar_tickets.py
1.4 Tratar os tickets
O Chrome abrirá as abas. Trate cada ticket e, ao final do dia, atualize a Tabela fato.

1.5 Fim do dia
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
python programa0_preprocessar.py   # Tabela fato
python programa1_download.py        # Download
python programa2_filtrar.py         # Filtro
python programa3_abrir.py           # Abrir no navegador
python programa4_persistir.py       # Persistir no banco
python programa5_enriquecer.py      # Enriquecer (backlog, movs, msgs)
2.3 Scripts auxiliares
Comando	O que faz
python scripts\carregar_analistas.py	Popula tabela analistas do usuario_empresa.xlsx
python scripts\marcar_respondidos.py	Marca tickets respondidos (Tabela fato)
python scripts\marcar_empresa_responsavel.py	Preenche responsavel_empresa
python scripts\diagnosticar_tickets.py	Aplica matriz de verdade
python scripts\aplicar_migration.py	Aplica migrations SQL
python scripts\verificar_banco.py	Verifica schema
python scripts\verificar_ticket.py <ID>	Detalhes de um ticket
2.4 Dry-run (teste sem abrir navegador)
powershell
python scripts\teste.py
3. Sequência Completa de Atualização
Execute nesta ordem quando quiser atualizar tudo:

powershell
# ==================== 1. PIPELINE ====================
python main.py

# ==================== 2. PERSISTÊNCIA ====================
python src\programa4_persistir.py

# ==================== 3. ENRIQUECIMENTO ====================
# Últimos 7 dias (uso diário, ~10 min)
python src\programa5_enriquecer.py --dias 7

# Últimos 30 dias (uso semanal, ~40 min)
# python src\programa5_enriquecer.py --dias 30

# ==================== 4. SCRIPTS DE DADOS ====================
python scripts\carregar_analistas.py           # Se mudou lista de analistas
python scripts\marcar_respondidos.py           # Sempre após atualizar Tabela fato
python scripts\marcar_empresa_responsavel.py   # Sempre após carregar analistas
python scripts\diagnosticar_tickets.py         # Sempre após enriquecimento

# ==================== 5. DASHBOARD ====================
python -m streamlit run dashboard/app.py
4. Monitoramento
4.1 Logs
Logs do programa5:

powershell
Get-Content dados\logs\programa5_YYYY-MM-DD.log -Tail 50
Persistir logs do terminal:

powershell
python main.py > dados\logs\execucao_$(Get-Date -Format "yyyy-MM-dd").log 2>&1
4.2 Arquivos Gerados
Arquivo	O que indica
~/Downloads/tickets.xlsx	Download bem-sucedido
~/Downloads/tickets_com_respondido.xlsx	Tabela fato processada
~/Downloads/acompanhamento.xlsx	Filtragem OK
dados/tickets.db	Persistência funcionando
dados/historicos/{id}.xlsx	Enriquecimento OK
4.3 Verificações Rápidas
powershell
# Ver últimas linhas do log
Get-Content dados\logs\programa5_2026-09-18.log -Tail 20

# Ver estado do banco
python scripts\verificar_banco.py

# Ver um ticket específico
python scripts\verificar_ticket.py 111239
5. Troubleshooting
5.1 Erros Comuns
Sintoma	Causa	Solução
"Nenhum ticket foi aberto"	Filtros muito restritivos	Rodar teste.py
FileNotFoundError: tickets.xlsx	Programa1 falhou	Verificar download
WebDriverException	ChromeDriver desatualizado	pip install --upgrade webdriver-manager
Chrome trava ao abrir abas	Muitos tickets	Aumentar delay
Timeout no login	Site lento	Aumentar timeout_segundos
Datas invertidas	Formato US no Excel	Verificar dayfirst=True
table analistas has no column named empresa_tipo	Migration faltando	ALTER TABLE analistas ADD COLUMN empresa_tipo TEXT;
no such column: classificacao	Migration faltando	ALTER TABLE tickets ADD COLUMN classificacao TEXT;
5.2 Diagnóstico por Sintoma
"Muitos tickets em OUTRO no diagnóstico"
Causa: os tickets têm movimentação mas o status não está nos 3 mapeados.

Verificar:

powershell
python -c "import sqlite3; c=sqlite3.connect('dados/tickets.db'); [print(r) for r in c.execute(\"SELECT diagnostico, COUNT(*) FROM tickets GROUP BY diagnostico\")]"
Solução: se > 50% em OUTRO, verificar se os status mapeados fazem sentido.

"Muitos tickets SEM_DADOS"
Causa: os tickets ainda não foram enriquecidos.

Verificar:

powershell
python -c "import sqlite3; c=sqlite3.connect('dados/tickets.db'); print('Enriquecidos:', c.execute('SELECT COUNT(*) FROM tickets WHERE enriquecido=1').fetchone()[0])"
Solução: rodar o Programa5 com mais dias:

powershell
python src\programa5_enriquecer.py --dias 30
"Tickets SPPREV não aparecem em travados"
Verificar 3 coisas:

A coluna responsavel_empresa está preenchida?

powershell
python -c "import sqlite3; c=sqlite3.connect('dados/tickets.db'); print(c.execute(\"SELECT responsavel_empresa, COUNT(*) FROM tickets GROUP BY responsavel_empresa\").fetchall())"
Os analistas foram carregados?

powershell
python scripts\verificar_analistas.py
Rodou o diagnóstico depois?

powershell
python scripts\diagnosticar_tickets.py
"Enriquecimento caiu em login"
Causa: sessão expirou no meio do processo.

Solução: o script marca o ticket como enriquecido=3 e continua. Rodar de novo processa os pendentes.

"Chrome fecha sozinho no enriquecimento"
Causa: consumo de memória acumulado (muitas abas abertas).

Solução:

powershell
# Rodar em lotes
python src\programa5_enriquecer.py --dias 7 --limite 50
5.3 Como Pedir Ajuda
Ao reportar problema, incluir:

Comando executado

Saída completa do terminal (com traceback)

Arquivos envolvidos (tamanho, data)

Screenshot (se aplicável)

Passos para reproduzir

6. Manutenção
6.1 Backup
powershell
# Backup do banco
$data = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item dados\tickets.db "dados\backup\tickets_$data.db"

# Backup dos Excel
Copy-Item ~\Downloads\tickets.xlsx "dados\backup\tickets_$data.xlsx"
Frequência: semanal + antes de migrations.

6.2 Limpeza de Logs
powershell
# Remover logs com mais de 30 dias
Get-ChildItem dados\logs\*.log |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item
6.3 Atualização de Dependências
powershell
pip install -r requirements.txt --upgrade
6.4 Atualização do Código
powershell
git pull
pip install -r requirements.txt
6.5 Aplicar Novas Migrations
Após git pull, sempre verificar se há migrations novas:

powershell
Get-ChildItem dados\migrations\*.sql | Sort-Object Name
python scripts\aplicar_migration.py
Atenção: o script ignora erros de coluna duplicada (idempotente).

7. Recuperação de Falhas
7.1 Se o Programa1 falhar
O tickets.xlsx pode estar incompleto.

powershell
Get-Item ~\Downloads\tickets.xlsx | Select-Object Length, LastWriteTime
Se tamanho < 100 KB → rodar Programa1 novamente.

7.2 Se o Programa5 falhar
O enriquecido=3 marca os que falharam. Para tentar de novo:

powershell
python -c "import sqlite3; c=sqlite3.connect('dados/tickets.db'); c.execute('UPDATE tickets SET enriquecido = 0 WHERE enriquecido = 3'); c.commit(); print(c.total_changes, 'resetados')"
7.3 Se o banco corromper
Restaurar do backup:

powershell
Copy-Item dados\backup\tickets_YYYYMMDD_HHMMSS.db dados\tickets.db
7.4 Se o dashboard travar
powershell
# Matar processo do Streamlit
Get-Process | Where-Object { $_.ProcessName -like "*streamlit*" } | Stop-Process -Force

# Rodar de novo
python -m streamlit run dashboard/app.py
8. Boas Práticas
8.1 ✅ Fazer
Rodar o pipeline sempre no mesmo horário

Fazer backup semanal do banco

Atualizar a Tabela fato todos os dias

Verificar logs após cada execução

Rodar as migrations após git pull

Usar a mesma máquina (evita inconsistências)

8.2 ❌ Não Fazer
Rodar de máquinas diferentes em paralelo

Deixar arquivos Excel abertos durante a execução

Fechar o terminal durante o pipeline

Ignorar warnings de importação

Commitar tickets.db para o Git

Fazer backup sem verificar integridade

9. Fluxo de Atualização Semanal (resumo)
Segunda-feira (10 min):

powershell
python main.py
python src\programa4_persistir.py
python src\programa5_enriquecer.py --dias 7
python scripts\marcar_respondidos.py
python scripts\diagnosticar_tickets.py
Sexta-feira (40 min):

powershell
python main.py
python src\programa4_persistir.py
python src\programa5_enriquecer.py --dias 30
python scripts\marcar_respondidos.py
python scripts\marcar_empresa_responsavel.py
python scripts\diagnosticar_tickets.py
Mensal (1x):

powershell
# Backup
Copy-Item dados\tickets.db "dados\backup\tickets_$(Get-Date -Format 'yyyyMM').db"

# Atualização completa
python src\programa5_enriquecer.py --dias 90
python scripts\diagnosticar_tickets.py
10. Contatos e Escalação
Situação	Contato
Bug no pipeline	Equipe de Automação
Site Help360 fora do ar	TI Help360
Acesso negado	Gestor imediato
Suspeita de vazamento	Segurança da Informação
Erro no banco	DBA / Suporte
11. Referências
08_Instalacao_e_Config.md

10_Testes.md

11_Roadmap.md