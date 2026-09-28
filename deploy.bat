@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================
echo   Email Management Agent - Deploy Script
echo   Windows CMD Edition
echo ============================================
echo.

:: Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed.
    echo Please install Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

echo [OK] Docker is installed and running.

:: Get project directory (where this script is located)
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"
echo [OK] Project directory: %PROJECT_DIR%

:: Check if .env exists, if not create from template
if not exist ".env" (
    echo.
    echo [1/5] Creating .env configuration...
    echo -----------------------------------------------------------
    echo  ENTER YOUR API CREDENTIALS
echo  (Leave blank and press Enter to skip optional services)
    echo -----------------------------------------------------------
    echo.

    set /p OPENAI_KEY="OpenAI API Key (required): "
    set /p GMAIL="Gmail address (required): "
    set /p GMAIL_APP_PASS="Gmail App Password (required): "
    set /p SLACK_TOKEN="Slack Bot Token (optional): "
    set /p NOTION_KEY="Notion API Key (optional): "
    set /p NOTION_DB="Notion Database ID (optional): "

    (
    echo # Email Agent Configuration
    echo OPENAI_API_KEY=%OPENAI_KEY%
    echo.
    echo # Gmail IMAP
    echo IMAP_HOST=imap.gmail.com
    echo IMAP_PORT=993
    echo IMAP_USER=%GMAIL%
    echo IMAP_PASSWORD=%GMAIL_APP_PASS%
    echo.
    echo # Slack (optional)
    echo SLACK_BOT_TOKEN=%SLACK_TOKEN%
    echo SLACK_ALERT_CHANNEL=#email-alerts
    echo.
    echo # Notion (optional)
    echo NOTION_API_KEY=%NOTION_KEY%
    echo NOTION_TASKS_DB=%NOTION_DB%
    ) > .env

    echo [OK] .env file created.
) else (
    echo [OK] .env file already exists.
)

:: Start services
echo.
echo [2/5] Starting Docker services...
docker compose up -d

if errorlevel 1 (
    echo [ERROR] Failed to start services.
    pause
    exit /b 1
)

echo [OK] Services started.

:: Wait for health
echo.
echo [3/5] Waiting for services to be healthy (30 seconds)...
timeout /t 30 /nobreak >nul

echo.
echo Current status:
docker compose ps

:: Initialize database
echo.
echo [4/5] Initializing database...
docker cp database/schema.sql email-agent-postgres:/schema.sql
docker exec -i email-agent-postgres psql -U n8n -d n8n -f /schema.sql >nul 2>&1

echo [OK] Database initialized.

:: Final status
echo.
echo ============================================
echo   DEPLOYMENT COMPLETE
echo ============================================
echo.
echo [5/5] Your Email Agent is running!
echo.
echo Access the services:
echo   n8n UI:        http://localhost:5678
echo   Username:      admin
echo   Password:      (from .env or docker-compose.yml)
echo   Qdrant:        http://localhost:6333
echo   PostgreSQL:    localhost:5432 (user: n8n)
echo   Redis:         localhost:6379
echo.
echo NEXT STEPS:
echo 1. Open http://localhost:5678 in your browser
echo 2. Sign in with admin credentials
echo 3. Go to Workflows - Import from File
echo 4. Select: n8n-workflows/email_agent_workflow.json
echo 5. Add your credentials (IMAP, OpenAI, Slack, Notion)
echo 6. Activate the workflow
echo.
echo To stop:   docker compose down
echo To start:  docker compose up -d
echo To test:   test.bat
echo.
pause
