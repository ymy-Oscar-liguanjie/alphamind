# AlphaMind Web版快速参考卡

## 📱 一句话说明
Python多轮对话程序已集成到Web界面，支持通过浏览器与AI投顾对话并获得投资建议。

## 🚀 最快启动方式

### Windows用户（最快）
```bash
双击 start.bat
# 或在PowerShell中
.\start.bat
```

### Mac/Linux用户
```bash
python app_server.py
```

### 然后打开浏览器
```
http://localhost:5000/consultation.html
```

---

## 🎯 核心功能对比

### ❌ 原始CLI版本（app.py）
```bash
python app.py
# → 选择菜单
# → 输入信息
# → 输出结果
```
- 命令行交互
- 需要手动选择菜单
- 不够直观

### ✅ 新的Web版本（app_server.py + consultation.html）
```
1. 打开浏览器访问 consultation.html
2. 输入用户ID
3. 自然对话（15轮以内）
4. 点击"完成咨询"
5. 获取个性化建议
```
- 图形化界面
- 实时聊天体验
- 专业美观

---

## 🔧 配置要求

### 必需
- ✅ Python 3.8+
- ✅ LLM API密钥（.env文件）
- ✅ 网络连接

### 可选
- 📱 现代浏览器（Chrome/Firefox/Edge）
- 🖥️ 本机访问或局域网访问

---

## 📂 新增文件一览

### 后端
```
app_server.py              Flask服务（用Python运行）
↓
/api/session/create        创建对话
/api/session/{id}/message  发送消息
/api/session/{id}/finalize 生成建议
```

### 前端
```
consultation.html          Web对话页面（浏览器打开）
├── 对话显示区
├── 消息输入框
├── 控制按钮
└── 状态面板
```

### 文档
```
DEPLOYMENT_GUIDE.md        完整部署指南 📖
WEB_INTEGRATION_SUMMARY.md 集成总结 📋
```

---

## 🌐 页面导航

| URL | 说明 |
|-----|------|
| `http://localhost:5000/` | 主页（assessment.html） |
| `http://localhost:5000/consultation.html` | 💬 **多轮对话** |
| `http://localhost:5000/assessment.html` | 📝 评测问卷 |
| `http://localhost:5000/result.html` | 📊 结果展示 |
| `http://localhost:5000/survey.html` | 📋 使用后问卷 |
| `http://localhost:5000/api/health` | 🏥 API健康检查 |

---

## 💬 对话示例

```
系统: 已创建咨询会话

投顾: 你好！我是你的专属投资顾问。很高兴认识你！
     能告诉我一下你是否有任何投资经验吗？

你:   我有5年的股票投资经验

投顾: 很好！5年的经验很有帮助。
     那么，你目前的风险承受能力如何？
     你更倾向于激进还是保守的投资？

你:   我比较激进，但也想有保障

投顾: 理解。那么你目前有多少闲钱可以用于投资呢？
     这个信息对制定适合你的投资方案很重要。

...（继续对话）

你:   exit

系统: 正在生成最终建议...

投顾: # 投资建议报告
     ## 基本信息
     - 风险等级：激进型
     - 资产配置：股票 65% | 债券 25% | 现金 10%
     
     ## 具体建议
     ...

系统: 建议已保存，可以导出
```

---

## 🔄 工作流程

```
┌─────────────────────┐
│  打开 consultation  │
│     .html           │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│   输入用户ID        │
│   点击"新建咨询"    │
└──────────┬──────────┘
           ↓
┌─────────────────────────────┐
│   API创建会话 + 初始问候    │
│   返回 session_id           │
└──────────┬──────────────────┘
           ↓
┌─────────────────────────────┐
│   用户输入消息              │
│   点击发送(→ 按钮)          │
└──────────┬──────────────────┘
           ↓
┌─────────────────────────────┐
│   API发送消息 + 获取回复    │
│   消息计数+1                │
└──────────┬──────────────────┘
           ↓
┌──────────────────────────────┐
│  消息显示在对话框             │
│  自动滚动到最新              │
│  重复2-4步（5-15轮）         │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│  用户输入"exit"             │
│  或点击"完成咨询"按钮       │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│  API生成最终建议            │
│  消息显示在对话框            │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│  用户点击"导出建议"         │
│  下载.txt文本文件           │
└──────────────────────────────┘
```

---

## 📊 数据流向

```
浏览器 (consultation.html)
   ↓ fetch POST/GET
Flask API (app_server.py)
   ↓ call function
Python程序 (llm_client + storage)
   ↓ HTTP request
LLM服务 (Claude API)
   ↓ response
Python程序
   ↓ save to DB
SQLite (alphamind.db)
   ↓ return JSON
Flask API
   ↓ return data
浏览器更新页面
```

---

## 🛠️ 常用命令

### 启动服务
```bash
# 方式1（推荐）
python app_server.py

# 方式2（生产环境）
gunicorn -w 4 -b 0.0.0.0:5000 app_server:app
```

### 测试API
```bash
# 健康检查
curl http://localhost:5000/api/health

# 创建会话
curl -X POST http://localhost:5000/api/session/create \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user"}'
```

### 查看日志
```bash
# Windows PowerShell
Get-Content -Tail 20 -Wait app.log

# Linux/Mac
tail -f app.log
```

---

## 🐛 快速排查

| 问题 | 检查项 | 解决方案 |
|------|--------|--------|
| 后端无法启动 | Flask是否安装 | `pip install flask flask-cors` |
| 前端无法连接 | 后端是否运行 | 打开 `http://localhost:5000/api/health` |
| API错误 | .env配置 | 检查 `LLM_API_KEY` 是否正确 |
| CORS错误 | 跨域设置 | app_server.py已配置CORS(app) |
| 数据未保存 | 数据库权限 | 检查 `alphamind.db` 是否可写 |

---

## 📈 性能指标

```
响应时间：2-5秒（等待LLM回复）
数据库：SQLite（自动创建）
内存占用：~50-100MB
并发连接：支持多用户同时咨询
```

---

## 🔐 安全提示

⚠️ **重要：**
- `.env` 文件不要提交到Git（.gitignore已配置）
- API密钥不要在公开场合暴露
- 生产环境使用HTTPS
- 定期备份SQLite数据库

---

## 📚 进阶功能

### 自定义系统提示词
编辑 `llm_client.py` 中的 `ADVISOR_SYSTEM_PROMPT`：
```python
ADVISOR_SYSTEM_PROMPT = """自定义你的投顾风格..."""
```

### 修改对话限制
编辑 `consultation.html` 中的最大轮数：
```javascript
const max_turns = 15;  // 改为你想要的轮数
```

### 改变后端端口
编辑 `app_server.py` 最后一行：
```python
app.run(debug=True, host='0.0.0.0', port=8000)
```

---

## 📞 获取帮助

1. **查看文档**
   - DEPLOYMENT_GUIDE.md - 部署指南
   - CONSULTATION_GUIDE.md - 使用指南
   - WEB_INTEGRATION_SUMMARY.md - 集成总结

2. **检查日志**
   - 浏览器控制台（F12）
   - 后端服务输出

3. **测试API**
   ```bash
   curl http://localhost:5000/api/health
   ```

---

## 🎓 学习路径

```
1. 阅读本快速参考卡 ← 你在这里
   ↓
2. 运行 start.bat 或 python app_server.py
   ↓
3. 打开浏览器访问 consultation.html
   ↓
4. 进行一次完整的对话测试
   ↓
5. 查看 DEPLOYMENT_GUIDE.md 了解细节
   ↓
6. 根据需要自定义和扩展
```

---

## ✅ 检查清单

在使用前确认：

- [ ] Python 3.8+ 已安装
- [ ] requirements.txt 已安装 (`pip install -r requirements.txt`)
- [ ] .env 文件已配置 LLM_API_KEY
- [ ] 网络连接正常
- [ ] 浏览器已打开 (Chrome/Firefox/Edge)
- [ ] 后端服务已启动 (`python app_server.py`)
- [ ] 可以访问 `http://localhost:5000/api/health`

✨ **准备就绪！开始咨询吧！**

---

## 🎉 总结

| 项目 | 说明 |
|------|------|
| **技术栈** | Python + Flask + SQLite + JavaScript |
| **功能** | 多轮对话咨询 + 实时建议生成 |
| **部署** | 本机运行 (localhost:5000) |
| **用户体验** | 专业Web界面 + 自然对话 |
| **数据存储** | SQLite本地数据库 |

**现在开始使用AlphaMind Web版吧！** 🚀
