"""同一 agent 任务在 WorkBuddy 各 GPT-6 档上的实测成本 → 换算 Codex。

跑真任务（带工具），从代理的 usage 日志汇总 token，再用两套费率算钱。
"""
import json
import os
import subprocess
import sys
import time

USAGE = str(_devcommon.TMP / "wb_usage.jsonl")
TASK = "统计这个目录下 .txt 文件的个数，并用一句话说明你是怎么数的"

# Codex 官方费率（credits / 1M tokens，Standard 速度，含输出倍率）
CODEX = {
    "gpt-6-astra":   {"in": 250, "cached": 25,  "out": 1250},
    "gpt-6.1-sol":   {"in": 50,  "cached": 2.5, "out": 250},
    "gpt-6-sol":     {"in": 50,  "cached": 5,   "out": 250},
    "gpt-6-luna":    {"in": 2.5, "cached": 0.25, "out": 12.5},
    "gpt-5.6-sol":   {"in": 100, "cached": 10,  "out": 500},
    "gpt-5.6-luna":  {"in": 5,   "cached": 0.5, "out": 30},
}
CODEX_USD_PER_CREDIT = 0.04          # 购买 credits 的单价
WB_PRO_CREDITS = 2000 + 50 * 30      # 1000 基础 + 1000 赠送 + 每日活跃 50×30
WB_PRO_USD = 10.0

HERMES = str(_devcommon.HERMES_AGENT / "venv" / "Scripts" / "python.exe")
# 用 hermes 的可执行入口
HERMES_BIN = "hermes"


def run_task(model):
    """跑一次任务，返回 (token 汇总, credit 汇总)。"""
    start = os.path.getsize(USAGE) if os.path.exists(USAGE) else 0
    t0 = time.time()
    r = subprocess.run(
        [HERMES_BIN, "chat", "-q", TASK, "-m", model, "--provider", "workbuddy-ai"],
        capture_output=True, text=True, timeout=900,
    )
    dt = time.time() - t0
    rows = []
    if os.path.exists(USAGE):
        with open(USAGE, encoding="utf-8") as fh:
            fh.seek(start)
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        pass
    tok = {
        "in": sum(r0.get("in") or 0 for r0 in rows),
        "cached": sum(r0.get("cached") or 0 for r0 in rows),
        "out": sum(r0.get("out") or 0 for r0 in rows),
        "reasoning": sum(r0.get("reasoning") or 0 for r0 in rows),
        "credit": sum(float(r0.get("credit") or 0) for r0 in rows),
        "turns": len(rows),
    }
    return tok, dt, r.returncode


def codex_credits(model, tok):
    r = CODEX.get(model)
    if not r:
        return None
    uncached = max(0, tok["in"] - tok["cached"])
    return (uncached / 1e6 * r["in"] + tok["cached"] / 1e6 * r["cached"]
            + tok["out"] / 1e6 * r["out"])


print(f"WorkBuddy Pro 月费 ${WB_PRO_USD}，月度积分约 {WB_PRO_CREDITS}"
      f" → ${WB_PRO_USD / WB_PRO_CREDITS:.5f}/积分")
print(f"Codex credits 单价 ${CODEX_USD_PER_CREDIT}/积分\n")

print(f"{'模型':14} {'轮次':>4} {'输入':>8} {'缓存':>7} {'输出':>6} {'WB积分':>8} "
      f"{'WB$':>9} {'Codex积分':>9} {'Codex$':>8}  倍数")
for m in ["gpt-6-luna", "gpt-6-sol", "gpt-6-astra"]:
    tok, dt, rc = run_task(m)
    wb_usd = tok["credit"] * (WB_PRO_USD / WB_PRO_CREDITS)
    cx_cr = codex_credits(m, tok)
    cx_usd = (cx_cr or 0) * CODEX_USD_PER_CREDIT
    ratio = (wb_usd / cx_usd) if cx_usd else float("inf")
    print(f"{m:14} {tok['turns']:>4} {tok['in']:>8} {tok['cached']:>7} {tok['out']:>6} "
          f"{tok['credit']:>8.3f} {wb_usd:>9.5f} {(cx_cr or 0):>9.2f} {cx_usd:>8.4f}  "
          f"{ratio:>5.2f}x")
    time.sleep(2)
