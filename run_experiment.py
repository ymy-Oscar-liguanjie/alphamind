"""
run_experiment.py

用途：
- 端到端实验脚本：生成合成数据（M1）→ 构建时序样本 → 训练多分类/二分类模型 → 产出指标与图像 → 写入报告
- 同时在 `advisor_design/` 目录生成投顾设计素材（配色、环图、风险仪表盘等）与模板风格的文本建议。

使用方式（Windows, cmd.exe）：
- 进入项目目录后运行：
  python run_experiment.py

输出目录：
- data/：合成数据与中间 CSV
- results/：训练评估的指标与图像
- advisor_design/：用于展示的设计素材与文本建议
"""

# 生成合成数据 -> 构建序列 -> 训练模型（多分类/二分类）-> 保存指标与多张图 -> 写入报告
import os
import json
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
# 简单日志工具
_log_msgs = []

# 中文字体设置，避免中文乱码
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_curve,
    auc,
    precision_recall_curve,
)
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import calibration_curve

from M1_data_prep import simulate
from temporal_model import build_sequences

# 运行快速指南（新增）
RUN_GUIDE = """
快速指南：如何运行本脚本（Windows, cmd.exe）

1) 在命令行中进入项目目录（保证 Python 环境已激活，依赖已安装）
   cd C:\\Users\\13412\\Desktop\\gxb

2) 安装必要依赖（如果未安装）：
   pip install -r requirements.txt

3) 运行脚本：
   python run_experiment.py

4) 结果目录：
   - 合成数据与中间文件保存在：<项目根>/data/
   - 指标、图像等实验结果保存在：<项目根>/results/
   - 投顾设计与文本建议保存在：<项目根>/advisor_design/ （为了演示和展示，不放在 results/）

注意：脚本默认产生合成数据（1000 用户，240 天），运行时间取决于机器性能；建议在调试时将参数 n_users, max_samples 缩小。
"""


def _log(msg: str):
    print(msg)
    _log_msgs.append(msg)


def ensure_dirs(base_dir):
    """
    确保数据与结果目录存在。

    参数：
    - base_dir: 项目根目录绝对路径

    返回：
    - (data_dir, results_dir): 二元组，分别为 data/ 与 results/ 目录的绝对路径
    """
    data_dir = os.path.join(base_dir, "data")
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    return data_dir, results_dir


# 新增：集中管理合成数据模拟参数的函数，方便在一个地方调整所有生成行为
def get_simulation_params(base_dir=None):
    """
    返回用于调用 M1_data_prep.simulate(...) 的参数字典，并在函数内部用中文详细说明每个参数的含义、推荐取值范围与调试建议。

    设计目标：
    - 将所有与合成数据生成有关的可调参数集中在一个地方，便于实验复现与快速调试
    - 提供清晰的中文注释，说明每个参数的含义及在调试/生产时的推荐设置

    参数：
    - base_dir (str|None): 项目根目录（可选）。若提供，则会将 simulate 的 outdir 设置为 os.path.join(base_dir, "data")，
      以保证生成的数据和本脚本的 `ensure_dirs()` 保持一致；否则默认使用当前工作目录下的 "data" 文件夹。

    返回：
    - params (dict)：适合直接用在 simulate(**params) 的参数字典，包含键：
        - n_users (int)：模拟用户数量。推荐：调试时 100~200，常规模拟 1000~10000，大规模压力测试可达 60000 或更多（受内存与时间限制）。
        - n_days (int)：模拟的交易日天数。推荐：短期调试 30~60，常规实验 120~360（如 240），长期回测可更长。
        - seed (int)：随机种子，保证结果可复现。若希望每次不同可设置为 None 或使用当前时间戳。
        - outdir (str)：输出目录，simulate 会在此目录下写入 CSV 与图片。默认为 base_dir/data 或 './data'。
        - max_samples (int|None)：后续序列构建时的样本上限，用于限制内存与训练时间。默认与 simulate 规模相匹配，可增大以训练更多样本。
        - rf_mc_n_estimators (int)：多分类随机森林的树数，树越多通常更稳定但更慢。默认提高为 500 以获得更可靠结果。
        - rf_bin_n_estimators (int)：二分类随机森林的树数，默认提高为 500。

    使用示例：
        params = get_simulation_params(base_dir)
        simulate(**params)

    调试提示：
    - 当脚本运行缓慢或内存占用过高时，先把 n_users 和 n_days 同时缩小为调试用的小值（例如 n_users=200, n_days=60）。
    - 若希望快速观察不同人群分布对下游模型的影响，可只调整 n_users 或在外部对 simulate 生成的 profiles.csv 做采样。
    - 若想复现之前的结果，确保 seed 相同且 outdir 与数据未被覆盖。
    """
    # 推荐的默认值（可以在这里修改为你需要的实验配置）
    params = {
        # 模拟用户数：影响样本量、运行时间和磁盘占用。调试时可设小值，最终实验可增大。
        "n_users": 60000,
        # 模拟天数：影响每个用户的时间序列长度。短序列更快，长序列更贴近真实历史。
        "n_days": 240,
        # 随机种子：固定可复现，设为 None 则每次不同（不推荐用于可复现实验）
        "seed": 42,
        # 输出目录：优先使用传入的 base_dir + /data ，否则使用当前工作目录 data/
        "outdir": os.path.join(base_dir, "data") if base_dir else os.path.join(os.getcwd(), "data"),
        # 序列构建的最大样本数：控制内存与训练时间。None 表示不限制（谨慎使用）。
        "max_samples": 100000,
        # 随机森林的默认树数，增大树数通常能提升稳定性，但会增加训练时间与内存占用
        "rf_mc_n_estimators": 500,
        "rf_bin_n_estimators": 500,
    }

    return params


# 绘图工具（所有标签均使用中文）
def save_confusion_matrix(y_true, y_pred, classes, out_png, title="混淆矩阵"):
    """
    保存混淆矩阵到 PNG。

    参数：
    - y_true: 一维数组，真实标签
    - y_pred: 一维数组，预测标签
    - classes: 类别标签列表（用于坐标轴刻度显示）
    - out_png: 输出图片文件路径
    - title: 图标题（默认“混淆矩阵”）

    返回：
    - 无（图片保存到 out_png）
    """
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=classes, yticklabels=classes)
    plt.xlabel("预测")
    plt.ylabel("真实")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()


def save_roc_pr_curves(y_true, y_prob, out_png_prefix):
    """
    保存 ROC 曲线与 PR 曲线到同一张图。

    参数：
    - y_true: 一维数组，真实二分类标签（0/1）
    - y_prob: 一维数组，正类概率
    - out_png_prefix: 输出文件名前缀（将自动追加 _roc_pr.png）

    返回：
    - 无（图片保存到 out_png_prefix + "_roc_pr.png"）
    """
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)

    prec, rec, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = auc(rec, prec)

    plt.figure(figsize=(10, 4))
    # ROC
    plt.subplot(1, 2, 1)
    plt.plot(fpr, tpr, label=f"AUC值={roc_auc:.3f}")
    plt.plot([0, 1], [0, 1], "k--")
    plt.xlabel("假阳性率")
    plt.ylabel("真正率")
    plt.title("ROC 曲线")
    plt.legend()

    # PR
    plt.subplot(1, 2, 2)
    plt.plot(rec, prec, label=f"AUC值={pr_auc:.3f}")
    plt.xlabel("召回率")
    plt.ylabel("精确率")
    plt.title("精确率-召回率 曲线")
    plt.legend()

    plt.tight_layout()
    plt.savefig(out_png_prefix + "_roc_pr.png")
    plt.close()


def aggregate_feature_importance(importances, seq_len, feat_cols):
    """
    将按时间步展开的特征重要性聚合回基础特征维度。

    参数：
    - importances: 长度 (seq_len * n_feat) 的重要性数组
    - seq_len: 时间步长度
    - feat_cols: 基础特征列名列表（长度 n_feat）

    返回：
    - pd.Series：索引为 feat_cols，值为聚合后的重要性（降序已在外部处理）
    """
    # importances is length (seq_len * n_feat); aggregate back to base feature names
    n_feat = len(feat_cols)
    imp = np.array(importances).reshape(seq_len, n_feat)
    agg = imp.sum(axis=0)
    return pd.Series(agg, index=feat_cols).sort_values(ascending=False)


def save_class_distribution(y, out_png, title="类别分布"):
    """
    保存类别分布条形图。

    参数：
    - y: 一维数组或序列，类别标签
    - out_png: 输出图片路径
    - title: 标题（默认“类别分布”）

    返回：
    - 无
    """
    plt.figure(figsize=(6, 4))
    uniq, cnts = np.unique(y, return_counts=True)
    sns.barplot(x=[str(u) for u in uniq], y=cnts, color="tab:blue")
    for i, c in enumerate(cnts):
        plt.text(i, c, str(c), ha="center", va="bottom", fontsize=9)
    plt.title(title)
    plt.xlabel("类别")
    plt.ylabel("数量")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()


def save_market_overview(mkt_csv, out_png):
    """
    保存市场概览图（收益与波动率双轴）。

    参数：
    - mkt_csv: market.csv 路径
    - out_png: 输出图片路径

    返回：
    - 无
    """
    mkt = pd.read_csv(mkt_csv)
    plt.figure(figsize=(10, 4))
    ax1 = plt.gca()
    ax1.plot(mkt["day"], mkt["mkt_ret"], label="市场收益", color="tab:blue")
    ax1.set_xlabel("交易日")
    ax1.set_ylabel("市场收益", color="tab:blue")
    ax2 = ax1.twinx()
    ax2.plot(mkt["day"], mkt["mkt_vol"], label="市场波动率", color="tab:orange", alpha=0.6)
    ax2.set_ylabel("市场波动率", color="tab:orange")
    plt.title("市场概览：收益与波动率")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()


def save_feature_correlation_heatmap(X, feat_cols, out_png, title="特征相关性热力图（按时间平均）"):
    """
    保存特征相关性热力图（对每条样本按时间平均后计算相关性）。

    参数：
    - X: 三维数组 (n_samples, seq_len, n_features)
    - feat_cols: 特征名列表（长度 n_features）
    - out_png: 输出图片路径
    - title: 图标题

    返回：
    - 无
    """
    X_mean = X.mean(axis=1)
    df = pd.DataFrame(X_mean, columns=feat_cols)
    corr = df.corr()
    plt.figure(figsize=(7, 6))
    sns.heatmap(corr, annot=False, cmap="coolwarm", center=0)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()


def save_feature_importance_bar(agg_series, out_png, title="特征重要性（按时间汇总）"):
    """
    保存特征重要性条形图。

    参数：
    - agg_series: pd.Series，索引为特征名，值为重要性
    - out_png: 输出图片路径
    - title: 图标题

    返回：
    - 无
    """
    plt.figure(figsize=(8, 6))
    sns.barplot(x=agg_series.values, y=agg_series.index, palette="viridis")
    plt.title(title)
    plt.xlabel("重要性")
    plt.ylabel("特征")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()


def save_pca_scatter(X_flat, y, out_png, title="PCA（主成分分析）二维可视化"):
    """
    使用 PCA 将高维特征降至二维并散点图展示，按类别上色。

    参数：
    - X_flat: 二维数组 (n_samples, n_features)
    - y: 一维数组，类别标签
    - out_png: 输出图片路径
    - title: 图标题

    返回：
    - 无
    """
    from sklearn.decomposition import PCA

    pca = PCA(n_components=2, random_state=42)
    X2 = pca.fit_transform(X_flat)
    plt.figure(figsize=(6, 5))
    palette = sns.color_palette("tab10", len(np.unique(y)))
    for cls in np.unique(y):
        mask = y == cls
        plt.scatter(X2[mask, 0], X2[mask, 1], s=8, label=str(cls), color=palette[int(cls) % len(palette)])
    plt.legend(title="类别", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()


def save_example_sequence_plot(X, y, seq_len, feat_cols, out_png):
    """
    随机抽取一个样本，展示部分关键特征的时间序列曲线。

    参数：
    - X: 三维数组 (n_samples, seq_len, n_features)
    - y: 一维数组，标签
    - seq_len: 序列长度
    - feat_cols: 特征名列表
    - out_png: 输出图片路径

    返回：
    - 无
    """
    idx = np.random.randint(0, X.shape[0])
    sample = X[idx]
    plt.figure(figsize=(10, 5))
    t = np.arange(seq_len)
    for f in [i for i, c in enumerate(feat_cols) if c in ("mkt_ret", "mkt_vol")]:
        plt.plot(t, sample[:, f], label=("市场收益" if feat_cols[f] == "mkt_ret" else "市场波动率"))
    if "action" in feat_cols:
        f = feat_cols.index("action")
        plt.step(t, sample[:, f], where="post", label="动作")
    plt.title(f"示例序列（下一步 y={y[idx]}）")
    plt.xlabel("时间步")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()


# 投顾设计素材生成（单独文件夹，不放 results）
def ensure_advisor_dir(base_dir):
    """
    确保 `advisor_design/` 目录存在并返回绝对路径。

    参数：
    - base_dir: 项目根目录

    返回：
    - advisor_dir: `advisor_design/` 的绝对路径
    """
    advisor_dir = os.path.join(base_dir, "advisor_design")
    os.makedirs(advisor_dir, exist_ok=True)
    return advisor_dir


def save_color_palette(advisor_dir):
    """
    生成并保存配色方案图（palette.png）。

    参数：
    - advisor_dir: 输出目录（advisor_design）

    返回：
    - colors: 列表形式的示例色值十六进制字符串
    """
    colors = ["#2E86AB", "#F6F5AE", "#F26419", "#1B998B", "#C5D86D", "#6C5B7B"]
    plt.figure(figsize=(8, 2))
    for i, c in enumerate(colors):
        plt.bar(i, 1, color=c)
        plt.text(i, 1.02, c, ha="center", va="bottom", fontsize=9)
    plt.xticks(range(len(colors)), [f"色{i+1}" for i in range(len(colors))])
    plt.yticks([])
    plt.title("配色方案（示例）")
    plt.tight_layout()
    plt.savefig(os.path.join(advisor_dir, "palette.png"))
    plt.close()
    return colors


def save_portfolio_donut(advisor_dir):
    """
    保存示例资产配置环图（portfolio_donut.png）。

    参数：
    - advisor_dir: 输出目录（advisor_design）

    返回：
    - 无
    """
    labels = ["股票", "债券", "基金", "REITs", "大宗商品", "现金"]
    sizes = [35, 25, 15, 10, 10, 5]
    colors = sns.color_palette("Set2", len(labels))
    fig, ax = plt.subplots(figsize=(5, 5))
    wedges, _ = ax.pie(sizes, labels=labels, colors=colors, startangle=90, wedgeprops=dict(width=0.4))
    ax.text(0, 0, "示例\n资产配置", ha="center", va="center", fontsize=12)
    ax.set_title("资产配置示例（环图）")
    plt.tight_layout()
    plt.savefig(os.path.join(advisor_dir, "portfolio_donut.png"))
    plt.close()


def save_risk_gauge(advisor_dir, score):
    """
    保存风险仪表盘（risk_gauge.png）。

    参数：
    - advisor_dir: 输出目录（advisor_design）
    - score: 0~1 之间的风险评分（数值越大指针越偏向高风险区域）

    返回：
    - 无
    """
    import numpy as _np
    from matplotlib.patches import Wedge
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.set_aspect('equal')
    ax.add_patch(Wedge((0, 0), 1, 180, 0, facecolor="#E0E0E0"))
    ax.add_patch(Wedge((0, 0), 1, 180, 120, facecolor="#2ecc71"))
    ax.add_patch(Wedge((0, 0), 1, 120, 60, facecolor="#f1c40f"))
    ax.add_patch(Wedge((0, 0), 1, 60, 0, facecolor="#e74c3c"))
    theta = 180 * (1 - score)
    x = 0.8 * _np.cos(_np.deg2rad(theta))
    y = 0.8 * _np.sin(_np.deg2rad(theta))
    ax.plot([0, x], [0, y], color="black", linewidth=2)
    ax.scatter([0], [0], color="black", s=20)
    ax.text(0, -0.2, f"风险评分：{score:.2f}", ha="center", va="center", fontsize=12)
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-0.2, 1.05)
    ax.axis('off')
    ax.set_title("风险仪表盘（示例）")
    plt.tight_layout()
    plt.savefig(os.path.join(advisor_dir, "risk_gauge.png"))
    plt.close()


def save_banner(advisor_dir):
    """
    保存报告封面横幅（banner.png）。

    参数：
    - advisor_dir: 输出目录（advisor_design）

    返回：
    - 无
    """
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.set_facecolor("#2E86AB")
    ax.text(0.05, 0.5, "智能投顾实验报告", color="white", fontsize=24, va="center", ha="left")
    ax.text(0.05, 0.2, "数据驱动 · 可解释 · 可视化", color="white", fontsize=12, va="center", ha="left")
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(os.path.join(advisor_dir, "banner.png"))
    plt.close()


def write_design_readme(advisor_dir, colors):
    """
    写入 `advisor_design/README.md`，介绍素材用途与配色。

    参数：
    - advisor_dir: 输出目录（advisor_design）
    - colors: 列表形式的示例色值

    返回：
    - 无
    """
    lines = [
        "# 投顾设计素材（示例）",
        "",
        "本文件夹包含用于报告或演示的美化素材：",
        "- palette.png：配色方案",
        "- portfolio_donut.png：资产配置环图示例",
        "- risk_gauge.png：风险仪表盘示例",
        "- banner.png：报告封面横幅",
        "",
        "建议：统一使用本配色方案，保持标题/图例中文一致，颜色与文字对比充分。",
        "",
        "示例色值：",
        *(f"- {c}" for c in colors),
    ]
    with open(os.path.join(advisor_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def save_small_icons(advisor_dir):
    """
    （可选）生成一组小图标示例到 `advisor_design/icons/`。

    参数：
    - advisor_dir: 输出目录（advisor_design）

    返回：
    - icons_dir: 图标目录绝对路径
    """
    icons_dir = os.path.join(advisor_dir, "icons")
    os.makedirs(icons_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(1.2, 1.2))
    ax.plot([0.1, 0.5, 0.9], [0.2, 0.6, 0.9], color="#2E86AB", linewidth=2)
    ax.axis('off')
    plt.savefig(os.path.join(icons_dir, "icon_stock.png"), dpi=150, bbox_inches='tight', pad_inches=0.05)
    plt.close()

    fig, ax = plt.subplots(figsize=(1.2, 1.2))
    ax.add_patch(plt.Circle((0.5, 0.55), 0.3, color="#1B998B"))
    ax.text(0.5, 0.55, "债", ha='center', va='center', color='white', fontsize=12)
    ax.axis('off')
    plt.savefig(os.path.join(icons_dir, "icon_bond.png"), dpi=150, bbox_inches='tight', pad_inches=0.05)
    plt.close()

    fig, ax = plt.subplots(figsize=(1.2, 1.2))
    ax.plot([0.1, 0.9], [0.6, 0.4], color="#F26419", linewidth=2)
    ax.plot([0.1, 0.9], [0.4, 0.6], color="#F6F5AE", linewidth=2)
    ax.axis('off')
    plt.savefig(os.path.join(icons_dir, "icon_fund.png"), dpi=150, bbox_inches='tight', pad_inches=0.05)
    plt.close()

    fig, ax = plt.subplots(figsize=(1.2, 1.2))
    ax.add_patch(plt.Rectangle((0.2, 0.25), 0.6, 0.5, color="#C5D86D"))
    ax.text(0.5, 0.5, "现", ha='center', va='center', color='black', fontsize=12)
    ax.axis('off')
    plt.savefig(os.path.join(icons_dir, "icon_cash.png"), dpi=150, bbox_inches='tight', pad_inches=0.05)
    plt.close()

    return icons_dir


def generate_text_advice(profiles_csv, advisor_dir, max_users=2000, portfolio_csv=None, predictions_csv=None, filter_user_ids=None):
    """
    生成以模板为风格的投顾建议TXT，并额外生成富文本 HTML：
    - TXT：保持原有格式（兼容旧流程）
    - HTML：新增聚合统计、风险分布饼图、每位用户的可视化资产配置条与折叠建议
    输出：advisor_dir/advice_user_<uid>.txt, advisor_dir/advice_all.txt, advisor_dir/advice_all.html
    """
    import pandas as _pd
    import os as _os

    profiles_csv = _os.path.abspath(profiles_csv)
    base_dir = _os.path.dirname(_os.path.dirname(profiles_csv))
    work_dir = _os.path.join(base_dir, "work")

    if portfolio_csv is None:
        portfolio_csv = _os.path.join(work_dir, "portfolio_recs.csv")
    if predictions_csv is None:
        predictions_csv = _os.path.join(work_dir, "predictions.csv")

    df = _pd.read_csv(profiles_csv)
    if filter_user_ids is not None:
        ids = set(int(x) for x in filter_user_ids)
        df = df[df['user_id'].isin(ids)]
    _os.makedirs(advisor_dir, exist_ok=True)

    risk_pred_map = {}
    risk_prob_map = {}
    try:
        pred_df = _pd.read_csv(predictions_csv)
        if {"user_id", "risk_pred"}.issubset(pred_df.columns):
            risk_pred_map = pred_df.set_index("user_id")["risk_pred"].to_dict()
        if {"user_id", "risk_prob"}.issubset(pred_df.columns):
            risk_prob_map = pred_df.set_index("user_id")["risk_prob"].to_dict()
    except Exception:
        pass

    portfolio_map = {}
    try:
        port_df = _pd.read_csv(portfolio_csv)
        if {"user_id", "portfolio"}.issubset(port_df.columns):
            portfolio_map = port_df.set_index("user_id")["portfolio"].to_dict()
    except Exception:
        pass

    def fmt_alloc_str(s):
        return str(s) if isinstance(s, str) and len(s.strip()) > 0 else "nan"

    def risk_to_str(val):
        try:
            return "进取型" if int(val) == 1 else "稳健型"
        except Exception:
            return "稳健型"

    out_all = []
    user_infos = []  # 用于 HTML 构建

    # 仅处理前 max_users 条（保持可控）
    for _, row in df.head(max_users).iterrows():
        uid = int(row.get('user_id', -1))
        # 风险使用模型预测优先
        risk_model = risk_pred_map.get(uid, row.get('risk_label', 0))
        risk_str = risk_to_str(risk_model)
        risk_prob = risk_prob_map.get(uid, None)

        # 基础画像
        income = float(row.get('income10k', 0.0))    # 万/年
        asset = float(row.get('asset10k', 0.0))      # 万
        debt = float(row.get('debt10k', 0.0))        # 万
        age = int(row.get('age', 0))
        education = str(row.get('education', ''))
        children = int(row.get('children', 0))
        exp_years = int(row.get('exp_years', 0))

        # 资产配置（字符串，若缺失用nan）
        portfolio_str = fmt_alloc_str(portfolio_map.get(uid, None))

        # 负债比
        debt_ratio = (debt / asset) if asset > 0 else 0.0

        # 应急资金：约等于年收入的一半（万元），与示例一致；以可用现金(资产*10%)估算缺口
        emergency_need = round(max(1.0, income / 2.0), 0)
        emergency_gap = max(0.0, round(emergency_need - asset * 0.1, 0))

        # 标题行
        header = f"用户ID：{uid} | 风险等级：{risk_str} 当前推荐配置：{portfolio_str}"
        if risk_prob is not None:
            try:
                header += f" (模型置信度：{float(risk_prob):.2f})"
            except Exception:
                pass

        lines = [header]

        # 一、基础配置建议
        lines.append("--- 一、基础配置建议 ---")
        if int(risk_model) == 1:  # 进取
            if exp_years < 2:
                lines.append("• 作为投资新手，建议以指数基金为主（如沪深300、中证500），降低个股风险")
            else:
                lines.append("• 可配置30%-40%主动管理型基金+20%-30%行业ETF（如科技、新能源）")
            if asset > 500:
                lines.append("• 建议配置10%-15%另类资产（如REITs、黄金ETF）分散风险")
        else:  # 稳健
            if debt_ratio > 0.5:
                lines.append(f"• 负债比例{int(round(debt_ratio*100, 0))}%，建议优先配置50%以上低波动资产（如国债、货币基金）")
            else:
                lines.append("• 可配置40%-50%中短债基金+20%-30%股息率较高的蓝筹股")

        # 二、风险管理建议
        lines.append("--- 二、风险管理建议 ---")
        if debt_ratio > 0.5:
            lines.append(f"• ⚠️ 高负债预警：负债/资产比{int(round(debt_ratio*100, 0))}%，建议每月偿还至少收入的20%用于降低负债")
        else:
            lines.append(f"• 负债健康：当前负债比{int(round(debt_ratio*100, 0))}%，可维持现有还款计划")
        lines.append(f"• 建议储备{int(emergency_need)}万元应急资金（当前缺口约{int(emergency_gap)}万）")

        # 三、长期规划建议
        lines.append("--- 三、长期规划建议 ---")
        if age >= 55:
            lines.append("• 临近退休：未来5年建议每年降低5%-10%权益资产比例，增加年金类产品配置")
        elif age < 35:
            lines.append("• 年轻用户：可采用定投策略（每月投入收入的15%-20%），长期复利效应更显著")
        if children > 0:
            lines.append("• 子女规划：建议配置5万元教育金（可选择529计划或教育金保险）")
        lines.append("• 可关注商业养老保险，补充基础养老金不足")

        # 四、投资行为建议
        lines.append("--- 四、投资行为建议 ---")
        if exp_years < 2:
            lines.append("• 建议先通过模拟交易熟悉市场，避免频繁操作（控制月交易次数）")
        else:
            lines.append("• 可设置止盈止损点（如盈利20%止盈，亏损10%止损），避免情绪化决策")
        if education in ("本科", "硕士及以上"):
            lines.append("• 可利用专业知识深入研究1-2个行业，建立能力圈投资")
        else:
            lines.append("• 推荐关注理财科普内容（如基金定投指南），逐步提升投资认知")

        advice_text = "\n".join(lines)
        with open(_os.path.join(advisor_dir, f"advice_user_{uid}.txt"), "w", encoding="utf-8") as f:
            f.write(advice_text)
        out_all.append(advice_text)

        user_infos.append({
            'uid': uid,
            'risk_str': risk_str,
            'risk_prob': risk_prob,
            'portfolio': portfolio_str,
            'debt_ratio': debt_ratio,
            'emergency_need': emergency_need,
            'emergency_gap': emergency_gap,
            'age': age,
            'income': income,
            'asset': asset,
            'debt': debt,
            'exp_years': exp_years,
            'education': education,
            'children': children,
            'lines': lines,
        })

    txt_path = _os.path.join(advisor_dir, "advice_all.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(out_all))

    # ---------------- HTML 生成 ----------------
    try:
        import matplotlib.pyplot as _plt
        import io as _io, base64 as _b64, html as _html

        html_parts = [
            "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'><title>智能投顾建议汇总</title>",
            "<style>body{font-family:Segoe UI,Microsoft YaHei,Arial,sans-serif;background:#f5f7fa;color:#222;margin:20px;}h1{margin-top:0;} .summary{background:#ffffff;padding:14px 18px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,.06);} .users{margin-top:20px;} .card{background:#fff;border-radius:10px;padding:14px 16px;margin:14px 0;box-shadow:0 2px 8px rgba(0,0,0,.08);} .badge{display:inline-block;padding:3px 10px;border-radius:16px;font-size:12px;color:#fff;} .risk-进取型{background:#E74C3C;} .risk-稳健型{background:#1B998B;} table{border-collapse:collapse;width:100%;margin-top:6px;} th,td{padding:6px 8px;border-bottom:1px solid #e1e5eb;font-size:13px;text-align:left;} details{margin-top:8px;} summary{cursor:pointer;font-weight:bold;} .alloc-bar{display:flex;height:16px;border-radius:8px;overflow:hidden;margin:6px 0;border:1px solid #ddd;} .alloc-bar span{height:100%;display:block;} .risk-gauge{font-family:monospace;margin:4px 0;background:#fff;padding:4px 8px;border-radius:6px;display:inline-block;border:1px solid #ddd;} .footer{margin:40px 0 10px;font-size:12px;color:#555;} .pie{max-width:220px;margin:10px auto;} .tag{background:#eef2f7;padding:2px 6px;border-radius:4px;margin-right:4px;font-size:12px;display:inline-block;} code{background:#eee;padding:2px 4px;border-radius:4px;} </style></head><body>",
            "<h1>智能投顾建议（可视化版）</h1>"
        ]

        # 聚合统计
        if user_infos:
            avg_income = sum(u['income'] for u in user_infos)/len(user_infos)
            avg_asset = sum(u['asset'] for u in user_infos)/len(user_infos)
            avg_debt = sum(u['debt'] for u in user_infos)/len(user_infos)
            avg_debt_ratio = sum(u['debt_ratio'] for u in user_infos)/len(user_infos)
            risk_counts = {}
            for u in user_infos:
                risk_counts[u['risk_str']] = risk_counts.get(u['risk_str'], 0) + 1
            labels = list(risk_counts.keys())
            sizes = [risk_counts[k] for k in labels]

            # 风险分布饼图
            buf = _io.BytesIO()
            fig, ax = _plt.subplots(figsize=(3.4, 3.4))
            ax.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=120, colors=['#E74C3C', '#1B998B'])
            ax.set_title('风险类型分布', fontproperties=None, fontsize=12)
            _plt.tight_layout()
            fig.savefig(buf, format='png', dpi=130)
            _plt.close(fig)
            img64 = _b64.b64encode(buf.getvalue()).decode('utf-8')

            html_parts.append("<div class='summary'>")
            html_parts.append(f"<div class='tag'>用户数: {len(user_infos)}</div><div class='tag'>平均收入(万): {avg_income:.1f}</div><div class='tag'>平均资产(万): {avg_asset:.1f}</div><div class='tag'>平均负债(万): {avg_debt:.1f}</div><div class='tag'>平均负债比: {avg_debt_ratio:.1%}</div>")
            html_parts.append(f"<div class='pie'><img src='data:image/png;base64,{img64}' alt='风险分布'></div>")
            html_parts.append("</div>")

        # 用户卡片
        html_parts.append("<div class='users'>")
        color_map = ['#2E86AB','#1B998B','#F26419','#C5D86D','#F6F5AE','#AA8F66','#9B5DE5','#FFAFCC']
        for idx, u in enumerate(user_infos):
            risk_prob_disp = f"置信度 {u['risk_prob']:.2f}" if isinstance(u['risk_prob'], (int,float)) else ""
            html_parts.append("<div class='card'>")
            html_parts.append(f"<div><span class='badge risk-{u['risk_str']}'> {u['risk_str']} </span> <strong>用户 {u['uid']}</strong> {risk_prob_disp}</div>")
            html_parts.append("<table><tbody>")
            html_parts.append(f"<tr><th>年龄</th><td>{u['age']}岁</td><th>投资经验</th><td>{u['exp_years']}年</td></tr>")
            html_parts.append(f"<tr><th>收入(万)</th><td>{u['income']:.1f}</td><th>资产(万)</th><td>{u['asset']:.1f}</td></tr>")
            html_parts.append(f"<tr><th>负债(万)</th><td>{u['debt']:.1f}</td><th>负债比</th><td>{u['debt_ratio']:.1%}</td></tr>")
            html_parts.append(f"<tr><th>应急金需(万)</th><td>{int(u['emergency_need'])}</td><th>缺口(万)</th><td>{int(u['emergency_gap'])}</td></tr>")
            html_parts.append(f"<tr><th>学历</th><td>{_html.escape(u['education'])}</td><th>子女</th><td>{u['children']}</td></tr>")
            html_parts.append("</tbody></table>")

            # 风险刻度条
            if isinstance(u['risk_prob'], (int,float)):
                prob = max(0.0, min(1.0, float(u['risk_prob'])))
                filled = int(round(prob*10))
                gauge = '█'*filled + '░'*(10-filled)
                html_parts.append(f"<div class='risk-gauge'>风险概率条：[{gauge}] {prob:.0%}</div>")

            # 资产配置条
            alloc = u['portfolio']
            if alloc != 'nan' and ':' in alloc:
                try:
                    segs = [x.strip() for x in alloc.split(',') if x.strip()]
                    spans = []
                    total_pct = 0.0
                    parsed = []
                    for s in segs:
                        name, pct = s.split(':')
                        p = float(pct.strip().strip('%'))
                        parsed.append((name.strip(), p))
                        total_pct += p
                    if total_pct > 0:
                        html_parts.append("<div class='alloc-bar'>")
                        for i,(name,p) in enumerate(parsed):
                            w = p/total_pct*100
                            color = color_map[i % len(color_map)]
                            spans.append(f"<span title='{name} {p:.1f}%' style='background:{color};width:{w:.2f}%;'></span>")
                        html_parts.extend(spans)
                        html_parts.append("</div>")
                        legend = ' | '.join(f"<span style='color:{color_map[i % len(color_map)]};font-weight:600'>{_html.escape(name)}</span>" for i,(name,_) in enumerate(parsed))
                        html_parts.append(f"<div style='font-size:12px;'>图例：{legend}</div>")
                except Exception:
                    pass
            else:
                html_parts.append("<div style='font-size:12px;color:#888;'>无资产配置数据</div>")

            # 建议折叠
            esc_lines = [_html.escape(x) for x in u['lines']]
            html_parts.append("<details><summary>展开/收起建议文本</summary><pre style='white-space:pre-wrap;font-size:12px;line-height:1.45;margin-top:6px;'>" + "\n".join(esc_lines) + "</pre></details>")
            html_parts.append("</div>")  # card end
        html_parts.append("</div>")  # users

        html_parts.append("<div class='footer'>免责声明：本报告仅为演示用途，不构成任何实际投资建议。</div>")
        html_parts.append("</body></html>")

        html_path = _os.path.join(advisor_dir, "advice_all.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_parts))
        print(f"HTML 投顾建议已生成: {html_path}")
    except Exception as _e:
        print(f"[WARN] 生成 HTML 建议失败: {_e}")

    return txt_path


def main():
    """
    主入口：
    - 生成合成数据到 data/
    - 构建序列并训练多分类与二分类模型，保存指标与图像到 results/
    - 生成投顾设计素材与文本建议到 advisor_design/

    参数：
    - 无（脚本内使用默认参数；如需可改为接收命令行参数）

    返回：
    - 无（在控制台打印路径概览）

    使用示例：
    - python run_experiment.py
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir, results_dir = ensure_dirs(base_dir)

    # 打印快速指南
    print(RUN_GUIDE)

    # 1) 生成合成数据
    # 使用集中配置的模拟参数（方便在一个地方调整所有模拟相关参数）
    sim_params = get_simulation_params(base_dir)
    # 确保 simulate 的 outdir 与 ensure_dirs 创建的 data_dir 一致性：
    # 如果 get_simulation_params 返回不同 outdir（用户希望覆盖），则以返回值为准；
    # 否则保持之前的 data_dir
    if "outdir" in sim_params:
        data_dir = sim_params["outdir"]
    # 为 simulate() 准备参数，只传入它接受的键
    simulate_call_params = {k: v for k, v in sim_params.items() if k in ("n_users", "n_days", "seed", "outdir")}
    simulate(**simulate_call_params)

    tx_path = os.path.join(data_dir, "transactions.csv")
    mkt_path = os.path.join(data_dir, "market.csv")
    profiles_path = os.path.join(data_dir, "profiles.csv")

    # 2) 构建序列（多分类）
    seq_len = 30
    max_samples = sim_params.get("max_samples", 50000)
    X, y, feat_cols = build_sequences(tx_path, mkt_path, seq_len=seq_len, max_samples=max_samples,
                                     add_rolling=True, rolling_windows=(3, 7, 14), binary=False)
    if X.size == 0:
        raise RuntimeError("No sequences built. Check data generation.")

    # 3) 划分数据、缩放
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    scaler = StandardScaler()
    n_tr, sl, nf = X_train.shape
    X_train_flat = X_train.reshape(n_tr * sl, nf)
    scaler.fit(X_train_flat)
    X_train_scaled = scaler.transform(X_train_flat).reshape(n_tr, sl, nf)
    n_te = X_test.shape[0]
    X_test_scaled = scaler.transform(X_test.reshape(n_te * sl, nf)).reshape(n_te, sl, nf)

    # 4) 训练 RF（多分类）
    rf_mc_estimators = sim_params.get("rf_mc_n_estimators", 200)
    rf_mc = RandomForestClassifier(n_estimators=rf_mc_estimators, random_state=42, n_jobs=-1)
    X_train_vec = X_train_scaled.reshape(n_tr, sl * nf)
    X_test_vec = X_test_scaled.reshape(n_te, sl * nf)
    rf_mc.fit(X_train_vec, y_train)
    y_pred_mc = rf_mc.predict(X_test_vec)

    # 指标与图（多分类）
    classes_mc = sorted(np.unique(y))
    report_mc = classification_report(y_test, y_pred_mc, output_dict=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(results_dir, f"metrics_multiclass_{ts}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_mc, f, ensure_ascii=False, indent=2)

    cm_png = os.path.join(results_dir, f"cm_multiclass_{ts}.png")
    save_confusion_matrix(y_test, y_pred_mc, classes=[str(c) for c in classes_mc], out_png=cm_png,
                          title="混淆矩阵（多分类）")

    agg_imp = aggregate_feature_importance(rf_mc.feature_importances_, seq_len, feat_cols)
    imp_png = os.path.join(results_dir, f"feature_importance_multiclass_{ts}.png")
    save_feature_importance_bar(agg_imp, imp_png, title="特征重要性（按时间汇总）")

    pca_png = os.path.join(results_dir, f"pca_multiclass_{ts}.png")
    save_pca_scatter(X_test_vec, y_test, pca_png, title="PCA（主成分分析）二维可视化（多分类）")

    seq_png = os.path.join(results_dir, f"example_sequence_{ts}.png")
    save_example_sequence_plot(X_test_scaled, y_test, seq_len, feat_cols, seq_png)

    # 5) 构建序列（二分类，买入 vs 非买入）
    Xb, yb, feat_cols_b = build_sequences(tx_path, mkt_path, seq_len=seq_len, max_samples=max_samples,
                                          add_rolling=True, rolling_windows=(3, 7, 14), binary=True)
    Xb_train, Xb_test, yb_train, yb_test = train_test_split(Xb, yb, test_size=0.2, random_state=42, stratify=yb)
    n_tr_b = Xb_train.shape[0]
    n_te_b = Xb_test.shape[0]

    scaler_b = StandardScaler()
    Xb_train_flat = Xb_train.reshape(n_tr_b * seq_len, len(feat_cols_b))
    scaler_b.fit(Xb_train_flat)
    Xb_train_scaled = scaler_b.transform(Xb_train_flat).reshape(n_tr_b, seq_len, len(feat_cols_b))
    Xb_test_scaled = scaler_b.transform(Xb_test.reshape(n_te_b * seq_len, len(feat_cols_b))).reshape(n_te_b, seq_len, len(feat_cols_b))

    rf_bin_estimators = sim_params.get("rf_bin_n_estimators", 300)
    rf_bin = RandomForestClassifier(n_estimators=rf_bin_estimators, random_state=42, n_jobs=-1)
    rf_bin.fit(Xb_train_scaled.reshape(n_tr_b, -1), yb_train)
    yb_pred = rf_bin.predict(Xb_test_scaled.reshape(n_te_b, -1))
    if hasattr(rf_bin, "predict_proba"):
        yb_prob = rf_bin.predict_proba(Xb_test_scaled.reshape(n_te_b, -1))[:, 1]
    else:
        yb_prob = np.where(yb_pred == 1, 1.0, 0.0)

    report_bin = classification_report(yb_test, yb_pred, output_dict=True)
    report_bin_path = os.path.join(results_dir, f"metrics_binary_{ts}.json")
    with open(report_bin_path, "w", encoding="utf-8") as f:
        json.dump(report_bin, f, ensure_ascii=False, indent=2)

    cm_bin_png = os.path.join(results_dir, f"cm_binary_{ts}.png")
    save_confusion_matrix(yb_test, yb_pred, classes=["非买入", "买入"], out_png=cm_bin_png,
                          title="混淆矩阵（二分类）")

    rocpr_png_prefix = os.path.join(results_dir, f"binary_{ts}")
    save_roc_pr_curves(yb_test, yb_prob, rocpr_png_prefix)

    # 校准曲线
    try:
        prob_true, prob_pred = calibration_curve(yb_test, yb_prob, n_bins=10, strategy="quantile")
        plt.figure(figsize=(5, 4))
        plt.plot([0, 1], [0, 1], "k--", label="理想")
        plt.plot(prob_pred, prob_true, marker="o", label="模型")
        plt.xlabel("预测概率")
        plt.ylabel("观测频率")
        plt.title("概率校准曲线（买入 vs 非买入）")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(results_dir, f"calibration_binary_{ts}.png"))
        plt.close()
    except Exception as e:
        _log(f"WARN: calibration_curve failed: {e}")

    agg_imp_b = aggregate_feature_importance(rf_bin.feature_importances_, seq_len, feat_cols_b)
    imp_bin_png = os.path.join(results_dir, f"feature_importance_binary_{ts}.png")
    save_feature_importance_bar(agg_imp_b, imp_bin_png, title="特征重要性（二分类-按时间汇总）")

    # 附加图表
    save_class_distribution(y_train, os.path.join(results_dir, f"y_dist_multiclass_train_{ts}.png"), title="类别分布（多分类-训练集）")
    save_class_distribution(y_test, os.path.join(results_dir, f"y_dist_multiclass_test_{ts}.png"), title="类别分布（多分类-测试集）")
    save_class_distribution(yb_train, os.path.join(results_dir, f"y_dist_binary_train_{ts}.png"), title="类别分布（二分类-训练集）")
    save_class_distribution(yb_test, os.path.join(results_dir, f"y_dist_binary_test_{ts}.png"), title="类别分布（二分类-测试集）")

    save_market_overview(mkt_path, os.path.join(results_dir, f"market_overview_{ts}.png"))
    save_feature_correlation_heatmap(Xb_test_scaled, feat_cols_b, os.path.join(results_dir, f"corr_heatmap_{ts}.png"))

    # 写入简要报告
    md = [
        f"# 实验报告 - {ts}",
        "",
        "本次实验基于合成数据，训练了随机森林多分类与二分类模型。",
        "",
        "## 数据",
        f"- 交易与市场 CSV 已保存到: {data_dir}",
        f"- 序列长度: {seq_len}",
        f"- 特征列: {', '.join(feat_cols)}",
        "",
        "## 结果",
        f"- 多分类指标 JSON: {os.path.basename(report_path)}",
        f"- 二分类指标 JSON: {os.path.basename(report_bin_path)}",
        "",
        "## 图像",
        f"- {os.path.basename(cm_png)}: 混淆矩阵（多分类）",
        f"- {os.path.basename(imp_png)}: 特征重要性（按时间汇总）",
        f"- {os.path.basename(pca_png)}: PCA（主成分分析）二维可视化",
        f"- {os.path.basename(seq_png)}: 示例序列",
        f"- {os.path.basename(cm_bin_png)}: 混淆矩阵（二分类）",
        f"- {os.path.basename(rocpr_png_prefix + '_roc_pr.png')}: ROC/PR 曲线（二分类）",
        f"- {os.path.basename('calibration_binary_' + ts + '.png')}: 概率校准曲线（二分类）",
        f"- {os.path.basename('y_dist_multiclass_train_' + ts + '.png')}: 类别分布（多分类-训练集）",
        f"- {os.path.basename('market_overview_' + ts + '.png')}: 市场概览",
        f"- {os.path.basename('corr_heatmap_' + ts + '.png')}: 特征相关性热力图",
        "",
        "> 提示：数值大小仅用于演示，真实场景请替换为真实数据。",
    ]
    with open(os.path.join(results_dir, f"report_{ts}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # 生成投顾设计素材（单独文件夹）
    advisor_dir = ensure_advisor_dir(base_dir)
    try:
        colors = save_color_palette(advisor_dir)
        save_portfolio_donut(advisor_dir)
        mean_score = float(np.mean(yb_prob)) if isinstance(yb_prob, (list, np.ndarray)) else 0.5
        save_risk_gauge(advisor_dir, max(0.0, min(1.0, mean_score)))
        save_banner(advisor_dir)
        write_design_readme(advisor_dir, colors)
        save_small_icons(advisor_dir)
        advice_file = generate_text_advice(profiles_path, advisor_dir, max_users=200)
        print(f"投顾文本建议已生成：{advice_file}")
    except Exception as e:
        _log(f"WARN: advisor_design generation failed: {e}")

    # 写入日志（若有）
    if _log_msgs:
        with open(os.path.join(results_dir, f"run_experiment_{ts}.log"), "w", encoding="utf-8") as f:
            f.write("\n".join(_log_msgs))

    print(f"完成！数据目录: {data_dir}，结果目录: {results_dir}，投顾设计目录: {advisor_dir}")


if __name__ == "__main__":
    main()
