@echo off
echo Installing Ager Pro Agent dependencies...

:: Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.8 or higher.
    exit /b 1
)

:: Install base package in development mode
echo Installing Ager Pro Agent...
pip install -e . || (
    echo Failed to install base package.
    exit /b 1
)

:: Install Windows-specific dependencies
echo Installing Windows-specific dependencies...
pip install pyreadline3 || (
    echo Failed to install pyreadline3.
    echo You may encounter issues with line editing functionality.
)

:: Ask if user wants to install Gemini support
echo.
set /p gemini_support="Do you want to install Google Gemini support? (y/n): "
if /i "%gemini_support%"=="y" (
    echo Installing Google Gemini support...
    pip install google-generativeai || (
        echo Failed to install Google Generativeai.
        echo You won't be able to use Gemini models.
    )
    
    echo.
    echo To use Gemini models, you'll need to set up an API key.
    echo Visit: https://makersuite.google.com/app/apikey
    echo.
    echo After getting your API key, you can set it:
    echo - Via environment variable: set GOOGLE_API_KEY=your_key_here
    echo - Or in config.yaml in your home directory
)

:: Check if Ollama is installed (for local models)
where ollama > nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Ollama not found in PATH. For local models, you need to install Ollama.
    echo Visit: https://ollama.com/download
)

echo.
echo Installation completed!
echo To run Ager Pro Agent:
echo - With local model: ager --model llama3:8b --ager-pro-agent
echo - With Gemini model: ager --model gemini-pro --ager-pro-agent
echo. 