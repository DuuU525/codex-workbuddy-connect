"""测量真实 Codex 形状请求的各模型首字节延迟（TTFB）与静默间隔。"""
import json
import os
import sys
import time
import urllib.request

# 从真实捕获的 Codex 请求里取 system 段（若存在），否则用等长的合成文本
SYS_SRC = str(_devcommon.TMP / "wb_chat2.json")
try:
    cap = json.load(open(SYS_SRC, encoding="utf-8"))
    SYS = cap["messages"][0]["content"]
    TOOLS = cap.get("tools") or []
except Exception:
    SYS = "你是严谨的软件工程助手。" * 400
    TOOLS = []

print(f"system 长度 {len(SYS)} 字, 工具 {len(TOOLS)} 个")


def probe(model, effort, tools=True):
    body = {"model": model, "stream": True,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": "用一句话说明这个项目的目录结构如何"}],
            "stream_options": {"include_usage": True}}
    if tools:
        body["tools"] = TOOLS
    if effort:
        body["reasoning_effort"] = effort
    data = json.dumps(body).encode()
    t0 = time.time()
    req = urllib.request.Request("http://127.0.0.1:8787/v1/chat/completions", data=data,
                                headers={"Content-Type": "application/json",
                                         "Authorization": "Bearer x"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            first = None
            last = None
            gaps = []
            n = 0
            for line in r:
                if not line.strip():
                    continue
                now = time.time()
                n += 1
                if first is None:
                    first = now - t0
                if last is not None and now - last > 2:
                    gaps.append(round(now - last, 1))
                last = now
            print(f"  {model:12} effort={str(effort):5} 首字节 {first:>7.2f}s  "
                  f"总 {time.time()-t0:>7.2f}s  事件 {n:>4}  >2s静默 {gaps[:5]}")
    except Exception as e:
        print(f"  {model:12} effort={str(effort):5} 失败: {type(e).__name__}: {e}")


_models = [("hy3", "low"), ("deepseek-v4.1-flash", "low")]
if os.environ.get("WB_ALLOW_PAID") == "1":   # 默认只测免费档
    _models += [("gpt-6-luna", "low"), ("gpt-6-sol", "medium")]
for m, _eff in _models:
    for eff in ["low", "high"]:
        probe(m, eff)
