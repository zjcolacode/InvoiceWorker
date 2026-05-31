#!/bin/bash

# InvoiceWorker 启动脚本

echo "🚀 启动 InvoiceWorker..."

# 获取脚本所在目录的父目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 启动后端
echo "📦 启动后端服务..."
cd "$PROJECT_DIR/backend"
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "✅ 后端服务已启动 (PID: $BACKEND_PID) - http://localhost:8000"

# 启动前端
echo "🎨 启动前端服务..."
cd "$PROJECT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
echo "✅ 前端服务已启动 (PID: $FRONTEND_PID) - http://localhost:5173"

echo ""
echo "========================================="
echo "  InvoiceWorker 已启动!"
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo "========================================="
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# 等待
wait
