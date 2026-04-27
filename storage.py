import sqlite3, datetime, json

conn = sqlite3.connect("alphamind.db")
c = conn.cursor()

# 原有表（保持兼容）
c.execute("""
CREATE TABLE IF NOT EXISTS chat (
user_id TEXT,
question TEXT,
answer TEXT,
risk TEXT,
portfolio TEXT,
time TEXT
)
""")

# 新增：对话会话表
c.execute("""
CREATE TABLE IF NOT EXISTS conversation_session (
session_id TEXT PRIMARY KEY,
user_id TEXT,
title TEXT,
risk_level TEXT,
portfolio_json TEXT,
created_time TEXT,
updated_time TEXT
)
""")

# 新增：对话消息表
c.execute("""
CREATE TABLE IF NOT EXISTS conversation_message (
message_id INTEGER PRIMARY KEY AUTOINCREMENT,
session_id TEXT,
user_id TEXT,
message_type TEXT,
role TEXT,
content TEXT,
timestamp TEXT,
FOREIGN KEY (session_id) REFERENCES conversation_session(session_id)
)
""")

conn.commit()

def save_chat(user_id, q, a, r, p):
    """保存用户会话"""
    c.execute("INSERT INTO chat VALUES (?,?,?,?,?,?)",
              (user_id, q, a, r, p, str(datetime.datetime.now())))
    conn.commit()

def get_user_history(user_id):
    """获取某用户的所有历史记录"""
    c.execute("SELECT question, risk, portfolio, time FROM chat WHERE user_id=? ORDER BY time DESC",
              (user_id,))
    return c.fetchall()

def get_latest_record(user_id):
    """获取某用户最新的一条记录"""
    c.execute("SELECT question, answer, risk, portfolio, time FROM chat WHERE user_id=? ORDER BY time DESC LIMIT 1",
              (user_id,))
    return c.fetchone()

def get_all_users():
    """获取所有用户ID"""
    c.execute("SELECT DISTINCT user_id FROM chat ORDER BY user_id")
    return [row[0] for row in c.fetchall()]

def delete_user_records(user_id):
    """删除某用户的所有记录"""
    c.execute("DELETE FROM chat WHERE user_id=?", (user_id,))
    conn.commit()

def get_record_count(user_id):
    """获取某用户的记录数"""
    c.execute("SELECT COUNT(*) FROM chat WHERE user_id=?", (user_id,))
    return c.fetchone()[0]

# ========== 多轮对话函数 ==========

def create_session(user_id, title=""):
    """创建一个新的对话会话"""
    import uuid
    session_id = str(uuid.uuid4())
    now = str(datetime.datetime.now())
    c.execute("""INSERT INTO conversation_session 
                (session_id, user_id, title, created_time, updated_time) 
                VALUES (?, ?, ?, ?, ?)""",
              (session_id, user_id, title, now, now))
    conn.commit()
    return session_id

def add_message(session_id, user_id, role, content, message_type="text"):
    """添加对话消息"""
    now = str(datetime.datetime.now())
    c.execute("""INSERT INTO conversation_message 
                (session_id, user_id, message_type, role, content, timestamp) 
                VALUES (?, ?, ?, ?, ?, ?)""",
              (session_id, user_id, message_type, role, content, now))
    conn.commit()

def get_session_messages(session_id):
    """获取会话的所有消息"""
    c.execute("""SELECT role, content FROM conversation_message 
                 WHERE session_id=? ORDER BY timestamp ASC""",
              (session_id,))
    return c.fetchall()

def update_session_risk(session_id, risk_level, portfolio_json):
    """更新会话的风险等级和资产配置"""
    now = str(datetime.datetime.now())
    c.execute("""UPDATE conversation_session 
                 SET risk_level=?, portfolio_json=?, updated_time=?
                 WHERE session_id=?""",
              (risk_level, json.dumps(portfolio_json), now, session_id))
    conn.commit()

def get_session_detail(session_id):
    """获取会话详情"""
    c.execute("""SELECT user_id, title, risk_level, portfolio_json, created_time, updated_time 
                 FROM conversation_session WHERE session_id=?""",
              (session_id,))
    return c.fetchone()

def get_user_sessions(user_id):
    """获取用户的所有会话"""
    c.execute("""SELECT session_id, title, risk_level, updated_time 
                 FROM conversation_session WHERE user_id=? ORDER BY updated_time DESC""",
              (user_id,))
    return c.fetchall()

def delete_session(session_id):
    """删除会话（级联删除消息）"""
    c.execute("DELETE FROM conversation_message WHERE session_id=?", (session_id,))
    c.execute("DELETE FROM conversation_session WHERE session_id=?", (session_id,))
    conn.commit()