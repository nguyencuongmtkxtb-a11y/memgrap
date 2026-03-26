@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   Memgrap - One-Click Setup (Windows)
echo ============================================
echo.

:: Detect project root from this script location
set "MEMGRAP_DIR=%~dp0"
:: Remove trailing backslash
if "%MEMGRAP_DIR:~-1%"=="\" set "MEMGRAP_DIR=%MEMGRAP_DIR:~0,-1%"

echo [1/6] Checking prerequisites...

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

:: Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker not found. Install Docker Desktop from https://docker.com
    pause
    exit /b 1
)

echo       Python: OK
echo       Docker: OK
echo.

echo [2/6] Installing Python dependencies...
cd /d "%MEMGRAP_DIR%"
pip install -e . --quiet
if errorlevel 1 (
    echo ERROR: pip install failed
    pause
    exit /b 1
)
echo       Done.
echo.

echo [3/6] Starting Neo4j container...
docker compose up -d
if errorlevel 1 (
    echo ERROR: docker compose failed. Is Docker Desktop running?
    pause
    exit /b 1
)
echo       Waiting for Neo4j to be healthy...
:waitloop
timeout /t 3 /nobreak >nul
docker inspect --format="{{.State.Health.Status}}" memgrap-neo4j 2>nul | findstr "healthy" >nul
if errorlevel 1 goto waitloop
echo       Neo4j: healthy
echo.

echo [4/6] Generating .env file...
if not exist "%MEMGRAP_DIR%\.env" (
    copy "%MEMGRAP_DIR%\.env.example" "%MEMGRAP_DIR%\.env" >nul
    echo.
    echo *** IMPORTANT: Edit .env and add your OPENAI_API_KEY ***
    echo     File: %MEMGRAP_DIR%\.env
    echo.
    set /p "OPENAI_KEY=Enter OpenAI API key (or press Enter to skip): "
    if not "!OPENAI_KEY!"=="" (
        powershell -Command "(Get-Content '%MEMGRAP_DIR%\.env') -replace 'sk-proj-\.\.\.', '!OPENAI_KEY!' | Set-Content '%MEMGRAP_DIR%\.env'"
        echo       API key saved.
    ) else (
        echo       Skipped. Edit .env manually later.
    )
) else (
    echo       .env already exists, skipping.
)
echo.

echo [5/6] Configuring MCP for Claude Code...
:: Write project path to ~/.memgrap for hooks to discover
echo %MEMGRAP_DIR%> "%USERPROFILE%\.memgrap"

:: Read OPENAI_API_KEY from .env
set "OPENAI_KEY_VALUE="
if exist "%MEMGRAP_DIR%\.env" (
    for /f "tokens=1,* delims==" %%A in ('findstr /B "OPENAI_API_KEY" "%MEMGRAP_DIR%\.env"') do set "OPENAI_KEY_VALUE=%%B"
)

:: Write global MCP config (~/.claude/mcp.json) so it works in ALL projects
set "MCP_DIR=%USERPROFILE%\.claude"
if not exist "%MCP_DIR%" mkdir "%MCP_DIR%"
set "MCP_FILE=%MCP_DIR%\mcp.json"
set "ESCAPED_DIR=%MEMGRAP_DIR:\=/%"

:: Build JSON with env block
> "%MCP_FILE%" echo {
>> "%MCP_FILE%" echo   "mcpServers": {
>> "%MCP_FILE%" echo     "graphiti-memory": {
>> "%MCP_FILE%" echo       "command": "python",
>> "%MCP_FILE%" echo       "args": ["-m", "src.mcp_server"],
>> "%MCP_FILE%" echo       "cwd": "%ESCAPED_DIR%",
>> "%MCP_FILE%" echo       "env": {
>> "%MCP_FILE%" echo         "OPENAI_API_KEY": "!OPENAI_KEY_VALUE!"
>> "%MCP_FILE%" echo       }
>> "%MCP_FILE%" echo     }
>> "%MCP_FILE%" echo   }
>> "%MCP_FILE%" echo }
echo       Global MCP config written: %MCP_FILE%

:: Also keep project-level .mcp.json for backward compat
echo {> "%MEMGRAP_DIR%\.mcp.json"
echo   "mcpServers": {>> "%MEMGRAP_DIR%\.mcp.json"
echo     "graphiti-memory": {>> "%MEMGRAP_DIR%\.mcp.json"
echo       "command": "python",>> "%MEMGRAP_DIR%\.mcp.json"
echo       "args": ["-m", "src.mcp_server"]>> "%MEMGRAP_DIR%\.mcp.json"
echo     }>> "%MEMGRAP_DIR%\.mcp.json"
echo   }>> "%MEMGRAP_DIR%\.mcp.json"
echo }>> "%MEMGRAP_DIR%\.mcp.json"
echo       Project MCP config written.
echo.

echo [6/6] Verifying setup...
python -c "from src.config import get_settings; s = get_settings(); print(f'  Neo4j: {s.neo4j_uri}'); print(f'  OpenAI key: {\"configured\" if s.openai_api_key else \"MISSING - edit .env\"}')"
echo.

echo ============================================
echo   Setup complete!
echo   Restart Claude Code to activate Memgrap.
echo ============================================
if not exist "%MEMGRAP_DIR%\.env" echo   WARNING: .env file missing - copy .env.example
echo.
pause
