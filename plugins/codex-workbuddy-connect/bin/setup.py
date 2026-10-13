"""codex-workbuddy-connect 安装 / 卸载器。

做四件事（全部幂等，可反复执行）：

  1. 在 $CODEX_HOME/config.toml 写入 [model_providers.workbuddy] 段
  2. 写入 $CODEX_HOME/wb.config.toml（profile 本体；0.162 起 profile 必须是独立文件）
  3. 生成 $CODEX_HOME/workbuddy-catalog.json（模型切换列表的数据源）
  4. 安装 query-current-model 技能，并可选地在 AGENTS.md 里加一条「现查当前模型」规则

用法：
    python setup.py install      [--no-skill] [--no-agents-rule] [--port 8787]
    python setup.py uninstall    [--yes]
    python setup.py status
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wbdiscover  # noqa: E402
from wbdiscover import console_encodings  # noqa: E402

HERE = Path(__file__).resolve().parent          # .../bin
PKG_ROOT = HERE.parent                           # .../codex-workbuddy-connect
PROVIDER = "workbuddy"
PROFILE_NAME = "wb"
MARK_BEGIN = "<!-- BEGIN codex-workbuddy-connect -->"
MARK_END = "<!-- END codex-workbuddy-connect -->"

PROVIDER_BLOCK = f"""[model_providers.{PROVIDER}]
name = "WorkBuddy"
base_url = "http://127.0.0.1:{{port}}/v1"
# 本地代理不校验密钥，占位即可（真正的登录态在代理里）
experimental_bearer_token = "workbuddy-local"
wire_api = "responses"
requires_openai_auth = false
# 上游会返回 429，给足退避重试次数，别让 Codex 很快放弃
request_max_retries = 6
stream_max_retries = 6
"""

PROFILE_BODY = f"""# Codex profile：走 WorkBuddy（本地代理）
#
# 用法：codex --profile {PROFILE_NAME}
# 前提：代理在跑 → scripts\\start-wbproxy.cmd（或 scripts\\codex-wb.cmd 会自动拉起）
# provider 本体在 config.toml 的 [model_providers.{PROVIDER}]

model_provider = "{PROVIDER}"
model = "deepseek-v4.1-flash"
model_reasoning_effort = "low"
"""

AGENTS_RULE = f"""{MARK_BEGIN}
## 回答「当前模型」必须现查（不得凭上下文）

被问到「当前模型 / 现在用的什么模型 / which model / 换模型了吗」等身份类问题时：

**必须现场执行以下命令取数，禁止依据对话历史或记忆回答。**

```bash
curl -s http://127.0.0.1:{{port}}/wb/last-model
```

规则：

- 报告 `model` 字段（代理实际转发给上游的模型，唯一权威）。
- `config_model` 只是「新建会话的默认值」，不等于当前会话在用的模型。
- **模型无法内省自己的身份**：上下文里出现过的模型名、你自己上一轮的回答，全部不可信——
  用户可以在会话中途切换模型，历史消息里没有任何痕迹。
- 每次都重新执行上面的命令，不要复用本会话早先拿到的值。
{MARK_END}
"""


# ── 基础工具 ────────────────────────────────────────────────
def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))


def proxy_python() -> str:
    """挑一个带 cryptography 的 python；挑不到就用当前解释器。"""
    return wbdiscover.find_python() or sys.executable


def port_open(port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def ensure_proxy(port: int, wait: int = 25) -> bool:
    """代理没跑就拉起来，等到端口可用。"""
    if port_open(port):
        return True
    script = HERE / "wbproxy.py"
    if not script.is_file():
        print(f"  找不到 {script}")
        return False
    print(f"  启动代理：{script}")
    flags = 0
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | 0x00000008  # DETACHED_PROCESS
    log = Path(os.environ.get("TEMP", ".")) / "wbproxy.log"
    try:
        with open(log, "ab") as fh:
            subprocess.Popen([proxy_python(), str(script), "--port", str(port)],
                             stdout=fh, stderr=fh, stdin=subprocess.DEVNULL,
                             creationflags=flags, close_fds=True)
    except OSError as e:
        print(f"  启动失败：{e}")
        return False
    for _ in range(wait * 2):
        time.sleep(0.5)
        if port_open(port):
            return True
    print(f"  代理在 {wait} 秒内没有就绪，日志：{log}")
    return False


def backup(path: Path) -> Path | None:
    if not path.is_file():
        return None
    dst = path.with_name(path.name + time.strftime(".bak-cwbc-%H%M%S"))
    shutil.copy2(path, dst)
    return dst


# ── 读写文本并保留原换行符 ──────────────────────────────────
# Codex 在 Windows 上写 CRLF。若用默认的文本模式读写，会把整份配置的换行符改成 LF，
# 表现为 diff 里「整个文件都变了」——必须按二进制原样读写。
def read_text_keep(path: Path) -> str:
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write_text_keep(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def to_newline(text: str, nl: str) -> str:
    """把文本统一成指定换行符（先把已有换行归一成 \\n 再替换）。"""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", nl)


# ── TOML 段落的插入 / 移除（按文本行操作，保留其余内容与注释）──
def strip_section(text: str, header: str) -> str:
    """删掉名为 header 的 [section]（含其后续行，直到下一个 [ 或文件尾）。"""
    lines = text.splitlines(keepends=True)
    out, i, n = [], 0, len(lines)
    removed = False
    while i < n:
        if lines[i].strip() == header:
            removed = True
            i += 1
            while i < n and not lines[i].lstrip().startswith("["):
                i += 1
            # 连同上一行遗留的注释块也顺手让位于下一轮处理
            continue
        out.append(lines[i])
        i += 1
    return "".join(out) if removed else text


def upsert_section(text: str, header: str, body: str) -> str:
    """替换/追加一个 [section] 段。

    必须幂等：同一份输入反复执行，输出字节不变。上一版在追加前无条件补一个分隔空行，
    而 strip_section 不回收上次留下的那一行，于是每装一次就多一行空行（实测 159→160→161 行）。
    这里先把尾部空行清干净，再统一补「恰好一个」分隔空行。
    """
    nl = detect_newline(text)
    text = strip_section(text, header)
    head = text.rstrip("\r\n")
    body_out = to_newline(body, nl).rstrip("\r\n")
    if not head:
        return body_out + nl
    return head + nl + nl + body_out + nl


# ── 各步骤 ──────────────────────────────────────────────────
def step_provider(home: Path, port: int) -> Path | None:
    cfg = home / "config.toml"
    if not cfg.is_file():
        print(f"  !! 找不到 {cfg}，请先安装并至少运行一次 Codex")
        return None
    bak = backup(cfg)
    text = read_text_keep(cfg)
    text = upsert_section(text, f"[model_providers.{PROVIDER}]", PROVIDER_BLOCK.format(port=port))
    write_text_keep(cfg, text)
    print(f"  已写入 [model_providers.{PROVIDER}]" + (f"（备份：{bak.name}）" if bak else ""))
    return cfg


def step_profile(home: Path) -> Path | None:
    prof = home / f"{PROFILE_NAME}.config.toml"
    if prof.is_file():
        bak = backup(prof)
        print(f"  已存在 {prof.name}" + (f"，备份：{bak.name}" if bak else ""))
    write_text_keep(prof, to_newline(PROFILE_BODY, "\r\n"))
    print(f"  已写入 profile：{prof.name}（用法：codex --profile {PROFILE_NAME}）")
    return prof


def step_catalog(home: Path, port: int) -> Path | None:
    out = home / "workbuddy-catalog.json"
    gen = HERE / "gen-catalog.py"
    r = subprocess.run([proxy_python(), str(gen), "--port", str(port), "--out", str(out), "--quiet"],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(f"  生成目录失败：{(r.stderr or r.stdout).strip()[:300]}")
        return None
    print(f"  已生成模型目录：{out.name}")
    return out


def step_skill(home: Path) -> None:
    src = PKG_ROOT / "skills" / "query-current-model"
    if not src.is_dir():
        print("  包里没有 skills/query-current-model，跳过")
        return
    dst = home / "skills" / "query-current-model"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"  已安装技能：{dst}")


def step_agents_rule(home: Path, port: int) -> None:
    agents = home / "AGENTS.md"
    text = read_text_keep(agents) if agents.is_file() else ""
    nl = detect_newline(text) if text else "\r\n"
    rule = to_newline(AGENTS_RULE.format(port=port), nl).rstrip("\r\n")
    if MARK_BEGIN in text:                      # 已装过 → 先移除旧版再写，便于升级
        text = re.sub(re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\r?\n?",
                      "", text, flags=re.S)
    # 与 upsert_section 同理：先清掉上一轮留下的分隔空行，再补「恰好一个」。
    # 不清就会每装一次多一行空行（实测 65a66 / 66a67）。
    text = text.rstrip("\r\n")
    if text:
        text += nl + nl
    bak = backup(agents) if agents.is_file() else None
    write_text_keep(agents, text + rule + nl)
    print(f"  已在 AGENTS.md 加入「现查当前模型」规则" + (f"（备份：{bak.name}）" if bak else ""))


def step_models_note(port: int) -> None:
    """列出可用模型，方便用户挑默认值。"""
    import json
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=20) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print(f"  （读不到模型列表：{e}）")
        return
    ids = [m.get("id") for m in (doc.get("data") or []) if m.get("id")]
    free = {"hy3", "step-5-preview", "deepseek-v4.1-flash"}
    print(f"  可用模型 {len(ids)} 个；实测免费档：{', '.join(sorted(free))}")
    print(f"  改用默认模型：编辑 {codex_home() / (PROFILE_NAME + '.config.toml')} 的 model = \"...\"")


# ── 命令 ────────────────────────────────────────────────────
def cmd_install(args) -> int:
    home = codex_home()
    home.mkdir(parents=True, exist_ok=True)
    print(f"安装到 {home}")
    print(f"包目录 {PKG_ROOT}")

    if not args.skip_doctor:
        print("\n[0/6] 环境体检")
        bad = [c for c in wbdiscover.diagnose(args.port) if not c[1]]
        for name, ok, detail in wbdiscover.diagnose(args.port):
            print(f"  [{'OK ' if ok else '!! '}] {name}: {detail}")
        # 代理没在跑不算致命（下一步会拉起）；其它失败要先解决
        fatal = [c for c in bad if "端口" not in c[0]]
        if fatal:
            print("\n  上面标 !! 的项需要先解决。修好后重跑 install.cmd。")
            if not args.force:
                return 1

    print("\n[1/6] 确保本地代理可用（生成目录需要它）")
    if not ensure_proxy(args.port):
        print("  代理不可用。请先启动并登录 WorkBuddy AI 桌面端，再重试。")
        return 1
    print("  OK")

    print("\n[2/6] 写入 provider")
    if not step_provider(home, args.port):
        return 1

    print("\n[3/6] 写入 profile")
    step_profile(home)

    print("\n[4/6] 生成模型目录")
    step_catalog(home, args.port)

    print("\n[5/6] 附加项")
    if args.no_skill:
        print("  跳过技能安装（--no-skill）")
    else:
        step_skill(home)
    if args.no_agents_rule:
        print("  跳过 AGENTS.md 规则（--no-agents-rule）")
    else:
        step_agents_rule(home, args.port)

    step_models_note(args.port)

    print("\n完成。用法：")
    print(f"  {PKG_ROOT / 'scripts' / 'codex-wb.cmd'}                 # TUI（自动拉起代理）")
    print(f"  {PKG_ROOT / 'scripts' / 'codex-wb.cmd'} exec \"任务\"      # 非交互")
    print(f"  codex --profile {PROFILE_NAME}                            # 已装 Codex 时")
    print("\n注意：桌面端切换模型不会写回 config.toml，代理会自动同步；")
    print("      旧的会话记住自己创建时的模型，改用「新聊天」才走新默认值。")
    return 0


def cmd_uninstall(args) -> int:
    home = codex_home()
    print(f"从 {home} 卸载")
    cfg = home / "config.toml"
    if cfg.is_file():
        bak = backup(cfg)
        text = strip_section(read_text_keep(cfg), f"[model_providers.{PROVIDER}]")
        write_text_keep(cfg, text)
        print(f"  已移除 [model_providers.{PROVIDER}]" + (f"（备份：{bak.name}）" if bak else ""))

    prof = home / f"{PROFILE_NAME}.config.toml"
    if prof.is_file():
        prof.unlink()
        print(f"  已删除 {prof.name}")

    cat = home / "workbuddy-catalog.json"
    if cat.is_file():
        cat.unlink()
        print(f"  已删除 {cat.name}")

    dst = home / "skills" / "query-current-model"
    if dst.is_dir():
        shutil.rmtree(dst)
        print(f"  已删除技能 {dst}")

    agents = home / "AGENTS.md"
    if agents.is_file() and MARK_BEGIN in read_text_keep(agents):
        bak = backup(agents)
        cur = read_text_keep(agents)
        nl = detect_newline(cur)
        text = re.sub(re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\r?\n?",
                      "", cur, flags=re.S)
        write_text_keep(agents, text.rstrip("\r\n") + nl)
        print(f"  已移除 AGENTS.md 规则" + (f"（备份：{bak.name}）" if bak else ""))

    print("\n完成。代理进程若还在跑，可手动结束；包目录未删除。")
    return 0


def cmd_doctor(args) -> int:
    """环境体检：不安装任何东西，只报告缺什么、怎么补。"""
    home = codex_home()
    print(f"CODEX_HOME : {home}")
    print(f"包目录      : {PKG_ROOT}")
    print()
    rows = wbdiscover.diagnose(args.port)
    width = max(len(r[0]) for r in rows)
    for name, ok, detail in rows:
        print(f"  [{'OK ' if ok else '!! '}] {name:<{width}}  {detail}")

    bad = [r for r in rows if not r[1] and "端口" not in r[0]]
    print()
    if bad:
        print("需要处理：")
        for name, _, _ in bad:
            tip = {
                "Python ≥3.10": "装 Python 3.10+（安装时勾选 Add python.exe to PATH），或设 WORKBUDDY_AI_PYTHON",
                "cryptography": '用上一步的 python 执行：python -m pip install cryptography',
                "WorkBuddy 桌面端": "装 WorkBuddy AI 桌面端（国际版）并登录；或用 WORKBUDDY_AI_APP 指定路径",
                "登录凭据": "启动桌面端并完成登录，凭据会自动写出",
                "Codex CLI": "npm i -g @openai/codex，或用 CODEX_WB_CODEX 指定",
            }.get(name, "")
            if tip:
                print(f"  - {name}：{tip}")
        return 1
    print("环境就绪，可以运行 install.cmd")
    return 0


def cmd_status(args) -> int:
    home = codex_home()
    cfg = home / "config.toml"
    text = read_text_keep(cfg) if cfg.is_file() else ""
    print(f"CODEX_HOME          : {home}")
    print(f"provider 段已安装    : {f'[model_providers.{PROVIDER}]' in text}")
    print(f"profile 文件        : {(home / (PROFILE_NAME + '.config.toml')).is_file()}")
    print(f"模型目录            : {(home / 'workbuddy-catalog.json').is_file()}")
    print(f"技能                : {(home / 'skills' / 'query-current-model').is_dir()}")
    ag = home / "AGENTS.md"
    print(f"AGENTS.md 规则      : {ag.is_file() and MARK_BEGIN in read_text_keep(ag)}")
    print(f"代理 {args.port} 在跑 : {port_open(args.port)}")
    if port_open(args.port):
        import json
        import urllib.request
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/wb/last-model", timeout=10) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            print(f"  实际在用模型      : {d.get('model')}")
            print(f"  配置默认          : {d.get('config_model')} (synced={d.get('config_synced')})")
        except Exception as e:
            print(f"  （查询失败：{e}）")
    return 0


def main() -> int:
    console_encodings()
    ap = argparse.ArgumentParser(description="codex-workbuddy-connect 安装器")
    ap.add_argument("--port", type=int, default=int(os.environ.get("WORKBUDDY_AI_PROXY_PORT", 8787)))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("install", help="安装（幂等）")
    p.add_argument("--no-skill", action="store_true", help="不安装 query-current-model 技能")
    p.add_argument("--no-agents-rule", action="store_true", help="不改动全局 AGENTS.md")
    p.add_argument("--skip-doctor", action="store_true", help="跳过环境体检")
    p.add_argument("--force", action="store_true", help="体检查出问题时也继续安装")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("uninstall", help="卸载（保留包目录与备份）")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_uninstall)

    p = sub.add_parser("status", help="查看安装状态与实际在用模型")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("doctor", help="环境体检（不安装任何东西）")
    p.set_defaults(func=cmd_doctor)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
