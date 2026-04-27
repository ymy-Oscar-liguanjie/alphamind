# -*- coding: utf-8 -*-
"""
投顾助手GUI（中文界面）
- 模拟用户问答：输入问题，一键生成应答与情绪分析
- 即时产出投顾建议：结合已训练模型（若存在）或规则推断，给出资产配置与建议
- 依赖：Python内置tkinter，外加numpy/pandas/joblib（若加载模型）

使用方式：
  python gui.py  # 启动图形界面

也可用于无界面快速验证：
  from gui import demo_compute
  print(demo_compute())
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from dataclasses import dataclass
import numpy as np
import pandas as pd

try:
    import joblib
except Exception:  # 允许无joblib
    joblib = None

# ----------------------------- 数据结构 -----------------------------
@dataclass
class UserInput:
    age: int
    education: str
    income10k: float
    asset10k: float
    debt10k: float
    children: int
    exp_years: int
    action_mean: float  # 交易倾向（-1卖出，0观望，1买入）
    q_text: str
    q_sentiment: int  # -1/0/1


# ----------------------------- 情绪分析 -----------------------------
def analyze_sentiment(text: str) -> int:
    text = (text or "").lower()
    pos_words = ["盈利", "上涨", "看好", "长期", "稳定", "增长", "机会", "低估", "利好", "乐观"]
    neg_words = ["亏损", "下跌", "担心", "风险", "波动", "崩盘", "踩雷", "不确定", "利空", "悲观"]
    pos = sum(w in text for w in pos_words)
    neg = sum(w in text for w in neg_words)
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def mock_answer(text: str) -> str:
    if not text.strip():
        return "您好，您可以提问如：‘现在是否适合定投？’ 我将结合您的风险偏好给出建议。"
    return (
        "感谢提问。我会结合您的画像、交易倾向与情绪，为您提供‘分散配置 + 纪律投资’的策略。"
        "若追求长期稳健，建议控制单次仓位，并使用定投平滑波动。"
    )


# ----------------------------- 风险预测（模型或规则） -----------------------------
def load_model_and_features(workdir: str = "work"):
    model, used_cols = None, None
    model_path = os.path.join(workdir, "risk_model.pkl")
    feat_path = os.path.join(workdir, "used_features_m3.csv")
    if os.path.exists(model_path) and joblib is not None:
        try:
            model = joblib.load(model_path)
        except Exception:
            model = None
    if os.path.exists(feat_path):
        try:
            used_cols = list(pd.read_csv(feat_path)["feature"].astype(str))
        except Exception:
            used_cols = None
    return model, used_cols


def predict_risk(user: UserInput, model=None, used_cols=None):
    # 若有已训练模型，则按其特征构造向量；否则走规则。
    base = {
        "age": user.age,
        "income10k": user.income10k,
        "asset10k": user.asset10k,
        "exp_years": user.exp_years,
        "action_mean": user.action_mean,
        "q_sentiment": user.q_sentiment,
        # 若模型包含下列列名，统一补零（GNN/时序特征没有单人图/序列可直接置0）
        "action_ema_10": 0.0, "action_ema_30": 0.0, "action_vol_30": 0.0,
        "action_trend_30": 0.0, "action_mkt_corr_30": 0.0, "buy_ratio_30": 0.0,
        "action_mean_gnn1": 0.0, "q_sentiment_gnn1": 0.0, "action_ema_10_gnn1": 0.0,
        "action_ema_30_gnn1": 0.0, "action_trend_30_gnn1": 0.0,
        "action_mean_gnn2": 0.0, "q_sentiment_gnn2": 0.0, "action_ema_10_gnn2": 0.0,
        "action_ema_30_gnn2": 0.0, "action_trend_30_gnn2": 0.0,
    }
    if model is not None and used_cols:
        X = np.array([[base.get(c, 0.0) for c in used_cols]], dtype=float)
        try:
            prob = float(model.predict_proba(X)[0, 1])
            pred = int(prob >= 0.5)
            return prob, pred, used_cols
        except Exception:
            pass

    # 规则兜底（与M1相近）
    score = 0.0
    score += 0.2 if user.age < 30 else 0.0
    score += 0.2 if user.income10k > 20 else 0.0
    score += 0.2 if user.asset10k > 100 else 0.0
    score += 0.2 if user.exp_years > 3 else 0.0
    score += 0.1 if user.education in ("本科", "硕士及以上") else 0.0
    score += 0.1 if user.children == 0 else 0.0
    score += 0.1 * user.action_mean  # 行为越偏买入越进取
    score += 0.05 * user.q_sentiment  # 情绪偏正面略微进取
    prob = float(np.clip(score, 0, 1))
    pred = int(prob >= 0.5)
    return prob, pred, [k for k in base.keys()]


# ----------------------------- 资产配置与投顾建议 -----------------------------
def mean_variance(mu, sigma, risk_aversion=2.0):
    inv_sigma = np.linalg.inv(sigma)
    w = (inv_sigma @ mu) / max(1e-8, risk_aversion)
    w = np.clip(w, 0, None)
    s = w.sum()
    return w / s if s > 0 else np.ones_like(w) / len(w)


def build_portfolio(risk_prob: float):
    assets = ["股票", "债券", "基金", "REITs", "商品", "现金"]
    mu = np.array([0.08, 0.03, 0.06, 0.045, 0.05, 0.01])
    rng = np.random.default_rng(42)
    base = rng.standard_normal((6, 6))
    sigma = (base @ base.T) / 100.0
    risk_aversion = 4.0 - 2.0 * float(risk_prob)  # 2~4之间
    w = mean_variance(mu, sigma, risk_aversion)
    portfolio_str = ", ".join([f"{a}: {x:.1%}" for a, x in zip(assets, w)])
    return assets, w, portfolio_str


def generate_advice(user: UserInput, risk_prob: float, risk_pred: int, portfolio_str: str) -> str:
    debt_ratio = user.debt10k / user.asset10k if user.asset10k > 0 else 0.0
    is_near_retirement = user.age >= 55
    is_new = user.exp_years < 2
    risk_level_str = '进取型' if risk_pred==1 else '稳健型'

    # --- Helper: parse portfolio string to (names, percents) ---
    def parse_portfolio(p_str):
        try:
            parts = [x.strip() for x in p_str.split(',') if x.strip()]
            names = []
            percents = []
            for it in parts:
                name, pct = it.split(':')
                names.append(name.strip())
                percents.append(float(pct.strip().strip('%')))
            return names, percents
        except Exception:
            return [], []

    # --- Helper: colorful stacked bar (emoji) ---
    def get_portfolio_bar(names, percents, width=30):
        colors = ['🟩', '🟦', '🟨', '🟧', '🟪', '⬜️']
        if not percents:
            return ''
        bar = ''
        for i, p in enumerate(percents):
            block_count = max(1, int(p / 100 * width))
            bar += colors[i % len(colors)] * block_count
        return bar

    # --- Helper: mini bar per line ---
    def mini_bar(p, width=20, fill='█', empty='░'):
        filled = int(round(p / 100 * width))
        return fill * filled + empty * (width - filled)

    # --- Helper: risk gauge (0-10) ---
    def risk_gauge(prob):
        # 进取概率越高，刻度越靠右
        n = 10
        pos = int(round(prob * n))
        gauge = '[' + '█' * pos + '░' * (n - pos) + f'] {prob:.0%}  ({'进取' if prob>=0.5 else '稳健'})'
        return gauge

    names, percents = parse_portfolio(portfolio_str)
    portfolio_bar = get_portfolio_bar(names, percents)

    # --- Header ---
    width = 64
    line_top    = '╔' + '═' * width + '╗'
    line_middle = '╠' + '═' * width + '╣'
    line_bottom = '╚' + '═' * width + '╝'

    title = '智能投顾分析报告'
    date_str = '2025-11-11'  # 如需动态日期可改为当前日期

    advice = [
        line_top,
        f"║{title:^{width}}║",
        line_middle,
        f"║ 报告日期: {date_str:<18} 用户类型: {risk_level_str:<6} 进取概率: {risk_prob:>6.1%} ║".ljust(width+2,' '),
        line_bottom,
        '',
        '【核心评估摘要】',
        '─' * 28,
        f"· 用户画像：{user.age}岁｜{user.education}｜{user.exp_years}年投资经验",
        f"· 风险偏好：{risk_level_str}  ｜ 概率刻度：{risk_gauge(risk_prob)}",
        f"· 资产配置：{portfolio_str}",
    ]

    if portfolio_bar:
        # legend
        legend = []
        color_symbols = ['🟩','🟦','🟨','🟧','🟪','⬜️']
        for i, n in enumerate(names[:6]):
            legend.append(f"{color_symbols[i]} {n}")
        advice.append('  ' + portfolio_bar)
        advice.append('  图例：' + ' ｜ '.join(legend))

    # --- Allocation table ---
    if names and percents:
        advice.append('')
        advice.append('【配置明细（按比例排序）】')
        advice.append('─' * 28)
        # sort by percent desc
        order = sorted(range(len(percents)), key=lambda i: percents[i], reverse=True)
        advice.append('资产    | 比例   | 配置条形图')
        advice.append('--------+--------+----------------------')
        for i in order:
            n, p = names[i], percents[i]
            advice.append(f"{n:<6} | {p:>5.1f}% | {mini_bar(p, 22)}")

    # --- 第一部分：详细评估 ---
    advice.extend([
        '',
        '【第一部分：详细评估】',
        '─' * 28,
        '1) 财务状况',
        f"   - 年收入：{user.income10k:.1f}万 ｜ 总资产：{user.asset10k:.1f}万 ｜ 负债：{user.debt10k:.1f}万",
        f"   - 债务比率：{debt_ratio:.1%}",
        '2) 市场洞察',
        f"   - 情绪判断：{'😊 正面' if user.q_sentiment==1 else '😟 负面' if user.q_sentiment==-1 else '😐 中性'}",
        f"   - 交易倾向：{'🔼 偏买入' if user.action_mean > 0.1 else '🔽 偏卖出' if user.action_mean < -0.1 else '⏸️ 观望'}",
    ])

    # --- 第二部分：行动策略建议 ---
    advice.append('')
    advice.append('【第二部分：行动策略建议】')
    advice.append('─' * 28)

    # 2.1 组合策略
    advice.append('2.1 投资组合策略')
    if risk_pred == 1:  # 进取型
        if is_new:
            advice.append('   - 新手入门：从宽基指数基金（如沪深300）起步，逐步加深。')
        else:
            advice.append('   - 积极增长：采用“核心-卫星”策略，30-40%主动权益 + 20-30%行业ETF（科技/新能源等）。')
        if user.asset10k > 500:
            advice.append('   - 资产增厚：规模较大，可配10-15%另类资产（REITs、黄金）提升分散度与韧性。')
    else:  # 稳健型
        if debt_ratio > 0.3:
            advice.append(f"   - 稳健为先：负债率({debt_ratio:.0%})偏高，建议50%+配置低波动产品（国债/货币基金），优先降杠杆。")
        else:
            advice.append('   - 均衡配置：构建“固收+”组合，40-50%中短债为基石，搭配20-30%高股息蓝筹，稳中求进。')

    # 2.2 风险管理
    advice.append('')
    advice.append('2.2 风险管理计划')
    if debt_ratio > 0.5:
        advice.append('   - [高负债预警] 负债率>50%为重要红线，建议每月至少用20%收入降杠杆，防范流动性风险。')
    else:
        advice.append(f"   - 财务健康：当前负债/资产比({debt_ratio:.0%})处于舒适区。")

    emergency_need = 6 * (user.debt10k + max(5, user.income10k / 12 * 0.5))  # 6个月(负债+生活开支)
    if user.asset10k * 0.1 < emergency_need:
        gap = emergency_need - user.asset10k * 0.1
        advice.append(f"   - [应急资金不足] 建议储备{emergency_need:.0f}万元应急金，当前缺口约{gap:.0f}万，这是投资的“安全垫”。")
    else:
        advice.append('   - 后盾坚实：应急资金充足，为投资计划保驾护航。')

    # --- 第三部分：长期视角与个人成长 ---
    advice.append('')
    advice.append('【第三部分：长期视角与个人成长】')
    advice.append('─' * 28)

    # 3.1 人生阶段规划
    advice.append('3.1 人生阶段规划')
    if is_near_retirement:
        advice.append('   - [退休准备] 临近退休，建议启动“防守模式”，未来5年每年将权益仓位下调5-10%。')
    elif user.age < 35:
        advice.append('   - [黄金投资期] 年轻是最大资本！建议坚持定投（每月收入的15-20%），让复利为你工作。')

    if user.children > 0:
        advice.append(f"   - [子女教育] 为{user.children}个子女规划约{user.children*5}万元教育金，可选目标日期基金/教育金保险。")

    # 3.2 投资行为
    advice.append('')
    advice.append('3.2 投资心法')
    if is_new:
        advice.append('   - [新手修炼] 先用模拟盘练手，小额慢行，把控情绪、避免冲动交易。')
    else:
        advice.append('   - [纪律为王] 设定并执行止盈（+20%）与止损（-10%）纪律。')

    if user.education in ('本科', '硕士及以上'):
        advice.append('   - [认知驱动] 发挥研究优势，深耕1-2个行业，建立能力圈。')
    else:
        advice.append('   - [终身学习] 持续学习理财知识，不断迭代投资系统。')

    # --- Footer ---
    advice.append('')
    advice.append(line_top)
    disclaimer = '免责声明：本报告仅为演示用途，不构成任何投资建议'
    advice.append(f"║{disclaimer:^{width}}║")
    advice.append(line_bottom)

    return "\n".join(advice)


# ----------------------------- GUI 视图 -----------------------------
class AdvisorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AIphaMind：智能投顾")
        try:
            self.root.iconbitmap(default='')
        except Exception:
            pass
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        self._build_ui()
        self.model, self.used_cols = load_model_and_features("work")

    def _section(self, parent, title):
        frm = ttk.LabelFrame(parent, text=title, padding=(10, 10))
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        return frm

    def _build_ui(self):
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)

        # 标题区
        title = ttk.Label(container, text="智能投顾助手", anchor='center',
                          font=("Microsoft YaHei", 18, "bold"))
        title.pack(fill=tk.X, pady=(12, 0))
        subtitle = ttk.Label(container, text="画像 × 问答情绪 × 风险评估 × 资产配置", anchor='center',
                             font=("Microsoft YaHei", 11))
        subtitle.pack(fill=tk.X, pady=(0, 8))

        body = ttk.Frame(container)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 左侧：用户画像与提问
        frm_user = self._section(left, "👤 用户画像")
        self.vars = {}
        fields = [
            ("年龄", "age", [str(x) for x in range(18, 81)]),
            ("学历", "education", ["高中及以下", "大专", "本科", "硕士及以上"]),
            ("年收入(万)", "income10k", [str(x) for x in range(1, 1001, 2)]),
            ("总资产(万)", "asset10k", [str(x) for x in range(0, 10001, 10)]),
            ("总负债(万)", "debt10k", [str(x) for x in range(0, 1001, 5)]),
            ("子女人数", "children", [str(x) for x in range(0, 6)]),
            ("投资经验(年)", "exp_years", [str(x) for x in range(0, 51)]),
            ("交易倾向", "action_mean", ["-1 (卖出)", "-0.5", "0 (观望)", "0.5", "1 (买入)"]),
        ]
        for i, (label, key, values) in enumerate(fields):
            ttk.Label(frm_user, text=label).grid(row=i, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar()
            combo = ttk.Combobox(frm_user, textvariable=var, values=values)
            combo.grid(row=i, column=1, sticky=tk.EW, pady=2)
            combo.set(values[len(values) // 3])
            self.vars[key] = var

        frm_q = self._section(left, "💬 用户提问")
        self.vars["q_text"] = tk.StringVar()
        q_entry = ttk.Entry(frm_q, textvariable=self.vars["q_text"], width=40)
        q_entry.pack(fill=tk.X, expand=True, pady=5)
        self.vars["q_text"].set("最近市场波动有点大，我应该怎么办？")

        self.btn_compute = ttk.Button(left, text="生成投顾建议", command=self._compute_and_display)
        self.btn_compute.pack(fill=tk.X, padx=10, pady=10, ipady=4)

        # 右侧：结果展示
        frm_answer = self._section(right, "🤖 模拟应答与情绪分析")
        self.lbl_answer = ttk.Label(frm_answer, text="...", wraplength=400, justify=tk.LEFT)
        self.lbl_answer.pack(fill=tk.X, pady=(0, 5))
        self.lbl_sentiment = ttk.Label(frm_answer, text="情绪: -", font=("", 10, "bold"))
        self.lbl_sentiment.pack(fill=tk.X)

        frm_advice = self._section(right, "📄 智能投顾分析报告")
        self.advice_text = scrolledtext.ScrolledText(frm_advice, wrap=tk.WORD, height=25,
                                                     font=("Courier New", 9))
        self.advice_text.pack(fill=tk.BOTH, expand=True)
        self.advice_text.insert(tk.END, "点击“生成”按钮，获取您的专属报告...")
        self.advice_text.config(state=tk.DISABLED)

    def _get_user_input(self) -> UserInput:
        try:
            return UserInput(
                age=int(self.vars["age"].get()),
                education=self.vars["education"].get(),
                income10k=float(self.vars["income10k"].get()),
                asset10k=float(self.vars["asset10k"].get()),
                debt10k=float(self.vars["debt10k"].get()),
                children=int(self.vars["children"].get()),
                exp_years=int(self.vars["exp_years"].get()),
                action_mean=float(self.vars["action_mean"].get().split(" ")[0]),
                q_text=self.vars["q_text"].get(),
                q_sentiment=analyze_sentiment(self.vars["q_text"].get()),
            )
        except (ValueError, TypeError) as e:
            messagebox.showerror("输入错误", f"请检查输入字段，确保均为有效数值。\n错误: {e}")
            return None

    def _compute_and_display(self):
        user = self._get_user_input()
        if user is None:
            return

        # 1. 模拟应答与情绪
        answer = mock_answer(user.q_text)
        sentiment_map = {-1: "😟 负面", 0: "😐 中性", 1: "😊 正面"}
        self.lbl_answer.config(text=answer)
        self.lbl_sentiment.config(text=f"情绪: {sentiment_map[user.q_sentiment]}")

        # 2. 风险预测
        risk_prob, risk_pred, _ = predict_risk(user, self.model, self.used_cols)

        # 3. 资产配置与建议
        assets, w, portfolio_str = build_portfolio(risk_prob)
        advice_all = generate_advice(user, risk_prob, risk_pred, portfolio_str)

        # 4. 显示
        self.advice_text.config(state=tk.NORMAL)
        self.advice_text.delete("1.0", tk.END)
        self.advice_text.insert(tk.END, advice_all)
        self.advice_text.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = AdvisorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
