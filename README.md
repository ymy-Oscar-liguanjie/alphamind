# 智能投顾演示项目（中文）

本项目是一套端到端的“模拟数据 → 特征工程 → 风险预测（含时序/GNN增强与联邦平均）→ 资产配置推荐 → 可解释性分析 → GUI演示”流水线，便于在本地快速体验从数据到应用的完整流程。

- 数据来源：M1 生成的合成数据（用户画像 + 市场 + 交易 + 问答情绪）
- 模块划分：M1~M6 对应数据准备、特征与拆分、联邦风险模型、资产配置、可解释性、GUI
- 额外组件：时序建模模块 temporal_model.py（支持 n_days 窗口体现市场变化）、单元测试 test_temporal_model.py

## 操作指南（简单完整）

前提：Windows + Python 3.10 及以上（cmd.exe 环境）。以下命令可直接复制粘贴到命令行。

1) 可选：创建并激活虚拟环境，然后安装依赖

```bat
cd C:\Users\13412\Desktop\gxb
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r C:\Users\13412\Desktop\gxb\requirements.txt
```

2) 一键跑通全流程（推荐）

```bat
python C:\Users\13412\Desktop\gxb\run_experiment.py
```

运行完成后，主要产物：
- 数据：`gxb/data/`
- 结果：`gxb/results/`（多种中文图表与指标 JSON、Markdown 报告）
- 投顾设计：`gxb/advisor_design/`（配色/仪表盘/横幅等素材，投顾建议 HTML 与文本：`advice_all.html`、`advice_all.txt`、`advice_user_*.txt`，以及示例小图标）

3) 启动 GUI 演示（本地交互生成建议）

```bat
python C:\Users\13412\Desktop\gxb\M6_ui.py
```

4) 可选：按模块逐步运行（便于理解流水线）

```bat
python C:\Users\13412\Desktop\gxb\M1_data_prep.py
python C:\Users\13412\Desktop\gxb\M2_features_and_split.py
python C:\Users\13412\Desktop\gxb\M3_fedavg_risk_model.py
python C:\Users\13412\Desktop\gxb\M4_portfolio_recommender.py
python C:\Users\13412\Desktop\gxb\M5_explainability_report.py
```

说明：
- M3 会在 `work/predictions.csv` 输出风险预测，M4 会在 `work/portfolio_recs.csv` 输出资产配置；M5 会在 `m5_results/` 输出分析图表，并将模板风格的投顾建议文本写入 `advisor_design/`。
- 仅想生成投顾建议文档时，按 1→2（或手动执行 1→M1→M2→M3→M4→M5）即可在 `advisor_design/` 查看 `advice_all.html`、`advice_all.txt` 与 `advice_user_*.txt`。

---

## 目录结构与产物

- M1_data_prep.py：生成合成数据到 `data/`（通过 `run_experiment.py` 调用）或 `outputs/`（单独运行 M1 时）
  - profiles.csv：用户画像（年龄、学历、收入、资产、负债、子女、经验、风险标签）
  - market.csv：逐日市场收益与波动率
  - transactions.csv：用户-日级交易行为（-1 卖/0 观望/1 买）
  - dialogs.csv：用户问答文本与情绪（-1/0/1）
  - user_data_vis.png：用户画像分布可视化
- M2_features_and_split.py：从 M1 数据提取/聚合特征，拆分训练/测试集，保存至 `work/`
  - work/all_features.csv、train_features.csv、test_features.csv
- M3_fedavg_risk_model.py：联邦平均（FedAvg）训练逻辑回归；可选融合 GNN 与时序特征
  - work/risk_model.pkl：保存的模型
  - work/predictions.csv：测试集预测
  - work/used_features_m3.csv：模型实际使用的特征列
- M4_portfolio_recommender.py：基于风险概率生成个性化资产配置
  - work/portfolio_recs.csv：包含推荐组合（Stocks/Bonds/Funds/REITs/Commodities/Cash 权重）
- M5_explainability_report.py：特征重要性分析 + 面向用户的投资建议文案
  - m5_results/feature_importance.csv、feature_importance.png
  - m5_results/user_advice.txt
- M6_ui.py：本地 GUI（tkinter）交互演示，实时给出投资建议
- temporal_model.py：时序建模（体现 n_days 窗口内市场变化），支持 LSTM 或 RandomForest
  - work/temporal_model_rf.joblib 或 work/temporal_model_lstm.h5
  - work/scaler.joblib（可选）
- test_temporal_model.py：针对时序样本构造的最小单元测试

## 环境依赖

建议 Python 3.10+（项目中存在 CPython 3.13 的字节码文件，3.13 亦可）。

必需依赖：

- numpy, pandas, seaborn, matplotlib
- scikit-learn, joblib
- tkinter（Python 内置，Windows 通常可用）

可选依赖：

- tensorflow（使用 LSTM 时需要；未安装将自动回退至 RandomForest）
- pytest（运行单元测试）
- yagmail、requests、ddddocr（仅 main.py 抢课脚本使用，与投顾流水线无关）

安装示例（Windows cmd）：

```
pip install numpy pandas seaborn matplotlib scikit-learn joblib
pip install tensorflow  # 可选，用于 LSTM
pip install pytest      # 可选，运行单测
```

## 快速开始（推荐顺序）

1) 生成合成数据（M1）

```
python c:\Users\13412\Desktop\M1_data_prep.py
```

2) 特征工程与数据拆分（M2）

```
python c:\Users\13412\Desktop\M2_features_and_split.py
```

3) 训练风险模型（M3，默认融合时序与 GNN 特征，自动保存到 work/）

```
python c:\Users\13412\Desktop\M3_fedavg_risk_model.py
```

可选开关（在代码中已有默认启用）：use_temporal/use_gnn。

4) 资产配置推荐（M4）

```
python c:\Users\13412\Desktop\M4_portfolio_recommender.py
```

5) 可解释性分析与投资建议（M5）

```
python c:\Users\13412\Desktop\M5_explainability_report.py
```

6) GUI 演示（M6）

```
python c:\Users\13412\Desktop\M6_ui.py
```

## 时序模型 temporal_model.py（体现 n_days 窗口内市场变化）

- build_sequences：
  - 将用户逐日交易 action 与市场 mkt_ret/mkt_vol（含 3/7/14 日滚动均值，可关）对齐，
  - 以滑动窗口（seq_len = n_days）构建样本，标签为“下一个交易日的动作”。
  - 对缺失日期进行鲁棒重索引（缺失动作填 0=观望），保证每个用户序列连续。
- 训练：
  - --model auto：优先 LSTM（若安装 TF），否则回退 RandomForest
  - --seq_len 30：窗口大小即 n_days，直接刻画“近 n_days 市场变化”
  - --scale：可选对特征做 StandardScaler

示例（Windows cmd）：

```
# 使用随机森林 + 二分类（买入 vs 非买入）
python c:\Users\13412\Desktop\temporal_model.py --seq_len 30 --model rf --binary --max_samples 10000

# 自动选择模型（若 TF 可用则用 LSTM），保存 scaler
python c:\Users\13412\Desktop\temporal_model.py --seq_len 30 --model auto --early_stop --save_scaler
```

单元测试：

```
pytest c:\Users\13412\Desktop\test_temporal_model.py -q
```

## 数据流与典型文件

- 数据目录：`data/`（通过 `run_experiment.py` 生成）或 `outputs/`（单独运行 `M1_data_prep.py`）
- 工作目录 `work/`：
  - M2：train_features.csv、test_features.csv
  - M3：risk_model.pkl、predictions.csv、used_features_m3.csv
  - M4：portfolio_recs.csv
  - temporal：temporal_model_rf.joblib 或 temporal_model_lstm.h5、scaler.joblib（可选）
- 结果目录 `m5_results/`：feature_importance.csv/png、user_advice.txt

M3 在 load_data 中可选融合：

- 时序特征：近窗 EMA/波动/趋势/与市场相关性/买入占比
- GNN 特征：构建用户画像 kNN 图并做 2 步传播，得到 _gnn1/_gnn2 扩散特征

## 常见问题（FAQ）

1. 运行 temporal_model 提示“没有足够的数据构建序列”？
   
   - 先运行 M1 生成数据；或检查 seq_len 是否过大。

2. LSTM 报错 tensorflow 未安装？
   
   - 可安装 tensorflow，或加参数 --model rf 使用随机森林。

3. GUI 无法加载模型？
   
   - GUI 会在缺少模型时回退规则推断；若需加载训练模型，先运行 M3。

4. 字体导致中文图例乱码？
   
   - 已在 M1/M5 中设置中文字体；如仍有问题可安装 SimHei/微软雅黑/宋体。

## 免责声明

本项目仅用于课程/学习演示，不构成任何投资建议。请勿用于真实投顾或生产环境。

## 运行 run_experiment.py 的快速指南

该脚本一键完成：生成合成数据 → 构建时间序列 → 训练多分类与二分类模型 → 导出多种中文图表与指标报告，并额外在项目根目录创建 `advisor_design/` 文件夹存放投顾设计美化素材与最终建议文档。

- 准备依赖（Windows cmd）：

```bat
python -m pip install -r C:\Users\13412\Desktop\gxb\requirements.txt
```

- 运行脚本：

```bat
python C:\Users\13412\Desktop\gxb\run_experiment.py
```

- 产物说明：
  - 数据：`gxb/data/`（profiles.csv、market.csv、transactions.csv、dialogs.csv、user_data_vis.png）
  - 结果：`gxb/results/`（多分类/二分类的混淆矩阵、特征重要性、PCA、ROC/PR、类别分布、市场概览、相关性热力图、概率校准曲线等中文图表，以及 metrics_*.json、report_*.md）
  - 投顾设计：`gxb/advisor_design/`（生成的配色方案图、仪表盘样例图、设计说明文档、示例图标，以及最终投顾建议：`advice_all.html`、`advice_all.txt`、`advice_user_*.txt`）

- 参数调整：如需控制模拟规模与性能，可在 `run_experiment.py` 的 `get_simulation_params(...)` 中调整 `n_users`、`n_days`、`max_samples` 等；脚本默认写入 `data/` 目录。

- 预览 HTML 建议：运行完毕后，直接双击打开 `advisor_design/advice_all.html` 即可在浏览器查看彩色可视化版汇总建议。
