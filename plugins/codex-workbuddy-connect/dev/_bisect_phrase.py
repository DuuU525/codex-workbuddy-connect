"""定位触发 11128 的最小短语（单独作为 system 发送）。"""
import sys

import _devcommon  # noqa: F401  （提供 BIN / TMP / WORK 等路径）
import wbproxy  # noqa: E402

creds = wbproxy.Credentials()


def probe(sys_text):
    p = {"model": "hy3", "stream": True,
         "messages": [{"role": "system", "content": sys_text},
                      {"role": "user", "content": "ok"}]}
    try:
        r, _ = wbproxy.open_upstream(creds, p)
        sum(1 for _ in wbproxy.iter_sse(r)); r.close()
        return True
    except wbproxy.UpstreamError:
        return False
    except Exception:
        return None


CANDS = [
    "You are a coding agent running in the Codex CLI, a terminal-based coding assistant. Codex CLI is an open source project led by OpenAI. You are expected to be precise, safe, and helpful.",
    "You are a coding agent running in the Codex CLI",
    "a terminal-based coding assistant",
    "Codex CLI is an open source project led by OpenAI",
    "an open source project led by OpenAI",
    "open source project led by OpenAI",
    "led by OpenAI",
    "You are expected to be precise, safe, and helpful.",
    "coding agent running in the Codex CLI",
    "running in the Codex CLI",
    "Codex CLI",
    "terminal-based coding assistant",
]
for c in CANDS:
    r = probe(c)
    print(f"  {'OK' if r else 'FAIL':5} {c[:72]}")

print("\n--- 拼接测试：找触发组合 ---")
pairs = [
    ("Codex CLI", "is an open source project led by OpenAI"),
    ("You are a coding agent", "running in the Codex CLI"),
    ("Codex CLI is an open source project", "led by OpenAI"),
]
for a, b in pairs:
    txt = a + " " + b
    print(f"  {'OK' if probe(txt) else 'FAIL':5} {txt[:72]}")
