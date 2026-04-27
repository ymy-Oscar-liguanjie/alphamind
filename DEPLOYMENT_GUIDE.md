# AlphaMind Web集成部署指南

## 项目架构

```
┌─────────────────────────────────────────┐
│         Web前端页面 (HTML/JS)           │
│  ┌─────────────────────────────────┐   │
│  │ assessment.html (评测问卷)      │   │
│  │ consultation.html (多轮对话)    │   │
│  │ result.html (结果展示)          │   │
│  │ survey.html (使用后问卷)        │   │
│  └─────────────────────────────────┘   │
└────────────────┬────────────────────────┘
                 │ HTTP API (fetch)
                 ↓
┌─────────────────────────────────────────┐
│     Flask后端API (app_server.py)        │
│  /api/session/create                    │
│  /api/session/{id}/message              │
│  /api/session/{id}/finalize             │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ↓            ↓            ↓
┌────────┐ ┌──────────┐ ┌──────────┐
│ LLM    │ │ Storage  │ │ Model    │
│ Client │ │ (SQLite) │ │ (ML)     │
└────────┘ └──────────┘ └──────────┘
```

## 快速开始

### 1️⃣ 安装依赖

```bash
# 进入项目目录
cd "c:\Users\wille\Desktop\实验室数据\gxb"

# 安装Python依赖
pip install -r requirements.txt
```

### 2️⃣ 配置环境变量

创建或更新 `.env` 文件：

```env
# LLM配置
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://tdyun.ai
LLM_MODEL=claude-sonnet-4-6

# Flask配置（可选）
FLASK_ENV=development
FLASK_DEBUG=True
```

### 3️⃣ 启动后端服务

```bash
python app_server.py
```

你应该看到：
```
==================================================
AlphaMind API Server 启动中...
==================================================
📍 地址: http://localhost:5000
📋 API文档:
   - POST /api/session/create - 创建会话
   - POST /api/session/<id>/message - 发送消息
   - POST /api/session/<id>/finalize - 生成最终建议
   - GET  /api/session/<id> - 获取会话信息
   - GET  /api/user/<id>/sessions - 用户会话列表
==================================================
```

### 4️⃣ 访问Web界面

在浏览器中打开：

```
http://localhost:5000/consultation.html
```

或访问其他页面：

```
http://localhost:5000/assessment.html        （评测问卷）
http://localhost:5000/result.html            （结果展示）
http://localhost:5000/survey.html            （使用后问卷）
```

## 功能说明

### 📋 评测问卷（assessment.html）
- 用户填写基础信息和投资问卷
- 系统生成风险等级和建议

### 💬 多轮对话咨询（consultation.html）**新增**
- 与AI投顾进行自然对话
- 逐步了解用户的投资需求
- 自动生成个性化投资建议
- 支持导出建议文本

### 📊 结果展示（result.html）
- 显示评测结果和雷达图
- 展示资产配置建议
- 多角色观点分析

### 📝 使用后问卷（survey.html）
- 收集用户体验反馈
- 数据保存到管理后台

## API文档

### 1. 创建咨询会话

**请求：**
```bash
POST /api/session/create
Content-Type: application/json

{
  "user_id": "user_001"
}
```

**响应：**
```json
{
  "success": true,
  "session_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "initial_message": "你好！我是你的专属投资顾问..."
}
```

### 2. 发送消息

**请求：**
```bash
POST /api/session/{session_id}/message
Content-Type: application/json

{
  "user_id": "user_001",
  "message": "我有3年的投资经验"
}
```

**响应：**
```json
{
  "success": true,
  "reply": "很好！3年的经验很有帮助...",
  "message_count": 3
}
```

### 3. 生成最终建议

**请求：**
```bash
POST /api/session/{session_id}/finalize
Content-Type: application/json

{
  "user_id": "user_001"
}
```

**响应：**
```json
{
  "success": true,
  "final_advice": "# 投资建议报告\n\n## 风险等级\n...",
  "session_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### 4. 获取会话信息

**请求：**
```bash
GET /api/session/{session_id}
```

**响应：**
```json
{
  "success": true,
  "session_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "user_id": "user_001",
  "message_count": 8,
  "created_at": "2026-04-27T12:00:00",
  "messages": [...]
}
```

### 5. 获取用户所有会话

**请求：**
```bash
GET /api/user/{user_id}/sessions
```

**响应：**
```json
{
  "success": true,
  "sessions": [
    {
      "session_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "title": "Web咨询-20260427120000",
      "risk_level": "激进型",
      "updated_at": "2026-04-27T12:30:00"
    }
  ]
}
```

## 使用流程

### 方式1：多轮对话咨询（推荐）

```
1. 打开 consultation.html
2. 输入用户ID（或使用默认）
3. 与投顾进行自然对话（5-15轮）
4. 点击"完成咨询"
5. 获取个性化建议
6. 导出建议文本
```

### 方式2：快速评测

```
1. 打开 assessment.html
2. 填写问卷
3. 提交自动分析
4. 查看 result.html 结果
5. 可选：参加使用后问卷
```

## 数据存储

所有数据存储在 SQLite 数据库中：

**数据库文件：** `alphamind.db`

**表结构：**

1. **chat** - 原有会话记录
   - user_id, question, answer, risk, portfolio, time

2. **conversation_session** - 新增咨询会话
   - session_id, user_id, title, risk_level, portfolio_json, created_time, updated_time

3. **conversation_message** - 新增对话消息
   - message_id, session_id, user_id, message_type, role, content, timestamp

## 常见问题

**Q：后端无法启动？**

A：检查以下内容：
1. 确保安装了所有依赖：`pip install -r requirements.txt`
2. 检查 `.env` 文件中的 API_KEY 配置
3. 确保端口 5000 未被占用
4. 查看是否有其他错误信息

**Q：前端页面无法连接到后端？**

A：
1. 确保后端服务正在运行
2. 检查浏览器控制台是否有错误
3. 确保跨域设置正确（已在 Flask 中配置 CORS）
4. 检查防火墙是否阻止了连接

**Q：如何修改后端端口？**

A：编辑 `app_server.py` 最后一行：
```python
app.run(debug=True, host='0.0.0.0', port=8000)  # 改为 8000
```

然后在前端 `consultation.html` 中修改：
```javascript
const API_BASE = 'http://localhost:8000/api';  // 改为 8000
```

**Q：如何在生产环境部署？**

A：建议使用 Gunicorn：
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app_server:app
```

或使用 Docker：
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app_server.py"]
```

## 技术栈

- **前端**：HTML5 + Vanilla JavaScript + CSS3
- **后端**：Flask + Flask-CORS
- **数据库**：SQLite3
- **LLM**：Claude API（通过 tdyun.ai）
- **依赖管理**：pip + requirements.txt

## 项目文件结构

```
gxb/
├── app.py                                 # 原始CLI程序
├── app_server.py                          # Flask后端服务 ✨ 新增
├── llm_client.py                          # LLM接口（支持多轮对话）
├── storage.py                             # 数据存储（支持会话管理）
├── model.py                               # 风险预测模型
├── portfolio.py                           # 投资组合生成
├── requirements.txt                       # Python依赖 ✨ 已更新
│
├── AlphaMind_Web1.1版，静态/
│   ├── consultation.html                  # 多轮对话页面 ✨ 新增
│   ├── assessment.html                    # 评测问卷页
│   ├── result.html                        # 结果展示页
│   ├── survey.html                        # 使用后问卷页
│   ├── admin_login.html                   # 管理员登录页
│   ├── admin_dashboard.html               # 管理员仪表板
│   └── alphamind_logo.png                 # 品牌logo
│
├── .env                                   # 环境变量配置
├── alphamind.db                           # SQLite数据库
└── CONSULTATION_GUIDE.md                  # 多轮对话指南
```

## 测试API

可使用 curl 或 Postman 测试 API：

```bash
# 创建会话
curl -X POST http://localhost:5000/api/session/create \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user"}'

# 发送消息
curl -X POST http://localhost:5000/api/session/{session_id}/message \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","message":"你好"}'

# 健康检查
curl http://localhost:5000/api/health
```

## 支持

遇到问题？
1. 查看 `console.log` 输出（浏览器开发者工具）
2. 检查后端日志
3. 查看 SQLite 数据库内容
4. 测试 API 端点是否正常

---

**现在你可以通过Web界面与AI投顾进行对话了！** 🎉
