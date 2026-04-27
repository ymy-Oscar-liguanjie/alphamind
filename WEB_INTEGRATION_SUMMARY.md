# AlphaMind Web集成总结

## ✅ 已完成的工作

你的Python程序（多轮对话咨询系统）已成功集成到AlphaMind Web界面中！

### 🔧 新增文件

| 文件 | 说明 |
|------|------|
| **app_server.py** | Flask后端服务，暴露API接口 |
| **consultation.html** | Web版多轮对话咨询页面 |
| **DEPLOYMENT_GUIDE.md** | 完整的部署和API文档 |
| **start.bat** | 一键启动脚本（Windows） |

### 📝 已更新文件

| 文件 | 改进 |
|------|------|
| **requirements.txt** | 添加 Flask、Flask-CORS、python-dotenv |
| **llm_client.py** | 新增 `ask_llm_with_history()` 支持多轮对话 |
| **storage.py** | 新增会话管理函数（`create_session()`, `add_message()` 等） |

## 🚀 如何使用

### 方式1：一键启动（推荐）

**Windows用户：**
```bash
双击 start.bat
```

**或手动启动：**
```bash
python app_server.py
```

### 方式2：分步启动

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **配置 `.env` 文件**
```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://tdyun.ai
LLM_MODEL=claude-sonnet-4-6
```

3. **启动后端**
```bash
python app_server.py
```

4. **打开浏览器访问**
```
http://localhost:5000/consultation.html
```

## 🌐 系统架构

```
浏览器页面 (HTML/JS)
    ↓ HTTP API (fetch)
Flask后端服务 (Python)
    ↓
  ├─ LLM Client (多轮对话)
  ├─ Storage (SQLite数据库)
  └─ Model (风险预测)
```

## 💬 Web对话流程

### 用户操作
```
1. 打开 consultation.html
2. 输入用户ID
3. 与AI投顾进行对话
4. 点击"完成咨询"
5. 获取个性化建议
6. 导出建议文本
```

### 后端处理
```
POST /api/session/create
  ↓
返回 session_id + 初始问候
  ↓
POST /api/session/{id}/message (循环)
  ↓
返回投顾回复
  ↓
POST /api/session/{id}/finalize
  ↓
返回最终建议
```

## 📊 API接口

### 核心API

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/session/create` | 创建咨询会话 |
| POST | `/api/session/{id}/message` | 发送消息并获取回复 |
| POST | `/api/session/{id}/finalize` | 生成最终建议 |
| GET | `/api/session/{id}` | 获取会话详情 |
| GET | `/api/user/{id}/sessions` | 获取用户所有会话 |
| DELETE | `/api/session/{id}` | 删除会话 |
| GET | `/api/health` | 健康检查 |

## 📁 项目结构

```
gxb/
├── 核心程序
│   ├── app.py                           ← CLI版本
│   ├── app_server.py                    ← Flask后端 ✨
│   ├── llm_client.py                    ← LLM接口
│   ├── storage.py                       ← 数据存储
│   ├── model.py                         ← ML模型
│   └── portfolio.py                     ← 投资组合
│
├── Web前端
│   └── AlphaMind_Web1.1版，静态/
│       ├── consultation.html            ← 多轮对话 ✨
│       ├── assessment.html              ← 评测问卷
│       ├── result.html                  ← 结果展示
│       ├── survey.html                  ← 使用后问卷
│       └── ...
│
├── 配置文件
│   ├── requirements.txt                 ✨ 已更新
│   ├── .env                             ← 环境配置
│   ├── .gitignore
│   └── start.bat                        ✨ 新增
│
└── 文档
    ├── DEPLOYMENT_GUIDE.md              ✨ 新增
    ├── CONSULTATION_GUIDE.md
    └── README.md
```

## 🔍 详细功能说明

### 后端服务 (app_server.py)

**主要功能：**
- 会话管理（创建、查询、删除）
- 消息处理（保存对话历史）
- API路由（7个核心端点）
- 静态文件服务（HTML页面）
- CORS配置（跨域请求）

**技术实现：**
- Flask框架
- RESTful API设计
- JSON请求/响应
- 内存 + 数据库混合存储

### 前端页面 (consultation.html)

**用户界面：**
- 对话显示区（自动滚动到最新）
- 消息输入框（支持Shift+Enter换行）
- 按钮控制（发送、完成、重置）
- 实时状态显示

**交互特点：**
- 实时显示投顾回复
- 自动处理加载状态
- 消息计数提醒
- 异常错误处理
- 导出建议功能

## 🔄 对话流程演示

```
用户: 你好
投顾: 你好！我是你的专属投资顾问...

用户: 我有3年投资经验
投顾: 很好！那么你目前的风险承受能力如何...

用户: 我比较激进
投顾: 理解。你的投资周期是多长...

...（继续5-15轮）

用户: exit
系统: 生成最终建议...
投顾: [详细的投资建议报告]
```

## 🐛 故障排除

### 问题1：后端无法启动

**错误信息：**
```
ModuleNotFoundError: No module named 'flask'
```

**解决方案：**
```bash
pip install flask flask-cors python-dotenv
```

### 问题2：前端无法连接到后端

**检查项：**
1. 后端是否正在运行（`http://localhost:5000/api/health`）
2. 浏览器控制台是否有CORS错误
3. 防火墙是否阻止了5000端口

**解决方案：**
```bash
# 如果需要改端口，编辑app_server.py最后一行
app.run(debug=True, host='0.0.0.0', port=8000)

# 然后编辑consultation.html中的API_BASE
const API_BASE = 'http://localhost:8000/api';
```

### 问题3：.env文件不存在

**解决方案：**
```bash
# 手动创建.env文件
# 填入你的API配置
LLM_API_KEY=your_key
LLM_BASE_URL=https://tdyun.ai
LLM_MODEL=claude-sonnet-4-6
```

## 📈 数据流向

```
用户输入
    ↓
consultation.html (JavaScript)
    ↓
fetch API请求
    ↓
app_server.py (Flask)
    ↓
llm_client.py (ask_llm_with_history)
    ↓
Claude API (多轮对话)
    ↓
返回AI回复
    ↓
storage.py (保存到SQLite)
    ↓
返回JSON响应
    ↓
JavaScript更新页面
    ↓
用户看到回复
```

## ⚙️ 系统配置

### Flask服务器

```python
app.run(
    debug=True,           # 开发模式
    host='0.0.0.0',       # 监听所有网卡
    port=5000             # 端口
)
```

### CORS配置

```python
CORS(app)  # 允许所有来源的请求
```

### 请求超时

```
HTTP请求超时: 30秒
```

## 🚀 生产部署建议

### 使用Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app_server:app
```

### 使用Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app_server.py"]
```

构建和运行：
```bash
docker build -t alphamind .
docker run -p 5000:5000 -e LLM_API_KEY=your_key alphamind
```

## 📞 支持

**遇到问题？**

1. 查看浏览器控制台日志
2. 检查后端输出
3. 查看 DEPLOYMENT_GUIDE.md
4. 测试 API 端点

**测试API：**
```bash
# 健康检查
curl http://localhost:5000/api/health

# 创建会话
curl -X POST http://localhost:5000/api/session/create \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test"}'
```

## 📋 总结

✅ **已完成的集成：**
- ✨ Flask后端服务已创建
- ✨ Web对话页面已开发
- ✨ 数据库会话管理已集成
- ✨ API接口已暴露
- ✨ 静态文件服务已配置
- ✨ 文档完善

✨ **关键特性：**
- 完全异步的对话体验
- 实时消息同步
- 自动数据持久化
- 跨域请求支持
- 详细的错误处理

🎉 **现在你可以通过Web界面与AI投顾进行对话了！**

---

**下一步？**
```bash
python app_server.py
# 打开 http://localhost:5000/consultation.html
# 开始对话！
```
