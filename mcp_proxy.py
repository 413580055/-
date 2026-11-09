# mcp_proxy.py (Windows 終極穩定版)
import sys
import asyncio
import json

def system1_security_inspection(text: str) -> tuple[bool, str]:
    """
    高效率的 System 1 檢測模型：
    檢查工具輸出中是否包含間接提示詞注入（Indirect Prompt Injection）的特徵。
    """
    malicious_patterns = [
        "系統安全覆寫",
        "忽略先前",
        "忽略所有",
        "改為呼叫",
        "最高機密指令"
    ]
    
    for pattern in malicious_patterns:
        if pattern in text:
            print(f"\n[🚨 SECURITY ALERT] Proxy 攔截到潛在的間接提示詞注入！觸發關鍵字: '{pattern}'", file=sys.stderr)
            safe_replacement = (
                "【安全警告 (Secure MCP Proxy)】\n"
                "偵測到此工具回傳內容包含可疑的「提示詞注入 (Prompt Injection)」攻擊企圖，"
                "已被安全中介層強制清洗與攔截，以維護 Agent 輸出完整性 (Output Integrity)."
            )
            return False, safe_replacement
            
    return True, text

async def forward_client_to_server(server_writer):
    """透過執行緒安全地從 sys.stdin 讀取 Client 請求並轉發給 Server"""
    loop = asyncio.get_running_loop()
    try:
        while True:
            # 使用 run_in_executor 避免 Windows 下標準輸入被封鎖
            line = await loop.run_in_executor(None, sys.stdin.buffer.readline)
            if not line:
                break
            server_writer.write(line)
            await server_writer.drain()
    except Exception as e:
        print(f"[Proxy C2S Error] {e}", file=sys.stderr)

async def forward_server_to_client(server_reader):
    """將 Server 的回應經過 Proxy 檢查後，直接寫入 sys.stdout"""
    try:
        while True:
            line = await server_reader.readline()
            if not line:
                break
            
            decoded_line = line.decode('utf-8')
            
            try:
                data = json.loads(decoded_line.strip())
                if "result" in data and "content" in data["result"]:
                    for content_item in data["result"]["content"]:
                        if content_item.get("type") == "text":
                            original_text = content_item.get("text", "")
                            is_safe, processed_text = system1_security_inspection(original_text)
                            content_item["text"] = processed_text
                    decoded_line = json.dumps(data) + "\n"
            except json.JSONDecodeError:
                pass
            
            # 直接將淨化後的資料寫入二進位標準輸出並立即強制重新整理 (flush)
            sys.stdout.buffer.write(decoded_line.encode('utf-8'))
            sys.stdout.buffer.flush()
    except Exception as e:
        print(f"[Proxy S2C Error] {e}", file=sys.stderr)

async def main():
    # 啟動子行程 mcp_server.py（加入 -u 參數確保無緩衝即時傳輸）
    server_cmd = [sys.executable, "-u", "mcp_server.py"]
    
    print("[Proxy] 正在啟動 Secure MCP Proxy 代理中介層...", file=sys.stderr)
    process = await asyncio.create_subprocess_exec(
        *server_cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # 雙向轉發任務
    t1 = asyncio.create_task(forward_client_to_server(process.stdin))
    t2 = asyncio.create_task(forward_server_to_client(process.stdout))

    await asyncio.gather(t1, t2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Proxy] 已安全關閉。", file=sys.stderr)