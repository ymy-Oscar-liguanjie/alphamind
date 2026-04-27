import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://tdyun.ai")
MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")

# 投顾顾问系统提示词
ADVISOR_SYSTEM_PROMPT = """你是一位经验丰富的投资顾问。你的职责是：
1. 耐心倾听用户的财务状况、投资目标和风险承受能力
2. 通过提问逐步了解用户的具体需求
3. 基于用户信息提供个性化的投资建议
4. 用温和、专业、可理解的语言交流
5. 始终强调投资风险提示

对话风格：
- 自然、亲切，像真实顾问一样对话
- 避免过于冗长的回答，保持简洁（2-3句话）
- 每次提问时，逐步引导用户向你揭示信息
- 在适当时机提供具体的投资建议

记住：这是一个对话过程，不是一次性输出所有建议。"""

def ask_llm(user_input, max_retries=3, retry_delay=2):
    """
    调用LLM API，支持重试机制
    :param user_input: 用户输入
    :param max_retries: 最大重试次数
    :param retry_delay: 重试延迟（秒）
    """
    
    if not API_KEY:
        return "错误: 未配置 LLM_API_KEY 环境变量"
    
    url = f"{BASE_URL}/v1/messages"

    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    data = {
        "model": MODEL,
        "max_tokens": 300,
        "messages": [
            {"role": "user", "content": user_input}
        ]
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            print(f"[尝试 {attempt + 1}/{max_retries}] 状态码: {response.status_code}")
            
            res_json = response.json()

            # 成功返回
            if response.status_code == 200 and "content" in res_json:
                return res_json["content"][0]["text"]

            # Token错误处理
            if response.status_code == 500 and "error" in res_json:
                error_msg = res_json["error"].get("message", "")
                if "token" in error_msg.lower():
                    print(f"[Token错误] {error_msg}")
                    if attempt < max_retries - 1:
                        print(f"[重试] 等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        return f"API错误: {error_msg}（已重试{max_retries}次）"
            
            # 其他错误
            if "error" in res_json:
                return f"API错误: {res_json['error']}"

            return f"未知返回格式: {res_json}"

        except requests.exceptions.Timeout:
            print(f"[超时] 请求超时，尝试重试...")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return "调用失败: 请求超时"
                
        except requests.exceptions.RequestException as e:
            print(f"[网络错误] {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return f"调用失败: {e}"
                
        except Exception as e:
            return f"调用失败: {e}"
    
    return "调用失败: 超过最大重试次数"


def ask_llm_with_history(messages, max_retries=3, retry_delay=2):
    """
    支持多轮对话的LLM调用（带对话历史）
    :param messages: 消息列表，格式为 [{"role": "user/assistant", "content": "..."}, ...]
    :param max_retries: 最大重试次数
    :param retry_delay: 重试延迟（秒）
    """
    
    if not API_KEY:
        return "错误: 未配置 LLM_API_KEY 环境变量"
    
    url = f"{BASE_URL}/v1/messages"

    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    data = {
        "model": MODEL,
        "max_tokens": 500,
        "system": ADVISOR_SYSTEM_PROMPT,
        "messages": messages
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            print(f"[尝试 {attempt + 1}/{max_retries}] 状态码: {response.status_code}")
            
            res_json = response.json()

            # 成功返回
            if response.status_code == 200 and "content" in res_json:
                return res_json["content"][0]["text"]

            # Token错误处理
            if response.status_code == 500 and "error" in res_json:
                error_msg = res_json["error"].get("message", "")
                if "token" in error_msg.lower():
                    print(f"[Token错误] {error_msg}")
                    if attempt < max_retries - 1:
                        print(f"[重试] 等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        return f"API错误: {error_msg}（已重试{max_retries}次）"
            
            # 其他错误
            if "error" in res_json:
                return f"API错误: {res_json['error']}"

            return f"未知返回格式: {res_json}"

        except requests.exceptions.Timeout:
            print(f"[超时] 请求超时，尝试重试...")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return "调用失败: 请求超时"
                
        except requests.exceptions.RequestException as e:
            print(f"[网络错误] {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return f"调用失败: {e}"
                
        except Exception as e:
            return f"调用失败: {e}"
    
    return "调用失败: 超过最大重试次数"