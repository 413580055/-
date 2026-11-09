# mcp_client.py
import asyncio
import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "qwen3.5:4b"

async def run_mcp_agent():
    # 1. 設定透過 Stdio 啟動 mcp_server.py
    server_params = StdioServerParameters(
        command="python",
        args=["-u", "mcp_proxy.py"],
        env=None
    )

    print("[Client] 正在連線到 MCP Server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化連線
            await session.initialize()
            print("[Client] 成功連線！")

            # 2. 動態從 MCP Server 取得可用工具清單
            mcp_tools_response = await session.list_tools()
            
            # 將 MCP 的工具格式轉換為 Ollama 可以接受的格式
            ollama_tools = []
            for t in mcp_tools_response.tools:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    }
                })
            
            print(f"[Client] 成功載入遠端工具: {[t['function']['name'] for t in ollama_tools]}")

            # 3. 進入互動式對話迴圈（設定研究助理的角色與工具使用規則）
            messages = [
                {
                    "role": "system", 
                    "content": (
                        "你是專業的 AI 研究助理。規則：\n"
                        "1. 當被問及《Building Effective Agents》相關概念時，必須使用 search_docs 工具。\n"
                        "2. 需要計算或時間時，請使用 calculator 或 get_time。\n"
                        "3. 遇到需要抓取網頁時，可使用 fetch_external_webpage。\n"
                        "4. 一律使用繁體中文回答。"
                    )
                }
            ]

            while True:
                q = input("\n請輸入問題（輸入 q 離開）：")
                if q.strip().lower() == "q":
                    break
                
                messages.append({"role": "user", "content": q})

                # 呼叫 Ollama 模型
                resp = ollama.chat(
                    model=MODEL,
                    messages=messages,
                    tools=ollama_tools,
                    options={"num_ctx": 8192},
                )
                
                msg = resp.message
                messages.append(msg)

                # 如果模型決定呼叫工具
                if msg.tool_calls:
                    for call in msg.tool_calls:
                        tool_name = call.function.name
                        tool_args = call.function.arguments
                        print(f"\n[MCP 攔截/呼叫] 執行遠端工具 -> {tool_name}({tool_args})")

                        # 透過 MCP Session 向 Server 發起工具調用 (JSON-RPC)
                        result = await session.call_tool(tool_name, arguments=tool_args)
                        tool_output = result.content[0].text
                        print(f"[MCP 回傳結果] {tool_output}")

                        # 將工具執行結果放回對話記錄
                        messages.append({
                            "role": "tool", 
                            "tool_name": tool_name, 
                            "content": tool_output
                        })

                    # 再次讓模型根據工具結果給出最終回答
                    final_resp = ollama.chat(model=MODEL, messages=messages)
                    print(f"\n答：{final_resp.message.content}")
                else:
                    print(f"\n答：{msg.content}")

if __name__ == "__main__":
    asyncio.run(run_mcp_agent())