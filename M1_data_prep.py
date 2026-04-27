# M1_data_prep.py
# 数据模拟模块：生成用户画像、市场数据、交易日志、对话数据等。
# 目的：为下游模块提供结构化的合成数据，包括用户特征、行为与市场环境
import os  # 用于目录创建与路径处理
import numpy as np  # 用于数值运算（随机数生成、数组运算）
import pandas as pd  # 用于结构化数据（DataFrame）与保存
import matplotlib.pyplot as plt  # 用于数据可视化
import seaborn as sns  # 基于 matplotlib 的高级可视化

# 修正字体设置以支持中文标签（可选）
plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei", "SimSun"]  # 常见中文字体
plt.rcParams["axes.unicode_minus"] = False  # 负号正常显示
plt.rcParams["figure.dpi"] = 150  # 图片清晰度


def simulate(n_users=60000, n_days=240, seed=42, outdir="outputs"):
    """
    生成用户与市场相关的合成数据，保存为 CSV 文件，并输出简单可视化结果。

    参数：
        n_users: 模拟的用户数量（默认 2000）
        n_days: 模拟的交易日天数（默认 240）
        seed: 随机种子，保证结果可复现（默认 42）
        outdir: 输出目录，保存 CSV 与图像（默认 'outputs'）
    """
    # 使用固定种子初始化随机数生成器，保证结果可复现
    rng = np.random.default_rng(seed)
    # 创建输出目录（若已存在则不报错）
    os.makedirs(outdir, exist_ok=True)

    # 1. 生成用户画像数据（年龄、学历、收入等）
    # 年龄在 20~64 岁之间（含 20，不含 65）
    ages = rng.integers(20, 65, n_users)

    # 学历分布（影响收入/资产与风险偏好）
    education_levels = ["高中及以下", "大专", "本科", "硕士及以上"]  # 采用中文标签便于下游阅读
    education_probs = [0.2, 0.3, 0.4, 0.1]
    education = rng.choice(education_levels, size=n_users, p=education_probs)

    # 各学历的收入基线（单位：万元/年）
    edu_income_baseline = {
        "高中及以下": 10,
        "大专": 14,
        "本科": 18,
        "硕士及以上": 28
    }
    # 围绕基线按正态分布采样个人收入，并裁剪到合理范围
    income = np.array([
        rng.normal(edu_income_baseline[edu], 5, 1)[0] for edu in education
    ]).clip(3, 80)

    # 各学历对应的资产倍数（学历越高，倍数越大）
    edu_asset_multiplier = {
        "高中及以下": 5,
        "大专": 6,
        "本科": 7,
        "硕士及以上": 9
    }
    asset_multipliers = np.array([edu_asset_multiplier[edu] for edu in education])
    # 计算总资产（收入×倍数 + 噪声），裁剪至合理范围（5 到 800 万）
    asset10k = (income * asset_multipliers + rng.normal(0, 15, n_users)).clip(5, 800)

    # 投资经验（单位：年，整数 0~9）
    exp_years = rng.integers(0, 10, n_users)

    # 子女数量与年龄相关（影响可支配收入与风险偏好）
    def get_children(age):
        """根据年龄段返回一个合理的子女数量。"""
        if age < 30:
            return rng.choice([0, 1], p=[0.8, 0.2])
        elif 30 <= age < 50:
            return rng.choice([0, 1, 2], p=[0.2, 0.5, 0.3])
        else:
            return rng.choice([0, 1, 2, 3], p=[0.3, 0.4, 0.2, 0.1])

    children = np.array([get_children(age) for age in ages])

    # 负债计算：以基础比例为底，受子女与学历倍数影响
    debt_ratio = 0.3 + 0.1 * (children > 0) - 0.05 * np.array([edu_asset_multiplier[edu] / 10 for edu in education])
    debt10k = (income * asset_multipliers * debt_ratio + rng.normal(0, 5, n_users)).clip(0, asset10k * 0.7)

    # 风险标签（0=稳健，1=进取）：由多因素加权得分决定
    risk_score = (
            0.2 * (ages < 30) +
            0.2 * (income > 20) +
            0.2 * (asset10k > 100) +
            0.2 * (exp_years > 3) +
            0.1 * (np.isin(education, ["本科", "硕士及以上"])) +
            0.1 * (children == 0)
    )
    risk_label = (risk_score > 0.5).astype(int)

    # 构建并保存用户画像表
    profiles = pd.DataFrame({
        "user_id": np.arange(n_users),
        "age": ages,
        "education": education,
        "income10k": income,
        "asset10k": asset10k,
        "debt10k": debt10k,
        "children": children,
        "exp_years": exp_years,
        "risk_label": risk_label
    })
    profiles.to_csv(os.path.join(outdir, "profiles.csv"), index=False)

    # 2. 生成市场数据：日收益与波动率
    mkt = rng.normal(0.0005, 0.01, n_days)  # 每日市场收益（均值 0.05%，标准差 1%）
    vol = rng.normal(0.15, 0.05, n_days).clip(0.05, 0.6)  # 每日波动率（均值 15%）
    market = pd.DataFrame({"day": range(n_days), "mkt_ret": mkt, "mkt_vol": vol})
    market.to_csv(os.path.join(outdir, "market.csv"), index=False)

    # 3. 生成用户交易：按用户与日期，受市场与风险偏好影响
    transactions = []
    for uid in range(n_users):
        # 偏好：进取型更易买入，稳健型更易卖出
        pref = 0.7 if risk_label[uid] == 1 else 0.3
        for d in range(n_days):
            ret = mkt[d] + rng.normal(0, 0.01)  # 观测收益（含额外噪声）
            # 买入概率随偏好与正向市场收益上升
            p_buy = np.clip(pref * (0.5 + 3 * mkt[d]), 0.05, 0.9)
            # 卖出概率在偏好较低且市场走弱时上升
            p_sell = np.clip((1 - pref) * (0.5 - 3 * mkt[d]), 0.05, 0.9)
            # 行为：-1 卖出，0 观望，1 买入
            # 概率：卖出 = p_sell*(1-p_buy)，观望 = 剩余概率，买入 = p_buy
            act = rng.choice(
                [-1, 0, 1],
                p=[p_sell * (1 - p_buy), 1 - (p_buy + p_sell * (1 - p_buy)), p_buy]
            )
            transactions.append([uid, d, ret, vol[d], act])

    # 保存交易表
    transactions = pd.DataFrame(transactions, columns=["user_id", "day", "mkt_ret", "mkt_vol", "action"])
    transactions.to_csv(os.path.join(outdir, "transactions.csv"), index=False)

    # 4. 生成对话数据（每位用户一条）：问答文本与情绪
    intents = [
        "新能源 基金 长期 定投",
        "AI 半导体 成长 风险承受高",
        "价值 投资 蓝筹 稳健 分红",
        "债券 固收 低波动",
        "黄金 商品 抗通胀",
        "医药 消费 产业轮动",
        "海外 ETF 汇率 风险",
        "短线 交易 高频",
        "长期 持有 价值"
    ]
    dialogs = pd.DataFrame({
        "user_id": np.arange(n_users),
        "q_text": rng.choice(intents, n_users),
        "a_text": rng.choice(intents, n_users),
        "q_sentiment": rng.choice([-1, 0, 1], n_users, p=[0.2, 0.5, 0.3]),
        "a_sentiment": rng.choice([-1, 0, 1], n_users, p=[0.2, 0.5, 0.3])
    })
    dialogs.to_csv(os.path.join(outdir, "dialogs.csv"), index=False)

    # 5. 简单可视化：检查用户画像分布
    plt.figure(figsize=(18, 15))
    # 子图 1：年龄分布
    plt.subplot(3, 2, 1)
    sns.histplot(profiles["age"], kde=True)
    plt.title("用户年龄分布")
    # 子图 2：学历分布
    plt.subplot(3, 2, 2)
    sns.countplot(x="education", data=profiles)
    plt.title("学历分布")
    # 子图 3：收入分布
    plt.subplot(3, 2, 3)
    sns.histplot(profiles["income10k"], kde=True)
    plt.title("年收入分布（万元）")
    # 子图 4：不同学历的收入
    plt.subplot(3, 2, 4)
    sns.boxplot(x="education", y="income10k", data=profiles)
    plt.title("不同学历的收入")
    # 子图 5：收入与资产散点（按学历着色）
    plt.subplot(3, 2, 5)
    sns.scatterplot(x="income10k", y="asset10k", hue="education", data=profiles)
    plt.title("收入与资产散点图（按学历着色）")
    # 子图 6：不同子女数量的负债
    plt.subplot(3, 2, 6)
    sns.boxplot(x="children", y="debt10k", data=profiles)
    plt.title("不同子女数量的负债")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "user_data_vis.png"))
    plt.close()

    # 完成信息
    print(f"M1 完成：数据已保存至 {outdir}。包含的要素：学历、负债、子女等。")


if __name__ == "__main__":
    simulate()
