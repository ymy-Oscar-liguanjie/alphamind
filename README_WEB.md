# AlphaMind Web集成版 - 快速使用指南

> 原项目已成功集成Web版本，支持通过浏览器与AI投顾进行多轮对话！

## ⚡ 最快启动（2分钟）

### Step 1: 准备环境
```bash
# 确保Python 3.8+已安装
python --version

# 安装依赖
pip install -r requirements.txt
```

### Step 2: 配置API密钥
```bash
# 编辑 .env 文件，添加
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://tdyun.ai
LLM_MODEL=claude-sonnet-4-6
```

### Step 3: 启动服务
```bash
# Windows用户：双击 start.bat
# 或手动运行
python app_server.py
```

### Step 4: 打开浏览器
```
http://localhost:5000/consultation.html
```

**就这么简单！** 🎉

---

## 📋 功能对比

| 功能 | CLI版 (app.py) | Web版 (app_server.py) |
|------|---|---|
| 交互方式 | 命令行菜单 | Web浏览器 |
| 用户体验 | 基础 | 专业现代 |
| 实时显示 | ❌ | ✅ |
| 消息历史 | 基础 | 完整记录 |
| 数据导出 | 文本 | 导出+分享 |
| 部署难度 | 简单 | 简单 |

---

## 🌐 Web界面功能

### 💬 多轮对话区
- 实时显示投顾回复
- 自动滚动到最新消息
- 时间戳记录
- 消息计数提醒

### 📝 控制按钮
- **新建咨询** - 创建新会话
- **发送** - 发送消息
- **完成咨询** - 生成最终建议
- **导出建议** - 下载建议文本

### 📊 状态面板
- 用户ID
- 会话ID
- 消息数
- 咨询状态

---

## 🔗 API端点

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/session/create` | 创建咨询会话 |
| POST | `/api/session/{id}/message` | 发送消息 |
| POST | `/api/session/{id}/finalize` | 生成最终建议 |
| GET | `/api/session/{id}` | 查询会话信息 |
| GET | `/api/user/{id}/sessions` | 用户会话列表 |
| GET | `/api/health` | 服务健康检查 |

---

## 📱 页面导航

```
http://localhost:5000/
├── /consultation.html      ← 💬 多轮对话（推荐）✨
├── /assessment.html        ← 📝 评测问卷
├── /result.html            ← 📊 结果展示
├── /survey.html            ← 📋 使用后问卷
└── /api/health             ← 🏥 健康检查
```

---

## 🎯 对话流程

```
用户: 你好，我是新投资者

投顾: 很高兴认识你！能告诉我你的投资经验吗？

用户: 我没有投资经验

投顾: 没关系！我们从基础开始。你现在有多少闲钱可以投资？

用户: 大概10万元

投顾: 很好。你对风险的态度如何？是想保守一点还是愿意承担风险？

用户: 我希望有收益但也不想太冒险

投顾: 理解。你的投资周期是多长？

...（继续5-15轮对话）

用户: exit

投顾: [生成详细的个性化投资建议]
```

---

## 💾 数据存储

所有数据自动保存到 `alphamind.db` SQLite数据库：

```
数据库结构:
├── chat (原始表)
│   └── user_id, question, answer, risk, portfolio, time
│
├── conversation_session (新增)
│   └── session_id, user_id, title, risk_level, ...
│
└── conversation_message (新增)
    └── message_id, session_id, role, content, timestamp, ...
```

---

## 🚀 进阶配置

### 修改服务端口

编辑 `app_server.py` 最后一行：
```python
app.run(debug=True, host='0.0.0.0', port=8000)  # 改为8000
```

然后编辑 `consultation.html`：
```javascript
const API_BASE = 'http://localhost:8000/api';  // 改为8000
```

### 修改对话限制

编辑 `consultation.html`:
```javascript
const max_turns = 20;  // 改为需要的轮数
```

### 自定义系统提示词

编辑 `llm_client.py`:
```python
ADVISOR_SYSTEM_PROMPT = """你的自定义提示词..."""
```

---

## 🐛 常见问题

### Q: 后端无法启动？
**A:** 检查依赖是否安装
```bash
pip install flask flask-cors python-dotenv
```

### Q: 前端无法连接后端？
**A:** 确保后端正在运行
```bash
# 测试API健康检查
curl http://localhost:5000/api/health
```

### Q: API密钥错误？
**A:** 检查 `.env` 文件配置是否正确
```bash
cat .env
```

### Q: 对话中间出错？
**A:** 查看浏览器控制台 (F12) 的错误信息

---

## 📚 相关文档

- **QUICK_REFERENCE.md** - 快速参考卡
- **DEPLOYMENT_GUIDE.md** - 完整部署指南
- **CONSULTATION_GUIDE.md** - 多轮对话使用指南
- **WEB_INTEGRATION_SUMMARY.md** - 集成技术总结

---

## 🎓 架构图

```
┌─────────────────────────────────────────┐
│         Web浏览器                        │
│  consultation.html (JavaScript)         │
└────────────────┬────────────────────────┘
                 │ HTTP API (JSON)
                 ↓
┌─────────────────────────────────────────┐
│      Flask后端服务                       │
│      (app_server.py)                    │
│  ├─ /api/session/create                 │
│  ├─ /api/session/{id}/message           │
│  └─ /api/session/{id}/finalize          │
└────────────┬────────────────────────────┘
             │
    ┌────────┼────────┐
    ↓        ↓        ↓
  LLM    Storage   Model
 Client  (SQLite)  (ML)
```

---

## ✅ 检查清单

启动前确认：

- [ ] Python 3.8+ 已安装
- [ ] `pip install -r requirements.txt` 已运行
- [ ] `.env` 文件已配置 API_KEY
- [ ] 网络连接正常
- [ ] 端口5000未被占用

---

## 📊 项目信息

```
项目名称: AlphaMind 智能投顾系统
核心功能: 多轮对话 + 风险评估 + 资产配置建议
技术栈: Python + Flask + SQLite + HTML5 + JavaScript
部署方式: 本地 (localhost:5000)
数据库: SQLite (alphamind.db)
LLM: Claude API (via tdyun.ai)
```

---

## 🎉 总结

✨ **你现在可以：**
1. 通过Web界面与AI投顾对话
2. 获取个性化投资建议
3. 导出建议文本
4. 查看对话历史
5. 支持多用户咨询

**立即开始吧！**

```bash
python app_server.py
# 打开 http://localhost:5000/consultation.html
```

---

**有问题？** 查看详细文档或检查浏览器控制台 (F12)
