@echo off
chcp 65001 >nul
cls

cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat

:MENU
cls
echo ============================================================
echo  HELP360 - MENU PRINCIPAL
echo ============================================================
echo.
echo  [1] Atualizacao rapida (so download + persistencia)
echo  [2] Atualizacao completa (tudo + anonimizacao + push)
echo  [3] So enriquecer (Programa5)
echo  [4] So analise de SLA
echo  [5] Testar anonimizacao
echo  [6] Ver status do banco
echo  [7] Rodar dashboard local
echo  [8] Sair
echo.
echo ============================================================
set /p OPCAO="Escolha uma opcao [1-8]: "

if "%OPCAO%"=="1" goto RAPIDO
if "%OPCAO%"=="2" goto COMPLETO
if "%OPCAO%"=="3" goto ENRIQUECER
if "%OPCAO%"=="4" goto SLA
if "%OPCAO%"=="5" goto ANON_TESTE
if "%OPCAO%"=="6" goto STATUS
if "%OPCAO%"=="7" goto DASHBOARD
if "%OPCAO%"=="8" goto SAIR
goto MENU

:RAPIDO
cls
echo [1/2] Baixando tickets...
python src\Programa1_download.py
echo [2/2] Persistindo...
python src\programa4_persistir.py
pause
goto MENU

:COMPLETO
cls
echo [1/6] Download...
python src\Programa1_download.py
if errorlevel 1 goto ERRO
echo [2/6] Persistencia...
python src\programa4_persistir.py
if errorlevel 1 goto ERRO
echo [3/6] Enriquecimento...
python src\programa5_enriquecer.py --dias 30
echo [4/6] SLA...
python scripts\analisar_sla_criticidade.py
echo [5/6] Anonimizacao...
python scripts\anonimizar_retroativo.py
echo [6/6] Compactar + commit + push...
python -c "import gzip, shutil; f_in=open('dados/tickets.db','rb'); f_out=gzip.open('dados/tickets.db.gz','wb'); shutil.copyfileobj(f_in, f_out); f_in.close(); f_out.close()"
git add -f dados\tickets.db.gz
git commit -m "sync: banco atualizado"
git push origin main
echo.
echo [OK] Concluido!
pause
goto MENU

:ENRIQUECER
cls
python src\programa5_enriquecer.py --dias 30
pause
goto MENU

:SLA
cls
python scripts\analisar_sla_criticidade.py
pause
goto MENU

:ANON_TESTE
cls
python scripts\testar_anonimizacao.py
pause
goto MENU

:STATUS
cls
echo ============================================================
echo  STATUS DO BANCO
echo ============================================================
python -c "import sqlite3; c=sqlite3.connect('dados/tickets.db'); print('Tickets:', c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]); print('Movimentacoes:', c.execute('SELECT COUNT(*) FROM movimentacoes').fetchone()[0]); print('Mensagens:', c.execute('SELECT COUNT(*) FROM mensagens').fetchone()[0]); c.close()"
pause
goto MENU

:DASHBOARD
cls
echo Iniciando dashboard local...
echo Acesse: http://localhost:8501
streamlit run dashboard/app.py
goto MENU

:ERRO
echo [ERRO] Algo falhou!
pause
goto MENU

:SAIR
exit /b 0