from flask import Flask, render_template, request, jsonify, session, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import sqlite3
import uuid
import os
import time
import pandas as pd

load_dotenv()

from llm_client import ask_llm_with_history
from ai_media_client import image_to_text, speech_to_text

try:
    from model import predict_risk
except Exception:
    predict_risk = None

try:
    from portfolio import generate_portfolio
except Exception:
    generate_portfolio = None

app = Flask(__name__)
app.secret_key = "alphamind_secret"
DB = "users.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_conn():
    return sqlite3.connect(DB)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY, username TEXT NOT NULL, title TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()

init_db()

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

def is_retryable_ai_error(text):
    if not text: return False
    s = str(text)
    retry_keywords = ["No available accounts","503","rate limit","temporarily unavailable","timeout","timed out","connection","API错误","internal_server_error","server_error","Too Many Requests","overloaded"]
    return any(k.lower() in s.lower() for k in retry_keywords)

def ask_llm_with_retry(messages, max_retries=5, base_delay=2):
    for attempt in range(1, max_retries + 1):
        try:
            reply = ask_llm_with_history(messages)
            if reply and not is_retryable_ai_error(reply):
                return reply
        except Exception as e:
            err = str(e)
            if not is_retryable_ai_error(err):
                return f"AI接口调用失败：{err}"
        if attempt < max_retries:
            time.sleep(base_delay * attempt)
    return "AI服务当前繁忙，系统已自动重试多次仍未成功，请稍后再发一次。"

def load_user_features(username):
    default_features = {"age":35,"income10k":18,"asset10k":80,"debt10k":10,"children":1,"exp_years":3,"action_mean":0,"q_sentiment":0}
    path = os.path.join("work", "all_features.csv")
    if not os.path.exists(path):
        return None, default_features, "未找到 work/all_features.csv，已使用默认用户画像"
    try:
        df = pd.read_csv(path)
        if str(username).isdigit() and "user_id" in df.columns:
            uid = int(username)
            row = df[df["user_id"] == uid]
            if len(row) > 0:
                return uid, row.iloc[0].to_dict(), f"已读取 user_id={uid} 的 M2 特征"
        return None, default_features, "当前登录名不是数字 user_id，已使用默认用户画像"
    except Exception as e:
        return None, default_features, f"读取 M2 特征失败，已使用默认用户画像：{str(e)}"

def run_m3_m4_analysis(username):
    user_id, features, feature_note = load_user_features(username)
    try:
        if predict_risk is None: raise RuntimeError("未能导入 model.predict_risk")
        risk_prob = float(predict_risk(features, workdir="work"))
        risk_level = "进取型" if risk_prob >= 0.5 else "稳健型"
        risk_note = "M3 风险预测成功"
    except Exception as e:
        risk_prob = 0.5
        risk_level = "稳健型"
        risk_note = f"M3 风险预测失败，已使用默认风险概率 50%：{str(e)}"
    try:
        if generate_portfolio is None: raise RuntimeError("未能导入 portfolio.generate_portfolio")
        try:
            portfolio = generate_portfolio(user_id=user_id, risk_prob=risk_prob, workdir="work")
        except TypeError:
            portfolio = None
        if isinstance(portfolio, dict):
            portfolio_str = ", ".join([f"{k}: {float(v):.1f}%" for k, v in portfolio.items()])
        elif portfolio is not None:
            portfolio_str = str(portfolio)
        else:
            if risk_prob < 0.33:
                portfolio = {"股票":20,"债券":55,"基金":10,"REITs":5,"大宗商品":5,"现金":5}
            elif risk_prob < 0.67:
                portfolio = {"股票":35,"债券":35,"基金":15,"REITs":5,"大宗商品":5,"现金":5}
            else:
                portfolio = {"股票":55,"债券":20,"基金":15,"REITs":5,"大宗商品":3,"现金":2}
            portfolio_str = ", ".join([f"{k}: {v:.1f}%" for k, v in portfolio.items()])
        portfolio_note = "M4 资产配置生成成功"
    except Exception as e:
        portfolio = {"股票":35,"债券":35,"基金":15,"REITs":5,"大宗商品":5,"现金":5}
        portfolio_str = ", ".join([f"{k}: {v:.1f}%" for k, v in portfolio.items()])
        portfolio_note = f"M4 资产配置失败，已使用默认配置：{str(e)}"
    return {"user_id":user_id,"features":features,"feature_note":feature_note,"risk_prob":risk_prob,"risk_level":risk_level,"risk_note":risk_note,"portfolio":portfolio,"portfolio_str":portfolio_str,"portfolio_note":portfolio_note}

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/chat")
def chat_page():
    if "user" not in session: return redirect("/")
    return render_template("chat.html", username=session["user"])

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username","").strip()
    email = data.get("email","").strip()
    password = data.get("password","").strip()
    confirm_password = data.get("confirm_password","").strip()
    if not username or not email or not password or not confirm_password:
        return jsonify({"success":False,"msg":"请完整填写注册信息"})
    if "@" not in email or "." not in email:
        return jsonify({"success":False,"msg":"邮箱格式不正确"})
    if len(password) < 6:
        return jsonify({"success":False,"msg":"密码长度不能少于6位"})
    if password != confirm_password:
        return jsonify({"success":False,"msg":"两次密码不一致"})
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users(username,email,password) VALUES(?,?,?)", (username,email,generate_password_hash(password)))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"success":False,"msg":"用户名或邮箱已存在"})
    finally:
        conn.close()
    return jsonify({"success":True,"msg":"注册成功"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    account = data.get("account","").strip()
    password = data.get("password","").strip()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username,password FROM users WHERE username=? OR email=?", (account,account))
    row = cur.fetchone()
    conn.close()
    if not row: return jsonify({"success":False,"msg":"用户不存在"})
    username, password_hash = row
    if not check_password_hash(password_hash, password):
        return jsonify({"success":False,"msg":"密码错误"})
    session["user"] = username
    return jsonify({"success":True})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success":True})

@app.route("/api/new_chat", methods=["POST"])
def new_chat():
    if "user" not in session: return jsonify({"success":False})
    chat_id = str(uuid.uuid4())
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO chats(id,username,title) VALUES(?,?,?)", (chat_id,session["user"],"新对话"))
    conn.commit()
    conn.close()
    return jsonify({"success":True,"chat_id":chat_id})

@app.route("/api/delete_chat/<chat_id>", methods=["DELETE","POST"])
def delete_chat(chat_id):
    if "user" not in session:
        return jsonify({"success":False,"msg":"请先登录"}), 401
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM chats WHERE id=? AND username=?", (chat_id, session["user"]))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"success":False,"msg":"没有权限或会话不存在"}), 404
    cur.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
    cur.execute("DELETE FROM chats WHERE id=? AND username=?", (chat_id, session["user"]))
    conn.commit()
    conn.close()
    return jsonify({"success":True})

@app.route("/api/chat_history")
def chat_history():
    if "user" not in session: return jsonify([])
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,title,created_at FROM chats WHERE username=? ORDER BY created_at DESC", (session["user"],))
    rows = cur.fetchall()
    conn.close()
    return jsonify([{"id":r[0],"title":r[1],"created_at":r[2]} for r in rows])

@app.route("/api/messages/<chat_id>")
def get_messages(chat_id):
    if "user" not in session: return jsonify([])
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT m.role,m.content FROM messages m JOIN chats c ON m.chat_id=c.id WHERE m.chat_id=? AND c.username=? ORDER BY m.id ASC""", (chat_id, session["user"]))
    rows = cur.fetchall()
    conn.close()
    return jsonify([{"role":r[0],"content":r[1]} for r in rows])

@app.route("/api/analysis", methods=["GET"])
def api_analysis():
    if "user" not in session:
        return jsonify({"success":False,"msg":"请先登录"}), 401
    return jsonify({"success":True,"analysis":run_m3_m4_analysis(session["user"])})

@app.route("/api/speech_to_text", methods=["POST"])
def api_speech_to_text():
    if "user" not in session:
        return jsonify({"success":False,"text":"请先登录"}), 401
    if "audio" not in request.files:
        return jsonify({"success":False,"text":"没有收到音频文件"})
    audio = request.files["audio"]
    safe_name = audio.filename or "recording.webm"
    filename = str(uuid.uuid4()) + "_" + safe_name
    path = os.path.join(UPLOAD_DIR, filename)
    audio.save(path)
    return jsonify({"success":True,"text":speech_to_text(path)})

@app.route("/api/image_chat", methods=["POST"])
def api_image_chat():
    if "user" not in session:
        return jsonify({"success":False,"reply":"请先登录"}), 401
    if "image" not in request.files:
        return jsonify({"success":False,"reply":"没有收到图片"})
    image = request.files["image"]
    prompt = request.form.get("prompt","").strip() or "请识别这张图片内容，并说明它与用户问题可能有什么关系。"
    chat_id = request.form.get("chat_id","").strip()
    ext = image.filename.lower().split(".")[-1] if "." in image.filename else "png"
    if ext not in ["png","jpg","jpeg","webp","gif"]: ext = "png"
    filename = str(uuid.uuid4()) + "." + ext
    path = os.path.join(UPLOAD_DIR, filename)
    image.save(path)
    with open(path, "rb") as f:
        image_bytes = f.read()
    image_summary = image_to_text(image_bytes, filename, prompt)
    image_url = f"/uploads/{filename}"
    reply = image_summary
    if chat_id:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM chats WHERE id=? AND username=?", (chat_id, session["user"]))
        if cur.fetchone():
            user_content = f"[图片]({image_url})\n{prompt}\n\n[图片识别内容]\n{image_summary}"
            cur.execute("INSERT INTO messages(chat_id,role,content) VALUES(?,?,?)", (chat_id,"user",user_content))
            cur.execute("INSERT INTO messages(chat_id,role,content) VALUES(?,?,?)", (chat_id,"assistant",reply))
            cur.execute("UPDATE chats SET title=? WHERE id=? AND title='新对话'", (prompt[:20],chat_id))
            conn.commit()
        conn.close()
    return jsonify({"success":True,"reply":reply,"image_url":image_url,"image_summary":image_summary})

@app.route("/api/chat", methods=["POST"])
def chat():
    if "user" not in session:
        return jsonify({"success":False,"reply":"请先登录"})
    data = request.json or {}
    chat_id = data.get("chat_id")
    message = data.get("message","").strip()
    if not chat_id: return jsonify({"success":False,"reply":"缺少 chat_id"})
    if not message: return jsonify({"success":False,"reply":"请输入内容"})
    analysis = run_m3_m4_analysis(session["user"])
    system_context = f"""
你是 AlphaMind 智能投顾系统。请基于以下模型分析结果和历史上下文回答用户问题。
如果历史中包含[图片识别内容]，说明用户之前上传过图片，你可以把该图片内容作为上下文继续回答。

【M2 用户特征来源】
{analysis["feature_note"]}

【M3 风险预测结果】
风险概率：{analysis["risk_prob"]:.2%}
风险等级：{analysis["risk_level"]}
状态：{analysis["risk_note"]}

【M4 资产配置结果】
{analysis["portfolio_str"]}
状态：{analysis["portfolio_note"]}

【用户画像】
{analysis["features"]}

回答要求：
1. 先结合 M3 风险等级判断用户属于稳健型还是进取型。
2. 再结合 M4 资产配置给出建议。
3. 如果用户提到“刚才的图片/这张图/图片里”，请参考历史中的[图片识别内容]。
4. 语气专业、清晰、适合普通用户理解。
"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO messages(chat_id,role,content) VALUES(?,?,?)", (chat_id,"user",message))
    cur.execute("SELECT role,content FROM messages WHERE chat_id=? ORDER BY id ASC", (chat_id,))
    rows = cur.fetchall()
    messages = [{"role":"system","content":system_context}]
    for r in rows:
        messages.append({"role":r[0],"content":r[1]})
    reply = ask_llm_with_retry(messages)
    cur.execute("INSERT INTO messages(chat_id,role,content) VALUES(?,?,?)", (chat_id,"assistant",reply))
    cur.execute("UPDATE chats SET title=? WHERE id=? AND title='新对话'", (message[:20], chat_id))
    conn.commit()
    conn.close()
    return jsonify({"success":True,"reply":reply,"analysis":analysis})

if __name__ == "__main__":
    app.run(debug=True)
