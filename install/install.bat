@echo off
REM ============================================================
REM  Lanceur de l'installateur glm
REM  Double-cliquez sur ce fichier pour installer glm.
REM ============================================================

title Installation de glm

REM Se placer dans le dossier de ce .bat
cd /d "%~dp0"

echo.
echo   Lancement de l'installateur glm...
echo.

REM Executer le script PowerShell en contournant la politique d'execution
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

echo.
echo   Appuyez sur une touche pour fermer cette fenetre...
pause >nul
