@echo off
rem Gera o instalador do DIGEP (installer\output\DIGEP_Folha_de_Ponto_Setup.exe). Basta dar dois cliques.
chcp 65001 >nul
cd /d "%~dp0.."
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (
  echo Python nao encontrado. Instale o Python 3.11 ou mais novo: https://www.python.org/downloads/
  echo ^(marque "Add python.exe to PATH" na instalacao^) e de dois cliques neste arquivo de novo.
  echo.
  pause
  exit /b 1
)
%PY% installer\gerar_instalador.py %*
echo.
pause
