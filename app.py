import os
import pandas as pd
import numpy as np
from llm_client import ask_llm, ask_llm_with_history



from model import predict_risk, load_model
from portfolio import generate_portfolio, load_portfolio_recommendations
from storage import (save_chat, get_user_history, get_latest_record, get_all_users, 
                     delete_user_records, create_session, add_message, get_session_messages,
                     update_session_risk, get_session_detail, get_user_sessions, delete_session)

def interactive_consultation():
    """多轮对话投资咨询模式（新）"""
    print("\n" + "="*50)
    print("欢迎使用 AlphaMind 投顾咨询系统")
    print("（输入 'exit' 或 'quit' 结束对话）")
    print("="*50 + "\n")
    
    user_id = input("👤 请输入你的用户ID: ")
    
    # 创建新的对话会话
    session_id = create_session(user_id, f"咨询-{user_id}")
    print(f"✅ 已创建新的咨询会话\n")
    
    # 初始化对话历史
    messages = []
    
    # 第一步：投顾主动打招呼并了解用户
    initial_greeting = ask_llm_with_history([
        {"role": "user", "content": "你好"}
    ])
    
    print(f"💼 投顾顾问: {initial_greeting}\n")
    add_message(session_id, user_id, "assistant", initial_greeting)
    messages.append({"role": "assistant", "content": initial_greeting})
    
    # 多轮对话
    turn = 0
    max_turns = 15  # 最多15轮对话
    
    while turn < max_turns:
        user_input = input("👤 你: ").strip()
        
        # 退出条件
        if user_input.lower() in ['exit', 'quit', '退出']:
            print("\n📋 准备生成最终建议...\n")
            
            # 让AI生成最终建议
            final_prompt = "请根据我们的对话，为我生成一份详细的投资建议报告。包括：1.我的风险等级\n2.推荐的资产配置\n3.具体的投资方向\n4.风险提示"
            messages.append({"role": "user", "content": final_prompt})
            
            final_advice = ask_llm_with_history(messages)
            add_message(session_id, user_id, "user", final_prompt)
            add_message(session_id, user_id, "assistant", final_advice)
            
            print(f"💼 投顾顾问:\n{final_advice}\n")
            
            # 保存会话
            save_chat(user_id, "咨询会话", final_advice, "未分类", "dynamic")
            print("✅ 咨询会话已保存\n")
            break
        
        if not user_input:
            print("⚠️  请输入内容\n")
            continue
        
        # 添加用户消息到历史
        add_message(session_id, user_id, "user", user_input)
        messages.append({"role": "user", "content": user_input})
        
        # 获取AI回复
        print("💭 正在分析...\n")
        assistant_reply = ask_llm_with_history(messages)
        
        if "错误" in assistant_reply or "失败" in assistant_reply:
            print(f"❌ {assistant_reply}\n")
            break
        
        # 添加AI回复到历史
        add_message(session_id, user_id, "assistant", assistant_reply)
        messages.append({"role": "assistant", "content": assistant_reply})
        
        print(f"💼 投顾顾问: {assistant_reply}\n")
        turn += 1
    
    if turn >= max_turns:
        print("⚠️  已达到最大对话轮数，请输入 'exit' 结束对话")
    
    print("📋 咨询结束\n")

def run_demo():
    user_id = input("输入用户ID: ")
    user_input = input("请输入你的情况: ")

    print("\n[处理中...]\n")

    try:
        # 第1步：从 M2 数据加载用户特征
        print("第1步: 加载用户特征...")
        all_features_path = "work/all_features.csv"
        if os.path.exists(all_features_path):
            all_features = pd.read_csv(all_features_path)
            user_data = all_features[all_features["user_id"] == int(user_id)]
            
            if len(user_data) == 0:
                print(f"⚠️  用户 {user_id} 在特征数据中不存在，使用示例特征")
                features_dict = {"age": 35, "income10k": 5, "asset10k": 20, "exp_years": 3, "children": 1}
            else:
                # 将用户数据转换为字典（包含所有特征）
                features_dict = user_data.iloc[0].to_dict()
                print(f"✅ 已加载用户 {user_id} 的特征信息")
        else:
            print(f"⚠️  特征文件不存在，使用示例特征")
            features_dict = {"age": 35, "income10k": 5, "asset10k": 20, "exp_years": 3, "children": 1}
        
        # 第2步：使用 M3 模型预测风险
        print("\n第2步: 使用 M3 模型预测风险等级...")
        try:
            risk_prob = predict_risk(features_dict, workdir="work")
            print(f"✅ 风险概率: {risk_prob:.2%}")
        except Exception as e:
            print(f"⚠️  M3 预测失败: {e}，使用规则推断")
            risk_prob = 0.5
        
        # 第3步：使用 M4 资产配置推荐
        print("\n第3步: 使用 M4 生成资产配置...")
        try:
            portfolio = generate_portfolio(user_id=int(user_id), risk_prob=risk_prob, workdir="work")
            print(f"✅ 资产配置已生成: {portfolio}")
        except Exception as e:
            print(f"⚠️  M4 推荐失败: {e}，使用规则推断")
            portfolio = generate_portfolio(user_id=None, risk_prob=risk_prob, workdir="work")
        
        # 第4步：LLM 增强建议生成
        print("\n第4步: 使用 LLM 生成投顾建议...")
        portfolio_str = ", ".join([f"{k}: {v:.1f}%" for k, v in portfolio.items()])
        final_prompt = f"""基于用户情况和数据分析结果，生成投资建议：

用户输入: {user_input}
风险概率: {risk_prob:.2%}
资产配置建议: {portfolio_str}

请生成详细的个性化投资建议，包括：
1. 风险评估
2. 资产配置解释
3. 具体投资方向
4. 风险提示"""
        
        answer = ask_llm(final_prompt)
        
        # 检查是否出错
        if "错误" in answer or "失败" in answer:
            print(f"❌ 建议生成失败: {answer}")
            return

        # 保存会话
        save_chat(user_id, user_input, answer, f"{risk_prob:.2%}", portfolio_str)

        print("\n===== 投顾建议 =====")
        print(answer)
        print("\n✅ 建议已保存")

    except Exception as e:
        print(f"❌ 程序出错: {e}")
        import traceback
        traceback.print_exc()
        return

def view_history():
    """查看用户历史记录"""
    print("\n===== 查看历史记录 =====\n")
    
    user_id = input("输入用户ID: ")
    
    # 获取最新记录
    latest = get_latest_record(user_id)
    
    if not latest:
        print(f"❌ 用户 {user_id} 没有历史记录\n")
        return
    
    question, answer, risk, portfolio, time = latest
    
    print(f"\n📅 最新建议时间: {time}")
    print(f"📝 用户问题: {question}")
    print(f"⚠️  风险等级: {risk}")
    print(f"💼 资产配置: {portfolio}")
    print(f"\n===== 投顾建议 =====")
    print(answer)
    print()

def view_all_history():
    """查看用户所有历史记录"""
    print("\n===== 查看所有历史记录 =====\n")
    
    user_id = input("输入用户ID: ")
    history = get_user_history(user_id)
    
    if not history:
        print(f"❌ 用户 {user_id} 没有历史记录\n")
        return
    
    print(f"\n📊 用户 {user_id} 的 {len(history)} 条历史记录:\n")
    
    for idx, (question, risk, portfolio, time) in enumerate(history, 1):
        print(f"[{idx}] 时间: {time}")
        print(f"    问题: {question}")
        print(f"    风险: {risk} | 配置: {portfolio}\n")

def view_all_users():
    """查看所有用户"""
    print("\n===== 所有用户 =====\n")
    
    users = get_all_users_with_counts()
    
    if not users:
        print("❌ 没有用户记录\n")
        return
    
    for user_id, count in users:
        print(f"👤 {user_id}: {count} 条记录")
    print()

def delete_history():
    """删除用户历史记录"""
    print("\n===== 删除历史记录 =====\n")
    
    user_id = input("输入用户ID: ")
    confirm = input(f"确定要删除用户 {user_id} 的所有记录吗？(yes/no): ")
    
    if confirm.lower() == "yes":
        delete_user_records(user_id)
        print(f"✅ 已删除用户 {user_id} 的所有记录\n")
    else:
        print("❌ 取消删除\n")

def main_menu():
    """主菜单"""
    while True:
        print("\n" + "="*35)
        print("    AlphaMind 投顾助手")
        print("="*35)
        print("1. 💬 多轮对话咨询（推荐！）")
        print("2. 快速生成建议")
        print("3. 📖 查看最新建议")
        print("4. 📚 查看所有历史记录")
        print("5. 👥 查看所有用户")
        print("6. 🗑️  删除用户记录")
        print("0. 👋 退出")
        print("="*35)
        
        choice = input("请选择操作 (0-6): ")
        
        if choice == "1":
            interactive_consultation()
        elif choice == "2":
            run_demo()
        elif choice == "3":
            view_history()
        elif choice == "4":
            view_all_history()
        elif choice == "5":
            view_all_users()
        elif choice == "6":
            delete_history()
        elif choice == "0":
            print("\n👋 感谢使用 AlphaMind，再见！\n")
            break
        else:
            print("\n❌ 无效选择，请重试\n")

if __name__ == "__main__":
    main_menu()
