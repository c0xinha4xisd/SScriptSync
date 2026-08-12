@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ======================================================
echo   SScriptSync v1 - Instalador (Windows)
echo ======================================================
echo.

where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 --version >nul 2>&1
  if %errorlevel% equ 0 (
    echo [OK] Usando: py -3
    py -3 "%~dp0install.py"
    goto :done
  )
)

where python >nul 2>&1
if %errorlevel% equ 0 (
  python --version >nul 2>&1
  if %errorlevel% equ 0 (
    echo [OK] Usando: python
    python "%~dp0install.py"
    goto :done
  )
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
  echo [OK] Usando Python 3.12 local
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%~dp0install.py"
  goto :done
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
  echo [OK] Usando Python 3.11 local
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%~dp0install.py"
  goto :done
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
  echo [OK] Usando Python 3.10 local
  "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" "%~dp0install.py"
  goto :done
)

echo.
echo [ERRO] Python 3.9+ NAO encontrado neste PC.
echo.
echo  1. https://www.python.org/downloads/  ^(Python 3.11 ou 3.12^)
echo  2. Marque: Add python.exe to PATH
echo  3. Marque: Install py launcher
echo  4. Feche o PowerShell, abra de novo
echo  5. Rode: install.bat
echo.
echo Ver docs/INSTALL.md no repositorio.
echo.
pause
exit /b 1

:done
echo.
pause
