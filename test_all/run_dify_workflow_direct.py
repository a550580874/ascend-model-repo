import requests
import json


def run_dify(query: str):
    url = "https://api.dify.ai/v1/chat-messages"

    payload = {
        "inputs": {},   # 如果你 workflow 有变量再加
        "query": query,
        "response_mode": "blocking",  # 🚨先用 blocking
        "conversation_id": "",
        "user": "python-client"
    }

    headers = {
        "Authorization": "Bearer app-rUPO5b1AwAIk9AwzlZydt01C",
        "Content-Type": "application/json"
    }

    resp = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120,
        verify=False
    )

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

    return resp.json()

if __name__ == "__main__":
    print(json.dumps(run_dify("glm-5 vllm a3 和 glm4.7 vllm 910B"), ensure_ascii=False, indent=2))
