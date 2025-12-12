import asyncio
import httpx
import uuid
import json
import time

# API的URL
BASE_URL = "http://127.0.0.1:25831"
RECOMMENDATION_URL = f"{BASE_URL}/recommendation"

async def make_request(client: httpx.AsyncClient, user_id: str, session_id: str, user_input: str, stream: bool):
    """
    发送单个异步请求的辅助函数
    """
    print(f"[开始] 用户: {user_id}, Session: {session_id}, 问题: '{user_input[:20]}...'")

    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "user_input": user_input,
        "stream": stream
    }

    start_time = time.time()
    try:
        response = await client.post(RECOMMENDATION_URL, json=payload, timeout=240.0)
        response.raise_for_status()

        duration = time.time() - start_time

        if stream:
            # 处理流式响应
            stream_content = ""
            async for chunk in response.aiter_text():
                stream_content += chunk
            print(f"[完成] 用户: {user_id} (流式) | 耗时: {duration:.2f}s | 响应: {stream_content[:50].strip()}...")
            return {"user_id": user_id, "success": True, "content": stream_content}
        else:
            # 处理非流式响应
            json_response = response.json()
            print(f"[完成] 用户: {user_id} (非流式) | 耗时: {duration:.2f}s | 响应: {json_response.get('message', '')[:50].strip()}...")
            return {"user_id": user_id, "success": True, "content": json_response}

    except httpx.RequestError as e:
        duration = time.time() - start_time
        print(f"[失败] 用户: {user_id} | 耗时: {duration:.2f}s | 错误: {e}")
        return {"user_id": user_id, "success": False, "error": str(e)}

async def run_concurrent_test():
    """
    并发测试主函数
    """
    print("--- 开始并发测试：模拟多个用户同时请求 ---")

    # 定义多个用户和他们的问题
    users = [
        {"id": "user_alpha", "input": "我想去加拿大读计算机科学，本科背景是软件工程。", "stream": False},
        {"id": "user_beta", "input": "你好，对澳大利亚的商业分析硕士感兴趣，有什么学校推荐吗？", "stream": True},
        {"id": "user_gamma", "input": "请问新加坡国立大学的金融科技项目怎么样？", "stream": False},
        {"id": "user_delta", "input": "我没有任何背景，就是想出国读个一年制的硕士，水一点也没关系，有推荐吗？", "stream": True},
        {"id": "user_epsilon", "input": "GPA只有2.8，托福刚过80，能申请到美国的什么学校？", "stream": False},
    ]

    # 使用httpx.AsyncClient来复用连接
    async with httpx.AsyncClient() as client:
        tasks = []
        for user in users:
            # 为每个用户创建一个独立的session_id
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            task = make_request(client, user["id"], session_id, user["input"], user["stream"])
            tasks.append(task)

        # 并发执行所有请求
        results = await asyncio.gather(*tasks)

    print("\n--- 并发测试完成 ---")
    print("所有请求结果汇总:")
    for result in results:
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    # 运行异步并发测试
    asyncio.run(run_concurrent_test())