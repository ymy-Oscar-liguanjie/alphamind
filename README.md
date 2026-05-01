# AlphaMind

AlphaMind 是一个基于机器学习模型与大语言模型（LLM）协同的智能投顾系统原型，用于实现用户风险评估、资产配置建议、智能对话、图片识别与浏览器语音输入。

---

## 一、项目简介

本项目在原有 M1-M6 投顾模型基础上，引入网页端交互系统和 Claude 大语言模型，实现从命令行投顾程序到类 ChatGPT 智能投顾网页应用的升级。

系统支持用户通过自然语言、图片和浏览器语音输入投资相关问题，并结合风险评估模型、资产配置模型和 LLM 生成可解释的投资建议。

---

## 二、核心功能

- 用户注册 / 登录
- 一问一答 风格对话界面
- 历史会话保存
- 会话删除
- 多轮上下文对话
- M3 风险预测
- M4 资产配置推荐
- 图片上传识别
- 图片显示在聊天记录中
- 图片识别结果进入上下文
- 拖拽上传图片
- 浏览器原生语音识别
- Markdown 渲染
- 代码块样式与复制按钮
- AI 思考动画
- 打字机输出效果
- 深色黑红橙主题界面

---

## 三、系统架构

整体流程：

```text
用户输入（文字 / 图片 / 浏览器语音）
        ↓
网页端 Flask 服务
        ↓
SQLite 用户与会话存储
        ↓
M2 用户特征读取
        ↓
M3 风险预测模型
        ↓
M4 资产配置模型
        ↓
LLM 生成解释性投顾回复
        ↓
网页端展示结果
```

---

## 四、核心模块

### 1. M1 数据生成

`M1_data_prep.py`

用于生成用户画像、市场数据、交易记录和对话数据。

### 2. M2 特征工程

`M2_features_and_split.py`

用于从 M1 数据中提取用户特征，并生成训练集、测试集和全量特征表。

### 3. M3 风险预测模型

`M3_fedavg_risk_model.py` / `model.py`

用于训练和加载风险预测模型，并输出风险概率。

### 4. M4 资产配置模型

`M4_portfolio_recommender.py` / `portfolio.py`

基于风险预测结果生成资产配置方案。

### 5. M5 可解释性报告

`M5_explainability_report.py`

用于分析特征重要性并生成解释性投顾报告。

### 6. 网页端系统

`web_app.py`

Flask 网页服务入口，包含：

- 登录注册
- 智能聊天
- 会话保存
- 图片上传
- M3/M4 分析接口
- SQLite 存储

### 7. LLM 调用模块

`llm_client.py`

负责调用 Claude 或其他兼容 OpenAI Chat Completions 格式的模型接口。

### 8. 图片识别模块

`ai_media_client.py`

负责图片识别接口调用。

### 9. 前端页面

`templates/`

包含：

- `login.html`
- `register.html`
- `chat.html`

### 10. 静态资源

`static/`

包含：

- `style.css`
- `alphamind_logo.png`

---

## 五、项目结构

```text
AlphaMind/
│
├─ web_app.py
├─ app.py
├─ llm_client.py
├─ ai_media_client.py
├─ model.py
├─ portfolio.py
├─ storage.py
│
├─ M1_data_prep.py
├─ M2_features_and_split.py
├─ M3_fedavg_risk_model.py
├─ M4_portfolio_recommender.py
├─ M5_explainability_report.py
├─ M6_ui.py
│
├─ templates/
│   ├─ login.html
│   ├─ register.html
│   └─ chat.html
│
├─ static/
│   ├─ style.css
│   └─ alphamind_logo.png
│
├─ uploads/
├─ work/
├─ outputs/
│
├─ requirements.txt
├─ .env
└─ README.md
```

---

## 六、安装依赖

在项目根目录运行：

```powershell
pip install -r requirements.txt
```

如使用一键启动版，可直接双击：

```text
start.bat
```

一键启动版会自动创建虚拟环境并安装依赖。

---

## 七、环境变量配置

在项目根目录创建 `.env` 文件：

```env
LLM_API_KEY=你的API_KEY
LLM_BASE_URL=https://tdyun.ai
LLM_MODEL=claude-opus-4-6

VISION_MODEL=claude-opus-4-6
```

说明：

```text
LLM_API_KEY     大模型 API Key
LLM_BASE_URL    中转站或模型服务地址
LLM_MODEL       普通聊天模型
VISION_MODEL    图片识别模型
```

浏览器语音识别使用 Chrome / Edge 原生能力，不需要 `ASR_MODEL`，也不需要 `whisper-1`。

---

## 八、启动网页系统

```powershell
python web_app.py
```

浏览器打开：

```text
http://127.0.0.1:5000
```

---

## 九、推荐运行流程

### 1. 生成数据

```powershell
python M1_data_prep.py
```

### 2. 生成特征

```powershell
python M2_features_and_split.py
```

### 3. 训练风险模型

```powershell
python M3_fedavg_risk_model.py
```

### 4. 生成资产配置

```powershell
python M4_portfolio_recommender.py
```

### 5. 启动网页

```powershell
python web_app.py
```

如果 `work/` 目录下缺少模型或特征文件，系统会使用默认用户画像和默认资产配置兜底，不会影响网页启动。

---

## 十、使用方式

### 登录 / 注册

首次访问网页后，先注册账号，再登录进入聊天页面。

### 智能对话

直接输入投资问题，例如：

```text
我35岁，年收入30万，有80万资产，想做稳健投资，应该怎么配置？
```

### 图片识别

可以点击“图片识别”上传图片，也可以把图片拖拽到聊天窗口中。

### 浏览器语音识别

点击“开始语音”，浏览器会请求麦克风权限。说话后文字会自动进入输入框。

注意：建议使用 Chrome 或 Edge。

---

## 十一、常见问题

### 1. 图片识别提示 No available accounts

这是中转站账号池临时不可用。系统会自动重试，如仍失败，稍后重试即可。

### 2. 图片识别提示格式不匹配

系统已根据图片真实文件头判断 MIME 类型，避免 JPEG 被误判成 PNG。

### 3. 语音识别不能用

浏览器原生语音识别依赖 Chrome / Edge。部分浏览器可能不支持。

### 4. 为什么不用 whisper-1？

当前版本使用浏览器原生语音识别，不走 API，不耗 token，也不需要语音模型。

### 5. 网页能打开但 AI 不回复

检查 `.env` 中：

```env
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

是否正确。

---

## 十二、后续优化方向

- 引入真实用户数据
- 增强用户画像填写表单
- 增加管理员后台
- 增加 PDF / Excel / Word 文件分析
- 增加行情数据接入
- 增加报告导出
- 部署到服务器并配置 HTTPS
- 接入企业微信 / 小程序
