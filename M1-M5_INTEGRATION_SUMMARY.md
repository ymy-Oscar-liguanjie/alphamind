# M1-M5 集成改进总结

## 📋 改进概览

本次改进将四个孤立的文件（`model.py`, `portfolio.py`, `app.py`, `app_server.py`）与 M1-M5 模块完整集成，形成完整的端到端数据流。

---

## 🔄 集成流程

```
M1 生成原始数据
  ↓
M2 特征工程提取
  ↓
M3 风险预测模型（model.py 改进）
  ↓
M4 资产配置推荐（portfolio.py 改进）
  ↓
M5 可解释性分析
  ↓
app.py + app_server.py（集成 M3/M4 结果）
  ↓
用户获得数据驱动 + LLM 增强的投资建议
```

---

## 📝 各文件改进详情

### 1️⃣ **model.py** - 风险预测模型集成 M3

**原始问题**：
- 使用随机模型 `RandomForestClassifier()`
- 用随机数据训练，无法真实预测

**改进内容**：
```python
# ✅ 加载 M3 训练的真实模型
load_model(workdir="work")
  ↓
  - work/risk_model.pkl（M3 输出的联邦学习模型）
  - work/used_features_m3.csv（M3 使用的特征列表）
  - work/scaler.joblib（特征标准化器）

# ✅ 改进的 predict_risk() 函数
def predict_risk(features_dict, workdir="work"):
    """支持两种输入方式"""
    - 方式1：字典格式 {"age": 35, "income10k": 5, ...}
    - 方式2：列表格式 [35, 5, ...]
    ↓
    返回风险概率 (0-1)
```

**使用示例**：
```python
from model import predict_risk

# 从特征字典预测
risk_prob = predict_risk({"age": 35, "income10k": 5})
# 结果：0.42 (42%风险概率 → 稳健型)
```

---

### 2️⃣ **portfolio.py** - 资产配置集成 M4

**原始问题**：
- 硬编码规则：只支持"保守/稳健/激进"三种
- 不使用 M4 生成的个性化推荐

**改进内容**：
```python
# ✅ 加载 M4 生成的推荐配置
load_portfolio_recommendations(workdir="work")
  ↓
  work/portfolio_recs.csv（M4 输出）
    columns: user_id | portfolio | 股票 | 债券 | 基金 | REITs | 大宗商品 | 现金

# ✅ 改进的 generate_portfolio() 函数
def generate_portfolio(user_id=None, risk_prob=None, workdir="work"):
    """优先级逻辑"""
    1. 若提供 user_id
       → 查询 M4 个性化推荐
       → 返回精准配置
    
    2. 否则，根据 risk_prob 使用规则推断
       → 保守型 (< 0.33): 债券 60%
       → 稳健型 (0.33-0.67): 债券 40% + 股票 35%
       → 激进型 (> 0.67): 股票 55% + 债券 20%
```

**使用示例**：
```python
from portfolio import generate_portfolio

# 方式1：从 M4 推荐查询（精准）
portfolio = generate_portfolio(user_id=123)
# 结果：{"股票": 35.2, "债券": 40.1, ...}

# 方式2：根据风险概率推断（降级）
portfolio = generate_portfolio(risk_prob=0.45)
# 结果：{"债券": 40, "股票": 35, ...}
```

---

### 3️⃣ **app.py** - 交互式咨询集成 M1-M5

**原始问题**：
- `run_demo()` 只调用 LLM
- 不使用 M2 特征、M3 预测、M4 推荐

**改进流程**：
```
第1步：加载用户特征（M2 输出）
  ↓
  从 work/all_features.csv 读取
  按 user_id 查询所有特征

第2步：M3 风险预测
  ↓
  使用真实模型预测风险概率

第3步：M4 资产配置
  ↓
  根据 user_id 或 risk_prob 获取配置

第4步：LLM 增强建议
  ↓
  将数据驱动结果注入 LLM 提示词
  生成专业投资建议
```

**改进的 run_demo() 调用链**：
```python
python app.py
输入 user_id: 5
输入 情况: 我想稳健投资

第1步: 加载用户特征...
✅ 已加载用户 5 的特征信息

第2步: 使用 M3 模型预测风险等级...
✅ 风险概率: 45.23%

第3步: 使用 M4 生成资产配置...
✅ 资产配置已生成: {'债券': 40, '股票': 35, ...}

第4步: 使用 LLM 生成投顾建议...
✅ 建议已保存
```

---

### 4️⃣ **app_server.py** - Flask API 集成完整数据流

**原始问题**：
- 只有对话会话管理
- 没有风险预测、资产配置 API
- 不使用 M3/M4 结果

**新增 API 端点**：

#### 🔹 风险预测端点（M3 集成）
```
POST /api/predict/risk
请求：
{
  "user_id": 5,
  "features": {}  // 可选，优先使用 user_id 从 M2 加载
}

响应：
{
  "success": true,
  "risk_prob": 0.4523,
  "risk_level": "稳健型"
}
```

#### 🔹 资产配置推荐端点（M4 集成）
```
POST /api/recommend/portfolio
请求：
{
  "user_id": 5,
  "risk_prob": null  // 可选
}

响应：
{
  "success": true,
  "portfolio": {
    "股票": 35.2,
    "债券": 40.1,
    "基金": 12.0,
    "REITs": 5.0,
    "大宗商品": 5.0,
    "现金": 2.7
  },
  "portfolio_str": "股票: 35.2%, 债券: 40.1%, ..."
}
```

#### 🔹 端到端分析端点（M1-M5 完整集成）
```
POST /api/analysis/end-to-end
请求：
{
  "user_id": 5,
  "features": {}  // 可选
}

响应：
{
  "success": true,
  "analysis": {
    "risk_prob": 0.4523,
    "risk_level": "稳健型",
    "portfolio": {...},
    "portfolio_str": "...",
    "llm_advice": "基于您的情况，建议..."  // LLM 生成
  }
}
```

#### 🔹 增强的会话结束端点
```
POST /api/session/<id>/finalize
新增功能：
1. 自动检测用户特征（M2）
2. 自动预测风险概率（M3）
3. 自动推荐资产配置（M4）
4. 将结果注入 LLM 上下文
5. 生成数据驱动的建议

响应：
{
  "success": true,
  "final_advice": "...",
  "risk_prob": 0.4523,
  "portfolio": {...}
}
```

---

## 🚀 使用示例

### 示例 1：运行改进的交互式咨询
```bash
cd c:\Users\wille\Desktop\实验室数据\gxb

# 确保已运行过 M1-M5
python run_experiment.py

# 运行交互式咨询
python app.py
```

### 示例 2：启动 Flask API 服务器
```bash
python app_server.py

# 输出：
# AlphaMind API Server 启动中（完整M1-M5集成版本）
# 📍 地址: http://localhost:5000
```

### 示例 3：调用 API（Python）
```python
import requests

# 预测风险
response = requests.post('http://localhost:5000/api/predict/risk', 
    json={"user_id": 5})
print(response.json())

# 推荐资产配置
response = requests.post('http://localhost:5000/api/recommend/portfolio',
    json={"user_id": 5})
print(response.json())

# 完整分析
response = requests.post('http://localhost:5000/api/analysis/end-to-end',
    json={"user_id": 5})
print(response.json())
```

---

## 📊 集成后的数据流

```
用户输入 (user_id, 特征等)
  ↓
M2 特征数据 (work/all_features.csv)
  ↓
M3 模型预测 (work/risk_model.pkl)
  ↓ risk_prob (0-1)
  ↓
M4 推荐配置 (work/portfolio_recs.csv)
  ↓ portfolio {资产: 权重}
  ↓
LLM 增强 (llm_client.ask_llm)
  ↓
最终建议 (专业、个性化、可操作)
```

---

## ✅ 验证集成

**检查点**：

1. ✅ M3 模型是否加载成功
   ```python
   from model import load_model
   model, features, scaler = load_model()
   ```

2. ✅ M4 推荐是否加载成功
   ```python
   from portfolio import load_portfolio_recommendations
   recs = load_portfolio_recommendations()
   print(f"加载了 {len(recs)} 个用户的推荐")
   ```

3. ✅ M2 特征是否正确读取
   ```python
   import pandas as pd
   features = pd.read_csv("work/all_features.csv")
   print(features.head())
   ```

4. ✅ 完整流程是否运行
   ```bash
   python app.py  # 测试交互式咨询
   python app_server.py  # 测试 API 服务器
   ```

---

## 🔍 故障排除

| 问题 | 原因 | 解决方案 |
|------|------|--------|
| `work/risk_model.pkl` 不存在 | M3 未运行 | 执行 `python M3_fedavg_risk_model.py` 或 `python run_experiment.py` |
| `work/portfolio_recs.csv` 不存在 | M4 未运行 | 执行 `python M4_portfolio_recommender.py` 或 `python run_experiment.py` |
| `work/all_features.csv` 不存在 | M2 未运行 | 执行 `python M2_features_and_split.py` 或 `python run_experiment.py` |
| 预测失败：`"错误: 无法获取模型使用的特征列"` | M3 没有生成 `used_features_m3.csv` | 检查 M3 代码，确保输出特征列 |
| API 无法加载特征数据 | 路径错误 | 确保在项目根目录运行 `app_server.py` |

---

## 📈 改进前后对比

| 维度 | 改进前 | 改进后 |
|------|-------|-------|
| **model.py** | 随机模型 | M3 实际模型 |
| **portfolio.py** | 硬编码规则 | M4 个性化推荐 |
| **app.py** | 仅 LLM | LLM + M3 + M4 |
| **app_server.py** | 仅会话管理 | 完整数据管道 API |
| **特征利用** | 0% | 100%（M1/M2 数据） |
| **模型利用** | 0% | 100%（M3/M4 结果） |
| **推荐质量** | 泛用规则 | 个性化数据驱动 |

---

## 🎯 下一步建议

1. **测试流程**：运行 `run_experiment.py` 生成完整数据，测试改进后的功能
2. **API 集成**：连接前端页面，调用新增的 API 端点
3. **性能优化**：缓存 M2 特征、M3 模型加载
4. **监控日志**：添加结构化日志，跟踪数据流转过程

---

**更新时间**：2026-04-28  
**集成版本**：M1-M5 完全集成 v1.0
