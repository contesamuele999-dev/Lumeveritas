@echo off
setlocal
cd /d "%~dp0"

set "MSG=%*"
if "%MSG%"=="" set "MSG=chore: update"

git add -A
git diff --cached --quiet && (echo Niente da committare. & goto :end)

git commit -m "%MSG%" || goto :fail
git push origin main || goto :fail

echo.
echo Push OK -^> https://github.com/contesamuele999-dev/lumeveritas
goto :end

:fail
echo.
echo ERRORE: git ha fallito. Vedi sopra.

:end
pause
