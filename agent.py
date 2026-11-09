import ollama
from datetime import datetime
from rag import load_chunks_by_section, search

MODEL = "qwen3.5:4b"   # 若不支援工具就換模型

CHUNKS = load_chunks_by_section("building_effective_agents_zh.md")

# ---------- 工具（就是普通函式）----------
def calculator(expression: str) -> str:
    """計算數學算式，例如 '123*45+6' 或 '25*25'。只接受數字與 + - * / ( )，不要放中文。"""
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        return "錯誤：只允許數字與 + - * / ( )"
    try:
        return str(eval(expression))
    except Exception as e:
        return f"錯誤：{e}"


def get_time() -> str:
    """取得現在的日期與時間。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def search_docs(query: str) -> str:
    """搜尋《Building Effective Agents》導讀文件。凡是詢問文件中的名詞、
    模式或概念（例如 workflow、agent、Evaluator-optimizer、Routing），
    都必須先用這個工具，query 請放關鍵字。"""
    def search_docs(query: str) -> str:
        """（docstring 不變）"""
    results = search(query, CHUNKS, top_k=6)        # 3 → 6
    print("[除錯] 搜尋結果：", results)
    results = [(i, s) for i, s in results if s > 0]
    if not results or results[0][1] < 0.5:           # 1.0 → 0.5
        return "文件裡沒有找到相關內容"
    return "\n\n".join(f"[第 {i} 段]\n{CHUNKS[i]}" for i, _ in results)


# 工具名稱 -> 函式（像 Java 的 Map<String, Function>）
TOOLS = {
    "calculator": calculator,
    "get_time": get_time,
    "search_docs": search_docs, 
}


# ---------- Agent 迴圈 ----------
def run_agent(question: str, max_steps: int = 5) -> str:
    messages = [
        {"role": "system", "content": (
            "你是助理。規則：\n"
            "1. 只要問題涉及《Building Effective Agents》、workflow、agent、"
            "Evaluator-optimizer、Routing 等文件內的概念，一律先呼叫 search_docs，不可憑記憶回答。\n"
            "2. 任何數學運算（包含很簡單的乘法）都必須呼叫 calculator，不可心算。\n"
            "3. 時間用 get_time。\n"
            "4. 沒有對應工具的事，誠實說做不到。\n"
            "5. 只有實際呼叫過 search_docs，才可以說「根據文件」。\n"
            "6. 一律使用繁體中文，數學結果用純文字，不要使用 LaTeX。"
        )},
        {"role": "system", "content": question},
    ]

    for step in range(max_steps):
        resp = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=list(TOOLS.values()),
            think=False,
            options={"num_ctx": 8192},
        )
        msg = resp.message
        messages.append(msg)

        # 模型沒要求工具 -> 這就是最終答案
        if not msg.tool_calls:
            return msg.content or "（模型沒有回答）"

        # 模型要求工具 -> 我們執行，再把結果丟回去
        for call in msg.tool_calls:
            name = call.function.name
            args = call.function.arguments
            print(f"[工具] {name}({args})")

            func = TOOLS.get(name)
            result = func(**args) if func else f"錯誤：沒有 {name} 這個工具"
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})

    return "已達最大步數，停止。"


if __name__ == "__main__":
    while True:
        q = input("\n問題（輸入 q 離開）：")
        if q.strip().lower() == "q":
            break
        print("答：", run_agent(q))