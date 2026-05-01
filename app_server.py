
"""
AlphaMind Flask后端服务
将多轮对话咨询程序通过API暴露给Web前端
完整集成M1-M5的数据流和模型预测
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
from datetime import datetime
import uuid
import os
import pandas as pd
import numpy as np


from llm_client import ask_llm_with_history, ask_llm
from model import predict_risk, load_model
from portfolio import generate_portfolio, load_portfolio_recommendations
from storage import (create_session, add_message, get_session_messages,
                     get_user_sessions, delete_session)


app = Flask(__name__)
CORS(app)

# ========== 会话管理 ==========

# 内存中保存当前用户的对话会话及风险数据
user_sessions = {}

# 加载M2特征数据（全局）
_all_features = None

def load_all_features():
    """加载M2生成的所有特征"""
    global _all_features
    if _all_features is None:
        try:
            features_path = "work/all_features.csv"
            if os.path.exists(features_path):
                _all_features = pd.read_csv(features_path)
                _all_features = _all_features.set_index("user_id")
                print(f"✅ 已加载 {len(_all_features)} 个用户的特征数据")
        except Exception as e:
            print(f"⚠️  加载特征数据失败: {e}")
    return _all_features

# ========== 预测和推荐端点 ==========

@app.route('/api/predict/risk', methods=['POST'])
def predict_user_risk():
    """基于用户特征预测风险概率（M3集成）"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        features_dict = data.get('features', {})
        
        if not features_dict and not user_id:
            return jsonify({
                'success': False,
                'error': '必须提供 features 或 user_id'
            }), 400
        
        # 优先从特征数据中加载
        if user_id:
            all_features = load_all_features()
            if all_features is not None and user_id in all_features.index:
                features_dict = all_features.loc[user_id].to_dict()
                print(f"✅ 使用M2特征数据预测用户 {user_id} 的风险")
        
        # 调用M3模型预测
        risk_prob = predict_risk(features_dict, workdir="work")
        
        return jsonify({
            'success': True,
            'risk_prob': float(risk_prob),
            'risk_level': '保守型' if risk_prob < 0.33 else ('稳健型' if risk_prob < 0.67 else '激进型')
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/recommend/portfolio', methods=['POST'])
def recommend_portfolio():
    """基于用户ID或风险概率推荐资产配置（M4集成）"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        risk_prob = data.get('risk_prob')
        
        if not user_id and risk_prob is None:
            return jsonify({
                'success': False,
                'error': '必须提供 user_id 或 risk_prob'
            }), 400
        
        # 调用M4推荐
        portfolio = generate_portfolio(
            user_id=int(user_id) if user_id else None,
            risk_prob=risk_prob,
            workdir="work"
        )
        
        return jsonify({
            'success': True,
            'portfolio': portfolio,
            'portfolio_str': ", ".join([f"{k}: {v:.1f}%" for k, v in portfolio.items()])
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analysis/end-to-end', methods=['POST'])
def end_to_end_analysis():
    """端到端分析：从用户特征到风险预测到资产配置（M1-M5集成）"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        features_dict = data.get('features', {})
        （带M3-M5集成）"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'unknown')
        
        if session_id not in user_sessions:
            return jsonify({
                'success': False,
                'error': '会话不存在'
            }), 404
        
        # 获取当前会话的消息历史
        messages = user_sessions[session_id]['messages'].copy()
        
        # 尝试从M2特征数据加载用户信息
        all_features = load_all_features()
        user_features = {}
        risk_prob = None
        portfolio = None
        
        if all_features is not None and user_id != 'unknown':
            try:
                if user_id in all_features.index:
                    user_features = all_features.loc[user_id].to_dict()
                    # 使用M3预测风险
                    risk_prob = predict_risk(user_features, workdir="work")
                    # 使用M4推荐资产配置
                    portfolio = generate_portfolio(user_id=user_id, risk_prob=risk_prob, workdir="work")
                else:
                    # 尝试用整数user_id
                    try:
                        user_id_int = int(user_id)
                        if user_id_int in all_features.index:
                            user_features = all_features.loc[user_id_int].to_dict()
                            risk_prob = predict_risk(user_features, workdir="work")
                            portfolio = generate_portfolio(user_id=user_id_int, risk_prob=risk_prob, workdir="work")
                    except:
                        pass
            except Exception as e:
                print(f"⚠️  M3/M4处理失败: {e}")
        
        # 生成最终建议
        final_prompt = """请根据我们的对话，为我生成一份详细的投资建议报告。包括：

1. **我的风险等级**（保守型/稳健型/平衡型/激进型）
2. **推荐的资产配置**（详细百分比）
3. **具体的投资方向**（股票、债券、基金、其他）
4. **每个方向的建议**（选择哪些产品）
5. **实施策略**（如何进行，注意事项）
6. **风险提示**（可能的风险和应对方法）

请确保建议具体、可操作、并针对我的具体情况。"""
        
        # 如果有M3/M4的结果，注入到LLM上下文中
        if risk_prob is not None and portfolio is not None:
            portfolio_str = ", ".join([f"{k}: {v:.1f}%" for k, v in portfolio.items()])
            context_prompt = f"\n\n[数据分析结果]\n风险概率: {risk_prob:.2%}\n推荐配置: {portfolio_str}\n\n{final_prompt}"
            final_prompt = context_prompt
        
        messages.append({"role": "user", "content": final_prompt})
        final_advice = ask_llm_with_history(messages)
        
        add_message(session_id, user_id, "user", final_prompt)
        add_message(session_id, user_id, "assistant", final_advice)
        
        # 保存M3/M4结果到会话中
        user_sessions[session_id]['risk_prob'] = risk_prob
        user_sessions[session_id]['portfolio'] = portfolio
        
        return jsonify({
            'success': True,
            'final_advice': final_advice,
            'session_id': session_id,
            'risk_prob': float(risk_prob) if risk_prob else None,
            'portfolio': portfolio
5. 风险提示"""
        
        llm_advice = ask_llm(analysis_prompt)
        
        return jsonify({
            'success': True,
            'analysis': {
                'risk_prob': float(risk_prob),
                'risk_level': '保守型' if risk_prob < 0.33 else ('稳健型' if risk_prob < 0.67 else '激进型'),
                'portfolio': portfolio,
                'portfolio_str': portfolio_str,
                'llm_advice': llm_advice
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/session/create', methods=['POST'])
def create_user_session():
    """创建新的对话会话"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', f'web_user_{uuid.uuid4().hex[:8]}')
        
        # 创建会话
        session_id = create_session(user_id, f"Web咨询-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        # 保存到内存
        user_sessions[session_id] = {
            'user_id': user_id,
            'messages': [],
            'created_at': datetime.now().isoformat()
        }
        
        # 初始化对话
        initial_greeting = ask_llm_with_history([
            {"role": "user", "content": "你好"}
        ])
        
        # 保存到数据库
        add_message(session_id, user_id, "assistant", initial_greeting)
        user_sessions[session_id]['messages'] = [
            {"role": "assistant", "content": initial_greeting}
        ]
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'initial_message': initial_greeting
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/session/<session_id>/message', methods=['POST'])
def send_message(session_id):
    """发送用户消息，获取投顾回复"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        user_id = data.get('user_id', 'unknown')
        60)
    print("AlphaMind API Server 启动中（完整M1-M5集成版本）")
    print("=" * 60)
    print("📍 地址: http://localhost:5000")
    print("\n📋 主要API端点:")
    print("   会话管理:")
    print("   - POST /api/session/create - 创建会话")
    print("   - POST /api/session/<id>/message - 发送消息")
    print("   - POST /api/session/<id>/finalize - 生成最终建议（含M3/M4）")
    print("   - GET  /api/session/<id> - 获取会话信息")
    print("   - DELETE /api/session/<id> - 删除会话")
    print("\n   数据分析（M1-M5集成）:")
    print("   - POST /api/predict/risk - M3风险预测")
    print("   - POST /api/recommend/portfolio - M4资产配置推荐")
    print("   - POST /api/analysis/end-to-end - 完整分析流程")
    print("   - GET  /api/user/<id>/sessions - 用户会话列表")
    print("\n   系统:")
    print("   - GET  /api/health - 健康检查")
    print("=" * 60)
    
    # 预加载特征数据
    load_all_features(rror': '会话不存在'
            }), 404
        
        # 获取当前会话的消息历史
        messages = user_sessions[session_id]['messages'].copy()
        
        # 添加用户消息
        messages.append({"role": "user", "content": user_message})
        add_message(session_id, user_id, "user", user_message)
        
        # 获取AI回复
        assistant_reply = ask_llm_with_history(messages)
        
        if "错误" in assistant_reply or "失败" in assistant_reply:
            return jsonify({
                'success': False,
                'error': assistant_reply
            }), 500
        
        # 保存AI回复
        messages.append({"role": "assistant", "content": assistant_reply})
        add_message(session_id, user_id, "assistant", assistant_reply)
        user_sessions[session_id]['messages'] = messages
        
        return jsonify({
            'success': True,
            'reply': assistant_reply,
            'message_count': len(messages)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/session/<session_id>/finalize', methods=['POST'])
def finalize_consultation(session_id):
    """结束咨询，生成最终建议"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'unknown')
        
        if session_id not in user_sessions:
            return jsonify({
                'success': False,
                'error': '会话不存在'
            }), 404
        
        # 获取当前会话的消息历史
        messages = user_sessions[session_id]['messages'].copy()
        
        # 生成最终建议
        final_prompt = """请根据我们的对话，为我生成一份详细的投资建议报告。包括：

1. **我的风险等级**（保守型/稳健型/平衡型/激进型）
2. **推荐的资产配置**（详细百分比）
3. **具体的投资方向**（股票、债券、基金、其他）
4. **每个方向的建议**（选择哪些产品）
5. **实施策略**（如何进行，注意事项）
6. **风险提示**（可能的风险和应对方法）

请确保建议具体、可操作、并针对我的具体情况。"""
        
        messages.append({"role": "user", "content": final_prompt})
        final_advice = ask_llm_with_history(messages)
        
        add_message(session_id, user_id, "user", final_prompt)
        add_message(session_id, user_id, "assistant", final_advice)
        
        return jsonify({
            'success': True,
            'final_advice': final_advice,
            'session_id': session_id
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """获取会话信息"""
    try:
        if session_id not in user_sessions:
            return jsonify({
                'success': False,
                'error': '会话不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'user_id': user_sessions[session_id]['user_id'],
            'message_count': len(user_sessions[session_id]['messages']),
            'created_at': user_sessions[session_id]['created_at'],
            'messages': user_sessions[session_id]['messages']
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/session/<session_id>', methods=['DELETE'])
def delete_user_session(session_id):
    """删除会话"""
    try:
        if session_id in user_sessions:
            delete_session(session_id)
            del user_sessions[session_id]
            return jsonify({'success': True})
        
        return jsonify({
            'success': False,
            'error': '会话不存在'
        }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/<user_id>/sessions', methods=['GET'])
def get_user_session_list(user_id):
    """获取用户的所有会话"""
    try:
        sessions = get_user_sessions(user_id)
        return jsonify({
            'success': True,
            'sessions': [
                {
                    'session_id': s[0],
                    'title': s[1],
                    'risk_level': s[2],
                    'updated_at': s[3]
                }
                for s in sessions
            ]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== 健康检查 ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'AlphaMind API Server'
    })


# ========== 静态文件服务（可选）==========

@app.route('/')
def serve_assessment():
    """提供主控台页面"""
    return send_from_directory('./AlphaMind_Web1.1版，静态', 'app_console.html')


@app.route('/<filename>')
def serve_static(filename):
    """提供其他静态文件"""
    return send_from_directory('./AlphaMind_Web1.1版，静态', filename)


@app.route('/api/advice/quick', methods=['POST'])
def quick_advice():
    """快速生成建议（对应 app.py 的 run_demo）"""
    data = request.get_json() or {}
    user_id = data.get('user_id', 'web_user')
    user_input = data.get('user_input', '')
    if not user_input:
        return jsonify({'success': False, 'error': 'user_input 不能为空'}), 400

    llm_response = ask_llm(f"提取用户信息：{user_input}")
    if "错误" in llm_response or "失败" in llm_response:
        return jsonify({'success': False, 'error': llm_response}), 500

    features = [30, 2, 50, 5, 1]
    risk = predict_risk(features)
    portfolio = generate_portfolio(risk)
    final_prompt = f"风险等级:{risk}，资产配置:{portfolio}，请生成投资建议"
    answer = ask_llm(final_prompt)

    if "错误" in answer or "失败" in answer:
        return jsonify({'success': False, 'error': answer}), 500

    save_chat(user_id, user_input, answer, risk, str(portfolio))
    return jsonify({'success': True, 'risk': risk, 'portfolio': portfolio, 'advice': answer})


@app.route('/api/history/latest/<user_id>', methods=['GET'])
def api_latest_history(user_id):
    latest = get_latest_record(user_id)
    if not latest:
        return jsonify({'success': False, 'error': '无记录'}), 404
    question, answer, risk, portfolio, time = latest
    return jsonify({
        'success': True,
        'record': {'question': question, 'answer': answer, 'risk': risk, 'portfolio': portfolio, 'time': time}
    })


@app.route('/api/history/all/<user_id>', methods=['GET'])
def api_all_history(user_id):
    rows = get_user_history(user_id)
    return jsonify({
        'success': True,
        'records': [
            {'question': q, 'risk': r, 'portfolio': p, 'time': t}
            for q, r, p, t in rows
        ]
    })


@app.route('/api/users', methods=['GET'])
def api_users():
    users = get_all_users_with_counts()
    return jsonify({
        'success': True,
        'users': [{'user_id': u, 'count': c} for u, c in users]
    })


@app.route('/api/history/<user_id>', methods=['DELETE'])
def api_delete_history(user_id):
    delete_user_records(user_id)
    return jsonify({'success': True, 'message': f'已删除 {user_id} 的记录'})


if __name__ == '__main__':
    print("=" * 50)
    print("AlphaMind API Server 启动中...")
    print("=" * 50)
    print("📍 地址: http://localhost:5000")
    print("📋 API文档:")
    print("   - POST /api/session/create - 创建会话")
    print("   - POST /api/session/<id>/message - 发送消息")
    print("   - POST /api/session/<id>/finalize - 生成最终建议")
    print("   - GET  /api/session/<id> - 获取会话信息")
    print("   - GET  /api/user/<id>/sessions - 用户会话列表")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
