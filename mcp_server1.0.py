# mcp_server.py
from mcp.server.fastmcp import FastMCP
from datetime import datetime

# 初始化 FastMCP 伺服器
mcp = FastMCP("ResearchAssistantServer")

@mcp.tool()
def calculator(expression: str) -> str:
    """計算數學算式，例如 '123*45+6' 或 '25*25'。只接受數字與 + - * / ( )。"""
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        return "錯誤：只允許數字與 + - * / ( )"
    try:
        return str(eval(expression))
    except Exception as e:
        return f"錯誤：{e}"

@mcp.tool()
def get_time() -> str:
    """取得現在的日期與時間。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    # 以標準輸入輸出 (stdio) 運行伺服器，等待 Client 呼叫
    mcp.run(transport='stdio')