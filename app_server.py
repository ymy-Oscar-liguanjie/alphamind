"""
AlphaMind Flask后端服务
将多轮对话咨询程序通过API暴露给Web前端
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
from datetime import datetime
import uuid

from llm_client import ask_llm_with_history
from llm_client import ask_llm
from model import predict_risk
from portfolio import generate_portfolio
from storage import (create_session, add_message, get_session_messages,
                     get_user_sessions, delete_session, save_chat,
                     get_latest_record, get_user_history, delete_user_records,
                     get_all_users_with_counts)

app = Flask(__name__)
CORS(app)

# ========== 会话管理 ==========

# 内存中保存当前用户的对话会话
user_sessions = {}

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
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': '消息不能为空'
            }), 400
        
        if session_id not in user_sessions:
            return jsonify({
                'success': False,
                'error': '会话不存在'
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
    return send_from_directory('./AlphaMind_Web1.1版，静态', 'assessment.html')


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
