"""量化对比：Codex 走 WorkBuddy vs Codex 原生费率（同一 token 消耗）。"""
import json
import os
import subprocess
import time

USAGE = str(_devcommon.TMP / "wb_usage.jsonl")
TASK = ("创建 fib.py：实现 fib(n) 返回第 n 个斐波那契数（迭代写法）；"
        "创建 t.txt 写入 '10'；运行 python -c \"from fib import fib; print(fib(10))\" 确认输出 55")
CODEX_CMD = wbdiscover.find_codex()
FLAGS = [
    CODEX_CMD, "exec", "--skip-git-repo-check",
    "-c", "model_provider=workbuddy",
    "-c", 'model_providers.workbuddy.name="WorkBuddy"',
    "-c", 'model_providers.workbuddy.base_url="http://127.0.0.1:8787/v1"',
    "-c", 'model_providers.workbuddy.env_key="WORKBUDDY_AI_API_KEY"',
    "-c", 'model_providers.workbuddy.wire_api="responses"',
    "-c", "model_providers.workbuddy.requires_openai_auth=false",
    "-c", "model_context_window=1000000", "-c", "model_max_output_tokens=128000",
    "--sandbox", "workspace-write",
]

# OpenAI Codex 官方费率（credits / 1M tokens，Standard 速度）
CODEX = {
    "gpt-6-luna":  {"in": 2.5, "cached": 0.25, "out": 12.5},
    "gpt-6-sol":   {"in": 50,  "cached": 5,    "out": 250},
    "gpt-6-astra": {"in": 250, "cached": 25,   "out": 1250},
    "gpt-6.1-sol": {"in": 50,  "cached": 2.5,  "out": 250},
}
CODEX_USD_PER_CREDIT = 0.04
WB_PRO_CREDITS = 3500.0
WB_PRO_USD = 10.0

env = dict(os.environ, WORKBUDDY_AI_API_KEY="workbuddy-local")
os.makedirs(str(_devcommon.WORK), exist_ok=True)


def run(model):
    d = str(_devcommon.WORK)
    for f in ("fib.py", "t.txt"):
        p = os.path.join(d, f)
        if os.path.exists(p):
            os.remove(p)
    if os.path.exists(USAGE):
        os.remove(USAGE)
    t0 = time.time()
    r = subprocess.run(FLAGS + ["-m", model, TASK], cwd=d, env=env,
                       capture_output=True, text=True, timeout=900,
                       stdin=subprocess.DEVNULL)
    dt = time.time() - t0
    rows = []
    if os.path.exists(USAGE):
        for line in open(USAGE, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    tok = {
        "in": sum(x.get("in") or 0 for x in rows),
        "cached": sum(x.get("cached") or 0 for x in rows),
        "out": sum(x.get("out") or 0 for x in rows),
        "reasoning": sum(x.get("reasoning") or 0 for x in rows),
        "credit": sum(float(x.get("credit") or 0) for x in rows),
        "turns": len(rows),
    }
    ok = os.path.exists(os.path.join(d, "fib.py"))
    return tok, dt, ok, r.stdout


print(f"{'模型':12} {'轮次':>4} {'输入':>8} {'缓存':>8} {'输出':>7} {'WB积分':>9} "
      f"{'WB$':>9} {'Codex积分':>10} {'Codex$':>8} {'省':>7} {'耗时':>7} 文件")
for m in ["gpt-6-luna", "gpt-6-sol"]:
    tok, dt, ok, out = run(m)
    wb_usd = tok["credit"] * (WB_PRO_USD / WB_PRO_CREDITS)
    r = CODEX.get(m)
    if r:
        unc = max(0, tok["in"] - tok["cached"])
        cx_cr = unc / 1e6 * r["in"] + tok["cached"] / 1e6 * r["cached"] + tok["out"] / 1e6 * r["out"]
    else:
        cx_cr = 0
    cx_usd = cx_cr * CODEX_USD_PER_CREDIT
    save = (1 - wb_usd / cx_usd) * 100 if cx_usd else 0
    print(f"{m:12} {tok['turns']:>4} {tok['in']:>8} {tok['cached']:>8} {tok['out']:>7} "
          f"{tok['credit']:>9.3f} {wb_usd:>9.5f} {cx_cr:>10.2f} {cx_usd:>8.4f} "
          f"{save:>6.1f}% {dt:>6.0f}s {'✓' if ok else '✗'}")
