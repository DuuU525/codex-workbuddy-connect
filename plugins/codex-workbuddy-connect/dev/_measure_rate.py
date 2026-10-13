"""精确测 WorkBuddy 的积分率：输入/输出各一个系数。

做法：同一模型跑两种规模，解出 credits per 1M input / output tokens。
用小倍率模型（luna x0.07）把成本压到最低，再拿 sol 验证倍率关系。
"""
import json
import sys
import time

import _devcommon  # noqa: F401  （提供 BIN / TMP / WORK 等路径）

_devcommon.guard_paid("本脚本使用收费模型做费率测量")
import wbproxy  # noqa: E402

c = wbproxy.Credentials()
FILLER = "The quick brown fox jumps over the lazy dog. " * 40   # ~450 tokens/块


def run(model, filler_blocks, want_long_answer=False):
    sysmsg = "You are a helpful assistant. " + (FILLER * filler_blocks)
    usr = ("Write a detailed 300-word explanation of how a CPU pipeline works."
           if want_long_answer else "Say OK.")
    p = {"model": model, "messages": [
        {"role": "system", "content": sysmsg},
        {"role": "user", "content": usr}]}
    r, _ = wbproxy.open_upstream(c, p)
    usage = None
    for ev in wbproxy.iter_sse(r):
        if ev.get("usage"):
            usage = ev["usage"]
    r.close()
    return usage


print("=== 小样本 ===")
for blocks, long_ans in [(1, False), (20, False), (20, True)]:
    u = run("gpt-6-luna", blocks, long_ans)
    print(f"  luna blocks={blocks:3} long={long_ans!s:5} -> in={u['prompt_tokens']:6} "
          f"out={u['completion_tokens']:5} credit={u.get('credit')}")

print("\n=== 解线性方程（luna）===")
a = run("gpt-6-luna", 1, False)
b = run("gpt-6-luna", 40, False)
d = run("gpt-6-luna", 40, True)
print(f"  A: in={a['prompt_tokens']} out={a['completion_tokens']} credit={a.get('credit')}")
print(f"  B: in={b['prompt_tokens']} out={b['completion_tokens']} credit={b.get('credit')}")
print(f"  C: in={d['prompt_tokens']} out={d['completion_tokens']} credit={d.get('credit')}")

# luna 倍率 0.07；用 B 与 A 的差分离输入系数
ca, cb, cc = a.get("credit") or 0, b.get("credit") or 0, d.get("credit") or 0
din = b["prompt_tokens"] - a["prompt_tokens"]
dcredit = cb - ca
if din > 0:
    rate_in = (dcredit / din) * 1_000_000
    print(f"\n  输入系数 ≈ {rate_in:.1f} credits / 1M input tokens （luna x0.07）")
    print(f"  → 基率 ≈ {rate_in / 0.07:.1f} credits / 1M input tokens（倍率归一化后）")

print("\n=== 倍率验证：同尺寸跑 sol (x1.33) 与 astra (x6.67) ===")
for m in ["gpt-6-luna", "gpt-6-sol", "gpt-6-astra"]:
    u = run(m, 20, False)
    print(f"  {m:14} in={u['prompt_tokens']:6} out={u['completion_tokens']:4} "
          f"credit={u.get('credit')}")
