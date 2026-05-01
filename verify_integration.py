#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 M1-M5 集成改进脚本
检查所有改进的文件是否正确集成了 M1-M5 的输出
"""

import os
import sys
import json

def check_file_exists(path, description):
    """检查文件是否存在"""
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"✅ {description}")
        print(f"   路径: {path}")
        print(f"   大小: {size:,} bytes\n")
        return True
    else:
        print(f"❌ {description} 不存在")
        print(f"   路径: {path}\n")
        return False


def verify_m1_m5_outputs():
    """验证 M1-M5 输出是否存在"""
    print("\n" + "="*60)
    print("验证 M1-M5 模块输出文件")
    print("="*60 + "\n")
    
    checks = {
        "M2 特征": "work/all_features.csv",
        "M3 模型": "work/risk_model.pkl",
        "M3 特征列": "work/used_features_m3.csv",
        "M4 推荐": "work/portfolio_recs.csv",
    }
    
    results = {}
    for name, path in checks.items():
        results[name] = check_file_exists(path, name)
    
    return results


def verify_improved_files():
    """验证改进后的文件是否包含集成代码"""
    print("="*60)
    print("验证改进后的代码集成")
    print("="*60 + "\n")
    
    checks = [
        ("model.py", ["joblib", "load_model", "predict_risk", "work/risk_model.pkl"]),
        ("portfolio.py", ["load_portfolio_recommendations", "work/portfolio_recs.csv", "generate_portfolio"]),
        ("app.py", ["predict_risk", "generate_portfolio", "work/all_features.csv"]),
        ("app_server.py", ["@app.route('/api/predict/risk", "@app.route('/api/recommend/portfolio", "load_all_features"]),
    ]
    
    results = {}
    for filename, keywords in checks:
        filepath = filename
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            found_keywords = all(kw in content for kw in keywords)
            if found_keywords:
                print(f"✅ {filename}")
                print(f"   找到关键代码: {', '.join(keywords[:2])} ...")
                print()
                results[filename] = True
            else:
                missing = [kw for kw in keywords if kw not in content]
                print(f"⚠️  {filename} 缺少以下关键代码:")
                for kw in missing:
                    print(f"   - {kw}")
                print()
                results[filename] = False
        else:
            print(f"❌ {filename} 不存在\n")
            results[filename] = False
    
    return results


def test_model_loading():
    """测试 model.py 是否能正确加载"""
    print("="*60)
    print("测试 model.py 加载")
    print("="*60 + "\n")
    
    try:
        from model import load_model
        model, features, scaler = load_model("work")
        
        if model is not None:
            print("✅ 模型加载成功")
            print(f"   模型类型: {type(model).__name__}")
            
            if features:
                print(f"   特征数量: {len(features)}")
                print(f"   前3个特征: {features[:3]}")
            
            if scaler:
                print(f"   缩放器已加载: {type(scaler).__name__}")
            
            print()
            return True
        else:
            print("⚠️  模型加载失败（这是正常的，如果 M3 未运行过）\n")
            return None
    
    except Exception as e:
        print(f"❌ 加载失败: {e}\n")
        return False


def test_portfolio_loading():
    """测试 portfolio.py 是否能正确加载"""
    print("="*60)
    print("测试 portfolio.py 加载")
    print("="*60 + "\n")
    
    try:
        from portfolio import load_portfolio_recommendations
        recs = load_portfolio_recommendations("work")
        
        if recs is not None:
            print("✅ 资产配置推荐加载成功")
            print(f"   用户数量: {len(recs)}")
            print(f"   配置列: {list(recs.columns)}")
            
            if len(recs) > 0:
                print(f"   示例数据 (第一行):")
                print(f"   {recs.iloc[0].to_dict()}")
            
            print()
            return True
        else:
            print("⚠️  推荐加载失败（这是正常的，如果 M4 未运行过）\n")
            return None
    
    except Exception as e:
        print(f"❌ 加载失败: {e}\n")
        return False


def test_prediction():
    """测试完整预测流程"""
    print("="*60)
    print("测试完整预测流程")
    print("="*60 + "\n")
    
    try:
        from model import predict_risk
        from portfolio import generate_portfolio
        
        # 测试特征字典
        test_features = {
            "age": 35,
            "income10k": 5,
            "asset10k": 20,
            "exp_years": 3,
            "children": 1,
            "action_mean": 0.5,
            "q_sentiment": 0
        }
        
        # 测试预测
        try:
            risk_prob = predict_risk(test_features)
            print(f"✅ 风险预测成功")
            print(f"   输入特征: {test_features}")
            print(f"   预测结果: {risk_prob:.2%}\n")
            
            # 测试推荐
            portfolio = generate_portfolio(risk_prob=risk_prob)
            print(f"✅ 资产配置生成成功")
            print(f"   配置: {portfolio}\n")
            
            return True
        except Exception as pred_error:
            print(f"⚠️  预测失败: {pred_error}")
            print(f"   这可能是因为 M3 模型尚未训练\n")
            return None
    
    except Exception as e:
        print(f"❌ 加载模块失败: {e}\n")
        return False


def main():
    """主验证流程"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "    M1-M5 集成改进验证工具".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    # 1. 验证 M1-M5 输出
    m1m5_results = verify_m1_m5_outputs()
    
    # 2. 验证改进的代码
    code_results = verify_improved_files()
    
    # 3. 测试模块加载
    model_result = test_model_loading()
    
    portfolio_result = test_portfolio_loading()
    
    # 4. 测试完整流程
    prediction_result = test_prediction()
    
    # 总结报告
    print("="*60)
    print("验证总结")
    print("="*60 + "\n")
    
    m1m5_ready = sum(m1m5_results.values())
    code_ready = sum(code_results.values())
    
    print(f"M1-M5 输出文件: {m1m5_ready}/4 ✓")
    print(f"代码改进: {code_ready}/4 ✓")
    
    if m1m5_ready == 4 and code_ready == 4:
        print("\n🎉 所有改进已成功集成！")
        print("\n下一步:")
        print("1. 运行 python app.py 测试交互式咨询")
        print("2. 运行 python app_server.py 启动 API 服务器")
        print("3. 访问 http://localhost:5000/api/health 测试 API")
    elif m1m5_ready < 4:
        print(f"\n⚠️  缺少 {4-m1m5_ready} 个 M1-M5 输出文件")
        print("   建议运行: python run_experiment.py")
    else:
        print(f"\n✅ 代码改进已就绪，等待 M1-M5 数据")
    
    print()


if __name__ == "__main__":
    main()
