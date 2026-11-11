@echo off
rem Gera o instalador do DIGEP (installer\output\DIGEP_Folha_de_Ponto_Setup.exe). Basta dar dois cliques.
chcp 65001 >nul
cd /d "%~dp0.."
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% installer\gerar_instalador.py %*
echo.
pause
