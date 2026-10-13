"""直连上游，抓取 429 的完整响应体（不打印任何凭据）。"""
import json
import sys
import time
import urllib.error
import urllib.request

import _devcommon  # noqa: F401  （提供 BIN / TMP / WORK 等路径）
import wbproxy  # noqa: E402

creds = wbproxy.Credentials()
print("凭据就绪, uid:", creds.uid[:8], "\n")

payload = {
    "model": "deepseek-v4.1-flash",
    "stream": True,
    "messages": [
        {"role": "system", "content": "简短回答"},
        {"role": "user", "content": "回复：ok"},
    ],
    "stream_options": {"include_usage": True},
}

for i in range(1, 9):
    data = json.dumps(wbproxy._prepare_payload(payload)).encode()
    req = urllib.request.Request(
        wbproxy.GLOBAL_BASE + wbproxy.CHAT_PATH,
        data=data, headers=creds.chat_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            for _ in r:
                break
        print(f"第 {i} 次: 200（正常）")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"第 {i} 次: HTTP {e.code}")
        try:
            doc = json.loads(body)
            print("  完整响应体：")
            print(json.dumps(doc, ensure_ascii=False, indent=2))
        except ValueError:
            print("  ", body[:1200])
        break
    time.sleep(0.4)
