import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from proxy import secure_call_tool

async def run():
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[Client] 成功連線至伺服器！")

            # 測試調用可能會夾帶攻擊負載的外部文件讀取工具
            print("[Client] 正在透過 AI 代理讀取外部網頁...")
            result = await secure_call_tool(
                session, 
                "read_external_document", 
                {"url": "https://example.com/public-post"}
            )
            print(f"\n[Client] 最終收到安全的工具執行結果：\n{result}")

if __name__ == "__main__":
    asyncio.run(run())
