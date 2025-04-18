@echo off
echo Ager - AI Coding Assistant
echo =========================
echo.

:: Set colors
set "CYAN=36"
set "GREEN=32"
set "YELLOW=33"
set "RED=31"
set "RESET=0"

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    call :colorEcho %RED% "Python not found! Please install Python 3.6 or later."
    echo.
    pause
    exit /b 1
)

:: Check if Ollama is running
python check_ollama.py
if %ERRORLEVEL% NEQ 0 (
    call :colorEcho %YELLOW% "Ollama is not running!"
    echo.
    call :colorEcho %YELLOW% "Please start Ollama and try again."
    echo.
    echo You can download Ollama from: https://ollama.ai/
    echo.
    pause
    exit /b 1
)

:menu
cls
echo Ager - AI Coding Assistant
echo =========================
echo.
call :colorEcho %CYAN% "Choose an option:"
echo.
echo 1. Start Chat Mode
echo 2. Start Agent Mode
echo 3. Start Claude Agent (API key required)
echo 4. Start Claude Agent with Local Model (no API key needed)
echo 5. Start Ager Pro Agent (Google API key or Ollama required)
echo 6. List Available Models
echo 7. Exit
echo.
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto chat
if "%choice%"=="2" goto agent
if "%choice%"=="3" goto claude
if "%choice%"=="4" goto claude_local
if "%choice%"=="5" goto ager_pro
if "%choice%"=="6" goto list_models
if "%choice%"=="7" goto end

echo Invalid choice. Please try again.
goto menu

:chat
cls
echo Starting Chat Mode...
echo.
call :colorEcho %CYAN% "Available models:"
echo.
python -c "from ager import get_available_models; print('\n'.join(['- ' + model for model in get_available_models()]))"
echo.
set /p model="Enter model name (or press Enter for default): "
call :colorEcho %GREEN% "Starting chat with streaming enabled..."
echo.
if "%model%"=="" (
    python ager.py --chat
) else (
    python ager.py --model %model% --chat
)
echo.
pause
goto menu

:agent
cls
echo Starting Agent Mode...
echo.
call :colorEcho %CYAN% "Available models:"
echo.
python -c "from ager import get_available_models; print('\n'.join(['- ' + model for model in get_available_models()]))"
echo.
set /p model="Enter model name (or press Enter for default): "
echo.
call :colorEcho %GREEN% "Starting agent..."
echo.
if "%model%"=="" (
    python ager.py --agent
) else (
    python ager.py --model %model% --agent
)
echo.
pause
goto menu

:claude
cls
echo Starting Claude Agent...
echo.
set /p model="Enter model name (optional, press Enter for default): "
echo.
call :colorEcho %GREEN% "Starting Claude Agent..."
echo.
if "%model%"=="" (
    python ager.py --claude_agent
) else (
    python ager.py --model %model% --claude_agent
)
echo.
pause
goto menu

:claude_local
cls
echo Starting Claude Agent with Local Model...
echo.
call :colorEcho %CYAN% "Available models:"
echo.
python -c "from ager import get_available_models; print('\n'.join(['- ' + model for model in get_available_models()]))"
echo.
set /p model="Enter model name (or press Enter for default): "
echo.
call :colorEcho %GREEN% "Starting Claude Agent with local model..."
echo.
if "%model%"=="" (
    python ager.py --claude_agent --local
) else (
    python ager.py --model %model% --claude_agent --local
)
echo.
pause
goto menu

:ager_pro
cls
echo Starting Ager Pro Agent...
echo.
set /p use_ollama="Use local Ollama model? (y/n, default=n): "
if /i "%use_ollama%"=="y" (
    call :colorEcho %CYAN% "Available models:"
    echo.
    python -c "from ager import get_available_models; print('\n'.join(['- ' + model for model in get_available_models()]))"
    echo.
    set /p model="Enter model name (or press Enter for default): "
    echo.
    call :colorEcho %GREEN% "Starting Ager Pro Agent with local model..."
    echo.
    if "%model%"=="" (
        python ager.py --ager_pro_agent --use-ollama
    ) else (
        python ager.py --model %model% --ager_pro_agent --use-ollama
    )
) else (
    call :colorEcho %GREEN% "Starting Ager Pro Agent with Gemini..."
    echo.
    python ager.py --ager_pro_agent
)
echo.
pause
goto menu

:list_models
cls
echo Available Models:
echo.
python ager.py --list-models
echo.
pause
goto menu

:end
echo Goodbye!
exit /b 0

:colorEcho
echo [%~1m%~2[0m
exit /b 