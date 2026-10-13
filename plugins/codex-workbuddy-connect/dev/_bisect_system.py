"""二分 Codex system prompt，找出触发 11128 的片段。"""
import json
import sys

import _devcommon  # noqa: F401  （提供 BIN / TMP / WORK 等路径）
import wbproxy  # noqa: E402

SRC = str(_devcommon.TMP / "wb_chat.json")
base = json.loads(open(SRC, encoding="utf-8").read())
SYS = base["messages"][0]["content"]
USER = base["messages"][1]["content"]
creds = wbproxy.Credentials()

print("system 总长:", len(SYS), "字符")


def probe(label, sys_text):
    p = {"model": "hy3", "stream": True,
         "messages": [{"role": "system", "content": sys_text},
                      {"role": "user", "content": "ok"}]}
    try:
        r, _ = wbproxy.open_upstream(creds, p)
        n = sum(1 for _ in wbproxy.iter_sse(r))
        r.close()
        print(f"  {label:44} OK ({n} 帧)")
        return True
    except wbproxy.UpstreamError as e:
        try:
            j = json.loads(e.detail)
            print(f"  {label:44} {e.status} code={j.get('code')}")
        except Exception:
            print(f"  {label:44} {e.status} {e.detail[:70]}")
        return False


print("\n--- 简单文本对照 ---")
probe("You are a helpful assistant.", "You are a helpful assistant.")
probe("You are a coding agent.", "You are a coding agent.")
probe("含 'Codex'", "You are a coding agent running in the Codex CLI.")
probe("含 'OpenAI'", "This is a project led by OpenAI.")
probe("含 'open source'", "Codex CLI is an open source project.")
probe("含 'terminal-based'", "You are a terminal-based coding assistant.")
probe("含 'harness'", "You receive context provided by the harness.")

print("\n--- 二分原文 ---")
lo, hi = 0, len(SYS)
fails = probe("全文", SYS)
while hi - lo > 8:
    mid = (lo + hi) // 2
    ok = probe(f"[0:{mid}] {mid} 字", SYS[:mid])
    if ok:
        lo = mid
    else:
        hi = mid
print(f"\n触发点在 {lo}~{hi} 之间：")
print("  尾部 80 字:", repr(SYS[max(0, lo - 80):hi + 80]))
