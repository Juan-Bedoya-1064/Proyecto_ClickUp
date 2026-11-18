@echo off
REM ==============================================================
REM  Sprint 1 · Acceso y usuarios — arranque en Windows (XAMPP)
REM  1) Abre XAMPP y pulsa Start en MySQL.
REM  2) Doble clic en este archivo.
REM ==============================================================
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py -3) || (set PY=python)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual .venv ...
    %PY% -m venv .venv || goto :error
)

echo Instalando dependencias (solo tarda la primera vez) ...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt || goto :error

if not exist ".env" copy ".env.example" ".env" >nul

".venv\Scripts\python.exe" run.py
pause
exit /b 0

:error
echo.
echo Algo fallo. Revisa que tengas Python 3.10 o superior instalado (python.org)
echo y marcada la opcion "Add Python to PATH".
pause
exit /b 1
