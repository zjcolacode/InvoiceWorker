# InvoiceWorker - 发票智能管理系统

基于 AI 的发票自动识别、管理和导出系统。

## 技术栈

### 后端
- Python 3.10+
- FastAPI
- SQLAlchemy
- DashScope (通义千问 OCR)

### 前端
- Vue 3 + TypeScript
- Vite
- Element Plus
- Pinia
- ECharts

## 快速开始

### 启动后端
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 启动前端
```bash
cd frontend
npm install
npm run dev
```

### 一键启动
```bash
./scripts/start.sh
```

## 项目结构

```
InvoiceWorker/
├── backend/          # 后端 FastAPI 服务
│   ├── app/
│   │   ├── api/      # API路由
│   │   ├── core/     # 核心配置
│   │   ├── models/   # 数据模型
│   │   ├── schemas/  # Pydantic模式
│   │   ├── services/ # 业务服务
│   │   └── tasks/    # 后台任务
│   └── storage/      # 文件存储
├── frontend/         # 前端 Vue 3 应用
│   └── src/
│       ├── api/      # API请求
│       ├── router/   # 路由配置
│       ├── stores/   # 状态管理
│       ├── views/    # 页面视图
│       └── utils/    # 工具函数
└── scripts/          # 脚本工具
```
