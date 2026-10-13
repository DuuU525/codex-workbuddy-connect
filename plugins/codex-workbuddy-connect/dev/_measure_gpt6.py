"""实测各 GPT-6 档的积分消耗率（credits per 1M tokens）。"""
import json
import sys
import time

import _devcommon  # noqa: F401  （提供 BIN / TMP / WORK 等路径）

_devcommon.guard_paid("本脚本使用收费模型做费率测量")
import wbproxy  # noqa: E402

c = wbproxy.Credentials()
SYS = {"role": "system", "content": "You are a terse assistant. Answer in one short sentence."}
USR = {"role": "user", "content": "What is the capital of France? Answer in one short sentence."}


def run(model, usr=USR):
    p = {"model": model, "messages": [SYS, usr]}
    t0 = time.time()
    r, _ = wbproxy.open_upstream(c, p)
    usage = None
    for ev in wbproxy.iter_sse(r):
        if ev.get("usage"):
            usage = ev["usage"]
    r.close()
    return usage, time.time() - t0


def credits():
    d = c.credits()
    return d["remaining"]


MODELS = ["gpt-6-luna", "gpt-6-sol", "gpt-6.1-sol", "gpt-6-astra"]
print(f"{'模型':16} {'prompt':>7} {'completion':>10} {'cached_hit':>10} {'credit':>8} {'耗时':>7}  余额变化")
for m in MODELS:
    before = credits()
    try:
        u, dt = run(m)
    except Exception as e:
        print(f"{m:16} 失败: {type(e).__name__}: {str(e)[:80]}")
        continue
    time.sleep(1)
    after = credits()
    u = u or {}
    print(f"{m:16} {u.get('prompt_tokens'):>7} {u.get('completion_tokens'):>10} "
          f"{u.get('prompt_cache_hit_tokens'):>10} {str(u.get('credit')):>8} {dt:>6.1f}s  "
          f"{before} -> {after} (Δ {round(before-after,4)})")
    print(f"{'':16} 完整 usage: {json.dumps(u, ensure_ascii=False)[:400]}")
