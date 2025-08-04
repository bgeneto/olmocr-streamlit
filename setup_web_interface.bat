@echo off
setlocal enabledelayedexpansion

echo 🚀 olmOCR Web Interface Setup
echo =============================

REM Check prerequisites
echo 📋 Checking prerequisites...

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    echo    Visit: https://docs.docker.com/desktop/windows/install/
    pause
    exit /b 1
)

REM Check Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not available. Please ensure Docker Desktop is installed.
    pause
    exit /b 1
)

echo ✅ Prerequisites check completed!
echo.

REM Create workspace directory
echo 📁 Creating workspace directory...
if not exist workspace mkdir workspace
if not exist models mkdir models
echo ✅ Workspace created!
echo.

REM Build and start services
echo 🏗️  Building and starting services...
echo    This may take 5-10 minutes on first run...

docker-compose up -d --build

echo ✅ Services started!
echo.

REM Wait for vLLM server to be ready
echo ⏳ Waiting for vLLM server to load model...
echo    This can take 5-10 minutes depending on your internet connection and GPU...

set max_attempts=60
set attempt=0

:wait_loop
if !attempt! geq !max_attempts! goto timeout

curl -s -f http://localhost:30024/v1/models >nul 2>&1
if not errorlevel 1 (
    echo ✅ vLLM server is ready!
    goto ready
)

set /a attempt+=1
echo    Attempt !attempt!/!max_attempts! - Still loading...
timeout /t 10 /nobreak >nul
goto wait_loop

:timeout
echo ❌ vLLM server failed to start within expected time.
echo    Check logs with: docker-compose logs vllm-server
pause
exit /b 1

:ready
echo.
echo 🎉 Setup completed successfully!
echo.
echo 📱 Access the web interface at: http://localhost:8501
echo 🔧 vLLM server API at: http://localhost:30024
echo.
echo 📊 Monitor services:
echo    docker-compose logs -f          # All logs
echo    docker-compose logs vllm-server # vLLM server logs
echo    docker-compose logs streamlit-app # Streamlit app logs
echo.
echo 🛑 Stop services:
echo    docker-compose down
echo.
echo 💡 For troubleshooting, see WEB_INTERFACE_README.md
echo.
echo Press any key to open the web interface...
pause >nul
start http://localhost:8501
