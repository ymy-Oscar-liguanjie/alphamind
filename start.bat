@echo off
REM AlphaMind Web系统启动脚本

echo.
echo ====================================================
echo    AlphaMind 投顾咨询系统启动脚本
echo ====================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [✓] Python已安装

REM 检查依赖是否已安装
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] 正在安装依赖...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [✓] 依赖检查完成

REM 检查.env文件
if not exist .env (
    echo.
    echo [!] 未找到.env文件，正在创建示例...
    (
        echo # LLM配置
        echo LLM_API_KEY=your_api_key_here
        echo LLM_BASE_URL=https://tdyun.ai
        echo LLM_MODEL=claude-sonnet-4-6
    ) > .env
    echo [!] 请编辑 .env 文件并填入你的API密钥
    pause
)

echo [✓] 环境配置就绪

echo.
echo ====================================================
echo    启动后端服务...
echo ====================================================
echo.
echo 📍 API地址: http://localhost:5000
echo 💬 咨询页面: http://localhost:5000/consultation.html
echo 📋 评测页面: http://localhost:5000/assessment.html
echo.
echo 按 Ctrl+C 停止服务
echo.

python app_server.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 服务启动失败
    pause
)
