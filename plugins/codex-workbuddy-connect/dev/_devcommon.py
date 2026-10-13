"""dev/ 诊断脚本共用的路径解析——不写死任何机器路径。

在 dev/ 下运行脚本时 Python 会把 dev/ 放进 sys.path[0]，所以直接 `import _devcommon` 即可。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent      # 包根目录
BIN = PKG_ROOT / "bin"                                 # 代理与生成器所在
SCRIPTS = PKG_ROOT / "scripts"                         # 启动器所在
DEV = PKG_ROOT / "dev"
WORK = DEV / "_work"                                   # 临时产物目录
TMP = Path(tempfile.gettempdir())                      # 系统临时目录

# Hermes 安装位置（只有跑 Hermes 插件相关诊断时才用到）
HERMES_HOME = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
HERMES_AGENT = HERMES_HOME / "hermes-agent"
HERMES_PLUGIN = HERMES_HOME / "plugins" / "model-providers" / "workbuddy-ai"

# 让 `import wbproxy` / `wbdiscover` 等可用
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))


# ── 费用保护 ────────────────────────────────────────────────
# 诊断脚本默认只碰免费档：hy3 / step-5-preview / deepseek-v4.1-flash 实测 0 积分。
# 要换成别的模型：设 WB_MODEL=<slug>。
FREE_MODEL = os.environ.get("WB_MODEL") or "deepseek-v4.1-flash"

# 这些模型按积分计费（credits / 1M tokens，实测值）
PAID_MODELS = {
    "glm-5.3-flash": 0.12,
    "glm-5.3": 0.12,
    "gpt-6-luna": 0.38,
    "hy4-preview": 0.02,
    "gpt-6-sol": 7.51,
    "deepseek-v4.1-flash-sg": 1.06,
}


def guard_paid(what: str) -> None:
    """跑「会真扣积分」的诊断前必须显式同意：设 WB_ALLOW_PAID=1。

    没有这道闸，别人拿到包随手跑一个探测脚本就会静默花掉自己的积分。
    """
    if os.environ.get("WB_ALLOW_PAID") == "1":
        return
    print(f"[费用保护] {what} 会真实消耗 WorkBuddy 积分。")
    print("          其用量按上游计费，可能一次数积分。确要运行请设：")
    print("            set WB_ALLOW_PAID=1")
    print("          只想跑不计费的检查：把模型设成免费档（WB_MODEL=hy3）。")
    raise SystemExit(2)
