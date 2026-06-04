@echo off
echo ============================================
echo   Claude Notch for Windows — Installation
echo ============================================
echo.

:: Vérifie que Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Telecharge-le sur https://python.org puis relance ce script.
    pause
    exit /b 1
)

echo Installation des dependances...
pip install -r requirements.txt

echo.
echo Installation terminee !
echo.
echo Lancement de Claude Notch...
pythonw claude_notch.py

echo.
echo Si la fenetre ne s'ouvre pas, lance run.bat
pause
