@echo off
REM Lanceur double-clic pour l'installation de GLM Code sur Windows.
REM Delegue le travail a install.ps1, dans la meme dossier.

setlocal
set "SCRIPT_DIR=%~dp0"

echo.
echo   GLM Code - installation
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install.ps1" %*
set "RESULT=%ERRORLEVEL%"

echo.
if "%RESULT%"=="0" (
    echo   Termine. Ouvre un nouveau terminal, puis lance : glm
) else (
    echo   L'installation a echoue ^(code %RESULT%^). Voir %TEMP%\glm-install.log
)
echo.
pause
exit /b %RESULT%
