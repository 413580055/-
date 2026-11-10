import sys
import re

# 核心安全檢查函數：雙語（中英文）混合變體與啟發式規則檢測
def inspect_and_sanitize(content: str) -> str:
    
    # 1. 雙語正規表達式（RegEx）規則庫：同時覆蓋英文與中文的各種提示詞注入變體
    regex_patterns = [
        # 英文指令覆蓋與越獄變體
        r"(ignore|disregard|forget|bypass|override|skip)\s+(previous|prior|all|the)?\s*(instructions?|directives?|rules?|commands?|prompts?|guidelines?)",
        
        # 中文指令覆蓋與越獄變體（加入選填的「的」字或其他修飾）
        r"(忽略|忘記|覆蓋|取消|繞過|跳過|不用理會|無視)\s*(先前|以前|所有|原本的|上述|這項)?\s*(?:的)?\s*(指令|規則|提示詞|設定|命令|內容)",
        
        # 英文系統越獄特徵
        r"(you are now|act as|system prompt|developer mode|new instructions?:)",
        
        # 中文系統越獄特徵（角色扮演劫持、開發者模式）
        r"(從現在開始|你現在是|切換到|身為|進入)\s*(開發者模式|管理員|無限制模式|debug 模式)"
    ]
    
    # 逐一檢查 RegEx 規則
    for pattern in regex_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            print(f"[🛡️ Security Alert] 透過「中英文雙語 RegEx」偵測到潛在攻擊！匹配規則：{pattern}", file=sys.stderr)
            return "[安全警告：此工具回傳內容包含中英文越獄或指令注入特徵，已被 Proxy 攔截清洗]"

    # 2. 啟發式規則（Heuristics）：檢測異常的高密度強制命令語氣（中英文皆適用）
    imperative_keywords = [
        "must now", "you are required to", "you must", 
        "你必須", "請立刻", "強制執行", "不得拒絕"
    ]
    match_count = sum(1 for kw in imperative_keywords if re.search(kw, content, re.IGNORECASE))
    
    if match_count >= 2:
        print(f"[🛡️ Security Alert] 透過「啟發式規則」偵測到中英文混雜的高密度強制命令語氣！", file=sys.stderr)
        return "[安全警告：此工具回傳內容包含異常的高密度強制命令，已被 Proxy 攔截清洗]"

    return content

# Secure Proxy 的中介攔截調用包裝
async def secure_call_tool(session, tool_name: str, arguments: dict):
    print(f"[Secure Proxy Interceptor] 正在安全檢查並轉發工具調用: {tool_name}({arguments})", file=sys.stderr)
    
    # 1. 實際呼叫後端真實 Server
    result = await session.call_tool(tool_name, arguments)
    
    # 2. 進行多層次安全檢查與清洗
    for item in result.content:
        if hasattr(item, "text"):
            original_text = item.text
            sanitized_text = inspect_and_sanitize(original_text)
            item.text = sanitized_text
            print(f"[Secure Proxy Interceptor] 內容檢查完畢。原始: {original_text} -> 清洗後: {sanitized_text}", file=sys.stderr)
            
    return result
