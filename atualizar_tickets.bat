@echo off
chcp 65001 >nul
cls

echo ============================================================
echo  HELP360 - ATUALIZAR E PUBLICAR
echo ============================================================
echo.
echo  Este script vai:
echo    1. Baixar tickets do Help360 (Programa1)
echo    2. Sincronizar banco (Programa4 - remove orfaos)
echo    3. Enriquecer (Programa5)
echo    4. Analisar SLA
echo    5. Anonimizar (LGPD)
echo    6. Recomprimir banco (.gz)
echo    7. Commit + push (Railway migra)
echo.
echo ============================================================
pause

cd /d "%~dp0"

REM Ativa o venv
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM ==================== FASE 1: BAIXAR ====================
echo.
echo ============================================================
echo  FASE 1/6 - Baixar tickets do Help360
echo ============================================================
python src\Programa1_download.py
if errorlevel 1 (
    echo [ERRO] Programa1 falhou!
    pause
    exit /b 1
)

REM ==================== FASE 2: SINCRONIZAR ====================
echo.
echo ============================================================
echo  FASE 2/6 - Sincronizar banco (remove orfaos)
echo ============================================================
python src\programa4_persistir.py
if errorlevel 1 (
    echo [ERRO] Programa4 falhou!
    pause
    exit /b 1
)

REM ==================== FASE 3: ENRIQUECER ====================
echo.
echo ============================================================
echo  FASE 3/6 - Enriquecer (Programa5)
echo ============================================================
python src\programa5_enriquecer.py --dias 30
if errorlevel 1 (
    echo [AVISO] Programa5 falhou - continuando...
)

REM ==================== FASE 4: SLA ====================
echo.
echo ============================================================
echo  FASE 4/6 - Analise de SLA
echo ============================================================
python scripts\analisar_sla_criticidade.py

REM ==================== FASE 5: LGPD ====================
echo.
echo ============================================================
echo  FASE 5/6 - Anonimizacao LGPD
echo ============================================================
python scripts\anonimizar_retroativo.py

REM ==================== FASE 6: RECOMPRIMIR + PUSH ====================
echo.
echo ============================================================
echo  FASE 6/6 - Recomprimir + commit + push
echo ============================================================

REM Confirma o total no SQLite
python -c "import sqlite3; conn = sqlite3.connect('dados/tickets.db'); print(f'Tickets no SQLite: {conn.execute(\"SELECT COUNT(*) FROM tickets\").fetchone()[0]}'); conn.close()"

REM Recomprimir
echo.
echo Recomprimindo banco...
python -c "import gzip, shutil; f_in=open('dados/tickets.db','rb'); f_out=gzip.open('dados/tickets.db.gz','wb'); shutil.copyfileobj(f_in, f_out); f_in.close(); f_out.close(); print('OK: .gz gerado')"

REM Confirma o .gz
python scripts\verificar_gz.py

REM Adiciona + commit + push
echo.
echo Fazendo commit + push...
git add -f dados/tickets.db.gz
git add src\*.py scripts\*.py dashboard\*.py

REM Verifica se tem mudanca
git diff --cached --quiet
if errorlevel 1 (
    REM Tem mudanca
    set DATA=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%
    set DATA=%DATA: =0%
    git commit -m "sync: banco atualizado em %DATA%"
    git push origin main
    if errorlevel 1 (
        echo [ERRO] Push falhou!
        pause
        exit /b 1
    )
    echo.
    echo [OK] Push feito! Railway vai migrar em ~2 min.
) else (
    echo [AVISO] Nada a commitar
)

echo.
echo ============================================================
echo  CONCLUIDO!
echo ============================================================
echo.
echo Proximos passos:
echo   1. Aguarde ~2 min (Railway migra)
echo   2. Va no Streamlit Cloud e faca Reboot
echo   3. Abra o dashboard atualizado
echo.

pause