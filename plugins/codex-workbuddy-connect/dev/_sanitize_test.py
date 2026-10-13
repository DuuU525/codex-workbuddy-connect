"""测「system prompt 要清洗到什么程度才放行」，并给出可用方案。"""
import json
import re
import sys

import _devcommon  # noqa: F401  （提供 BIN / TMP / WORK 等路径）
import wbproxy  # noqa: E402

SYS = json.loads(open(str(_devcommon.TMP / "wb_chat.json"), encoding="utf-8").read())["messages"][0]["content"]
creds = wbproxy.Credentials()


def probe(sys_text, label):
    p = {"model": "hy3", "stream": True,
         "messages": [{"role": "system", "content": sys_text},
                      {"role": "user", "content": "ok"}]}
    try:
        r, _ = wbproxy.open_upstream(creds, p)
        sum(1 for _ in wbproxy.iter_sse(r)); r.close()
        print(f"  {label:46} OK   ({len(sys_text)} 字)")
        return True
    except wbproxy.UpstreamError as e:
        try:
            code = json.loads(e.detail).get("code")
        except Exception:
            code = "?"
        print(f"  {label:46} FAIL code={code} ({len(sys_text)} 字)")
        return False
    except Exception as e:
        print(f"  {label:46} ERR {type(e).__name__}")
        return False


def strip_first_para(t: str) -> str:
    """删掉开头的身份段（到第一个 '# ' 标题前）。"""
    i = t.find("\r\n\r\n# ")
    if i < 0:
        i = t.find("\n\n# ")
    return t[i:].lstrip("\r\n") if i > 0 else t


print("原长:", len(SYS))
print("\n--- 逐级清洗 ---")
probe(SYS, "原文")
probe(strip_first_para(SYS), "删掉开头身份段")

# 把身份段替换成中性文字
neutral = ("You are a precise, safe, and helpful coding agent working in a "
           "terminal-based assistant harness.")
body = strip_first_para(SYS)
probe(neutral + "\r\n\r\n" + body, "身份段换成中性描述")

# 再试：把提到的产品名全替换掉
scrub = SYS
for bad, good in [("Codex CLI", "the CLI"), ("Codex", "the assistant"), ("OpenAI", "the vendor")]:
    scrub = scrub.replace(bad, good)
probe(scrub, "全文替换产品名（Codex/OpenAI）")

print("\n--- 若仍有残留，逐段二分 ---")
lo, hi = 0, len(SYS)
if not probe(SYS[:2000], "前 2000 字"):
    while hi - lo > 100:
        mid = (lo + hi) // 2
        if probe(SYS[:mid], f"前 {mid} 字"):
            lo = mid
        else:
            hi = mid
    print(f"\n  首个触发段落区间: {lo}~{hi}")
    print("  片段:", repr(SYS[lo:hi][:300]))
