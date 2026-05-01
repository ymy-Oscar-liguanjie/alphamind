"""资产配置推荐模块
集成 M4 输出的个性化资产配置
"""
import os
import pandas as pd

# 全局推荐缓存
_portfolio_recs = None

def load_portfolio_recommendations(workdir="work"):
    """加载 M4 生成的资产配置推荐"""
    global _portfolio_recs
    
    if _portfolio_recs is not None:
        return _portfolio_recs
    
    try:
        recs_path = os.path.join(workdir, "portfolio_recs.csv")
        if not os.path.exists(recs_path):
            raise FileNotFoundError(f"推荐文件不存在: {recs_path}\n请先运行 M4_portfolio_recommender.py")
        
        _portfolio_recs = pd.read_csv(recs_path)
        _portfolio_recs = _portfolio_recs.set_index("user_id")  # 以user_id为索引
        print(f"✅ 已加载 {len(_portfolio_recs)} 个用户的资产配置推荐")
        
        return _portfolio_recs
    
    except Exception as e:
        print(f"❌ 加载推荐配置失败: {e}")
        return None

def generate_portfolio(user_id=None, risk_prob=None, workdir="work"):
    """生成或查询资产配置
    
    优先级：
    1. 如果提供 user_id，从 M4 推荐中直接查询
    2. 否则根据 risk_prob 使用规则生成
    
    Args:
        user_id: 用户ID（可选）
        risk_prob: 风险概率 0-1（可选，若不提供user_id则需要此参数）
        workdir: 工作目录
        
    Returns:
        dict: 资产配置 {资产名: 权重百分比}
    """
    # 首先尝试从M4推荐中查询
    if user_id is not None:
        portfolio_recs = load_portfolio_recommendations(workdir)
        if portfolio_recs is not None and user_id in portfolio_recs.index:
            try:
                row = portfolio_recs.loc[user_id]
                # portfolio 列包含配置字符串，其他列为具体权重
                assets = ["股票", "债券", "基金", "REITs", "大宗商品", "现金"]
                config = {}
                for asset in assets:
                    if asset in row.index:
                        config[asset] = float(row[asset]) * 100  # 转为百分比
                
                if config:
                    print(f"✅ 使用 M4 推荐配置 (user_id: {user_id})")
                    return config
            except Exception as e:
                print(f"⚠️  查询推荐配置失败: {e}")
    
    # 降级到规则推荐（基于风险概率）
    if risk_prob is None:
        raise ValueError("必须提供 user_id 或 risk_prob")
    
    # 风险概率 -> 风险等级 -> 资产配置
    if risk_prob < 0.33:
        # 保守型
        return {
            "债券": 60,
            "股票": 15,
            "基金": 10,
            "REITs": 5,
            "大宗商品": 5,
            "现金": 5
        }
    elif risk_prob < 0.67:
        # 稳健型
        return {
            "债券": 40,
            "股票": 35,
            "基金": 12,
            "REITs": 5,
            "大宗商品": 5,
            "现金": 3
        }
    else:
        # 激进型
        return {
            "债券": 20,
            "股票": 55,
            "基金": 15,
            "REITs": 5,
            "大宗商品": 3,
            "现金": 2
        }

if __name__ == "__main__":
    # 测试：加载推荐
    recs = load_portfolio_recommendations()
    if recs is not None:
        print(f"推荐配置列数: {len(recs.columns)}")
        print(f"推荐配置列名: {list(recs.columns)}")
        if len(recs) > 0:
            print(f"\n第一个用户的推荐:")
            print(recs.iloc[0])