@echo off
setlocal EnableDelayedExpansion

:: ============================================================
::  Ollama PDF RAG - Full Dependency Installer
::  Installs: Python packages, chat-ui (npm)
:: ============================================================

set "ROOT=%~dp0"
set "ERRORS=0"

call :header "Ollama PDF RAG - Installer"

:: ------------------------------------------------------------
:: 1. Copy .env if not present
:: ------------------------------------------------------------
call :section "Environment Setup"
if not exist "%ROOT%.env" (
    if exist "%ROOT%.env.example" (
        copy "%ROOT%.env.example" "%ROOT%.env" >nul
        call :ok ".env created from .env.example -- fill in your secrets before running"
    ) else (
        call :warn ".env.example not found, skipping .env creation"
    )
) else (
    call :ok ".env already exists"
)

:: ------------------------------------------------------------
:: 2. Python check
:: ------------------------------------------------------------
call :section "Python"
python --version >nul 2>&1
if errorlevel 1 (
    call :fail "Python not found. Install from https://www.python.org/downloads/ and re-run."
    set /a ERRORS+=1
    goto :node_check
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do call :ok "Found %%v"

:: ------------------------------------------------------------
:: 3. Virtual environment
:: ------------------------------------------------------------
call :section "Python Virtual Environment"
if not exist "%ROOT%venv\" (
    echo   Creating venv...
    python -m venv "%ROOT%venv"
    if errorlevel 1 (
        call :fail "Failed to create venv"
        set /a ERRORS+=1
        goto :pip_skip
    )
    call :ok "venv created at .\venv"
) else (
    call :ok "venv already exists"
)

:: ------------------------------------------------------------
:: 4. pip install requirements
:: ------------------------------------------------------------
call :section "Python Requirements"
echo   Installing from requirements.txt...
"%ROOT%venv\Scripts\pip.exe" install -r "%ROOT%requirements.txt" --quiet
if errorlevel 1 (
    call :fail "pip install failed"
    set /a ERRORS+=1
) else (
    call :ok "Python requirements installed"
)
goto :node_check

:pip_skip
call :warn "Skipped pip install (venv creation failed)"

:: ------------------------------------------------------------
:: 5. Node.js check
:: ------------------------------------------------------------
:node_check
call :section "Node.js"
node --version >nul 2>&1
if errorlevel 1 (
    call :fail "Node.js not found. Install from https://nodejs.org/ and re-run."
    set /a ERRORS+=1
    goto :done
)
for /f "tokens=*" %%v in ('node --version') do call :ok "Found Node.js %%v"

:: ------------------------------------------------------------
:: 6. chat-ui (npm)
:: ------------------------------------------------------------
call :section "chat-ui (npm)"
if not exist "%ROOT%chat-ui\package.json" (
    call :warn "chat-ui\package.json not found, skipping"
    goto :done
)
if not exist "%ROOT%chat-ui\.env.local" (
    if exist "%ROOT%chat-ui\.env.local.example" (
        copy "%ROOT%chat-ui\.env.local.example" "%ROOT%chat-ui\.env.local" >nul
        call :ok "chat-ui\.env.local created from example"
    )
)
echo   Running npm install in chat-ui...
pushd "%ROOT%chat-ui"
npm install --loglevel=error
if errorlevel 1 (
    call :fail "npm install failed in chat-ui"
    set /a ERRORS+=1
) else (
    call :ok "chat-ui dependencies installed"
)
popd

:: ------------------------------------------------------------
:: Done
:: ------------------------------------------------------------
:done
echo.
echo  ============================================================
if !ERRORS! == 0 (
    echo   [OK] All installations completed successfully.
    echo.
    echo   Next steps:
    echo     1. Edit .env with your secrets
    echo     2. Activate Python venv:   venv\Scripts\activate
    echo     3. Start chat-ui:          cd chat-ui ^&^& npm run dev
) else (
    echo   [!!] Completed with !ERRORS! error(s). Review output above.
)
echo  ============================================================
echo.
pause
endlocal
exit /b !ERRORS!

:: ============================================================
:: Helpers
:: ============================================================
:header
echo.
echo  ============================================================
echo    %~1
echo  ============================================================
echo.
goto :eof

:section
echo.
echo  ---- %~1 ----
goto :eof

:ok
echo   [OK] %~1
goto :eof

:warn
echo   [!!] %~1
goto :eof

:fail
echo   [FAIL] %~1
goto :eof
