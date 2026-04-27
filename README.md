# AlphaMind

AlphaMind 是一个基于机器学习与大语言模型（LLM）协同的智能投顾系统原型，用于实现用户风险评估与资产配置建议的自动生成。

---

## 一、项目简介

本项目在原有机器学习投顾模型基础上，引入 Claude 大语言模型，实现从“静态模型”到“智能交互系统”的升级。

系统支持用户通过自然语言输入投资需求，自动完成风险评估、资产配置，并生成可解释的投资建议。

---

## 二、系统架构

系统整体流程如下：

用户输入（自然语言）  
↓  
LLM（Claude）解析用户意图  
↓  
风险评估模型（随机森林）  
↓  
资产配置模型（均值方差优化）  
↓  
LLM生成投资建议解释  
↓  
数据存储（SQLite）

---

## 三、核心模块

### 1. 风险评估模型（M3）
- 使用 RandomForestClassifier
- 输入用户画像与行为特征
- 输出风险等级（保守 / 稳健 / 激进）

---

### 2. 资产配置模型（M4）
- 基于均值方差优化方法
- 根据风险等级生成资产分配比例

---

### 3. 大语言模型（LLM）
- 使用 Claude API
- 负责：
  - 用户输入理解
  - 投资建议解释生成
  - 对话交互能力

---

### 4. 数据存储
- 使用 SQLite 数据库
- 存储：
  - 用户历史输入
  - 风险评估结果
  - 投资建议记录

---

## 四、运行方式（Windows / PowerShell）

### 1. 安装依赖

```powershell
pip install -r requirements.txt
pip install python-dotenv
```

## 2. 运行环境
```pwershell
$env:ANTHROPIC_AUTH_TOKEN="你的API_KEY"
$env:ANTHROPIC_BASE_URL="链接"
$env:LLM_MODEL="模型"
```
## 3. 启动
```powershell
python app.py
```

---

## 五、 实列
输入
```Bsah
月入百万，有车有房，非常想梭哈
```
---

## 六、 项目特点

 机器学习 + LLM 协同架构
 
 支持自然语言交互
 
 可解释的投资建议
 
 模块化设计（M1 ~ M6）
 
 可扩展（支持多模型接入）
 
 ---

 ## 七、 项目结构
 
M1_data_prep.py              数据生成

M2_features_and_split.py     特征工程

M3_fedavg_risk_model.py      风险模型（核心）

M4_portfolio_recommender.py  资产配置

M5_explainability_report.py  解释模块

M6_ui.py                     用户界面

app.py                       主程序入口（新版）

llm_client.py                LLM调用模块

storage.py                   数据存储模块

--- 
## 八、 项目结构

后续优化方向

引入真实用户数据

增强多轮对话能力

支持网页端 / 小程序

引入行为分析与动态画像

多模态输入（语音 / OCR）




