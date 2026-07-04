@echo off
REM ============================================================
REM  Remise a zero + installation propre de glm
REM  Double-cliquez sur ce fichier.
REM ============================================================

title Remise a zero de glm

cd /d "%~dp0"

echo.
echo   Nettoyage des anciennes installations et reinstallation de glm...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nettoyer-et-installer.ps1"

echo.
echo   Appuyez sur une touche pour fermer cette fenetre...
pause >nul
