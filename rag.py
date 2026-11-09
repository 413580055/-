import re
import math
import time
import ollama

MODEL = "qwen3.5:4b"   

def load_chunks_by_section(path, max_len=900):
    """按 ## 或 ### 標題切段，太長的再切開"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    parts = re.split(r"\n(?=#{2,3} )", text)
    chunks = []
    for p in parts:
        while len(p) > max_len:
            chunks.append(p[:max_len])
            p = p[max_len - 100:]
        chunks.append(p)
    return chunks

def keywords(text):
    """英文單字整個當關鍵字（轉小寫），中文用連續兩字"""
    text = text.lower()
    result = set()
    for word in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text):
        result.add(word)
        if "-" in word:
            result.update(word.split("-"))
    for seg in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(seg) == 1:
            result.add(seg)
        for i in range(len(seg) - 1):
            result.add(seg[i:i + 2])
    return result

def search(question, chunks, top_k=3):
    keys = keywords(question)
    lowered = [c.lower() for c in chunks]
    n = len(chunks)
    weights = {}
    for k in keys:
        df = sum(1 for c in lowered if k in c)
        weights[k] = math.log((n + 1) / (df + 1))
    scored = []
    for i, c in enumerate(lowered):
        score = sum(weights[k] * min(c.count(k), 3) for k in keys)
        scored.append((score, i))
    scored.sort(reverse=True)
    return [(i, s) for s, i in scored[:top_k]]

def ask(question, chunks):
    results = search(question, chunks, top_k=4)
    if results[0][1] < 1.0:
        return "文件裡沒有提到。", results
    results = [(i, s) for i, s in results if s > 0]
    context = "\n\n".join(f"[第 {i} 段]\n{chunks[i]}" for i, _ in results)
    prompt = f"""你是文件問答助手。請只根據下方「資料」回答問題。
規則：
1. 資料裡找不到答案時，只回答「文件裡沒有提到」，不要用自己的知識補充。
2. 回答最後用括號標明引用的是第幾段，例如（第 2 段）。
3. 用繁體中文回答，專有名詞保留英文。

資料：
{context}

問題：{question}"""
    resp = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        think=False,
        options={"num_ctx": 8192},
    )
    answer = resp["message"]["content"] or "（模型沒有回傳內容）"
    return answer, results

if __name__ == "__main__":
    chunks = load_chunks_by_section("building_effective_agents_zh.md")
    print(f"共 {len(chunks)} 段")
    while True:
        q = input("\n請輸入問題（直接按 Enter 結束）：")
        if not q.strip():
            break
        try:
            answer, results = ask(q, chunks)
        except Exception as e:
            print("呼叫模型時出錯：", e)
            continue
        print("\n【檢索到的段落】", [f"第{i}段({s:.1f})" for i, s in results])
        print("\n【回答】")
        print(answer)