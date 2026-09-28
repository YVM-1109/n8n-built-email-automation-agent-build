@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================
echo   Email Agent - Health Check
echo ============================================
echo.

cd /d "%~dp0"

echo [1/5] Checking Docker services...
docker compose ps

echo.
echo [2/5] Testing PostgreSQL...
docker exec -i email-agent-postgres psql -U n8n -d n8n -c "SELECT COUNT(*) FROM emails;" 2>nul
if errorlevel 1 (
    echo    [WARN] Database tables may not exist yet.
) else (
    echo    [OK] Database is accessible.
)

echo.
echo [3/5] Testing Redis...
docker exec -i email-agent-redis redis-cli ping 2>nul
if errorlevel 1 (
    echo    [WARN] Redis not responding.
) else (
    echo    [OK] Redis: PONG
)

echo.
echo [4/5] Testing Qdrant...
curl -s http://localhost:6333/healthz >nul 2>&1
if errorlevel 1 (
    echo    [WARN] Qdrant not responding.
) else (
    echo    [OK] Qdrant is healthy.
)

echo.
echo [5/5] Testing n8n...
curl -s -o nul -w "%%{http_code}" http://localhost:5678/healthz > temp.txt 2>nul
set /p STATUS=<temp.txt
del temp.txt 2>nul
if "%STATUS%"=="200" (
    echo    [OK] n8n is responding (HTTP 200).
) else (
    echo    [INFO] n8n UI at http://localhost:5678
echo.
)

echo.
echo ============================================
echo   TEST COMPLETE
echo ============================================
echo.
if all checks show [OK], your agent is ready.
echo Open http://localhost:5678 to configure workflows.
echo.
pause
