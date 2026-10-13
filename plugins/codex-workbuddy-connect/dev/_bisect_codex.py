"""对 Codex 的真实 chat payload 做二分，找出触发 11128 的字段。"""
import copy
import json
import sys

import _devcommon  # noqa: F401  （提供 BIN / TMP / WORK 等路径）
import wbproxy  # noqa: E402

SRC = str(_devcommon.TMP / "wb_chat.json")
base = json.loads(open(SRC, encoding="utf-8").read())
creds = wbproxy.Credentials()

print("基线：消息 %d 条，工具 %d 个，顶层字段 %s" % (
    len(base["messages"]), len(base.get("tools") or []),
    sorted(k for k in base if k not in ("model", "messages", "stream"))))


def probe(label, mut=None, drop=()):
    p = copy.deepcopy(base)
    for k in drop:
        p.pop(k, None)
    if mut:
        mut(p)
    try:
        r, _ = wbproxy.open_upstream(creds, p)
        n = sum(1 for _ in wbproxy.iter_sse(r))
        r.close()
        print(f"  {label:32} -> OK ({n} 帧)")
        return True
    except wbproxy.UpstreamError as e:
        try:
            j = json.loads(e.detail)
            print(f"  {label:32} -> {e.status} code={j.get('code')} {j.get('msg')}")
        except Exception:
            print(f"  {label:32} -> {e.status} {e.detail[:90]}")
        return False
    except Exception as e:
        print(f"  {label:32} -> {type(e).__name__}: {str(e)[:90]}")
        return False


print("\n--- 逐项删除 ---")
probe("原样", None, ())
probe("去掉 tools", None, ("tools",))
probe("去掉 parallel_tool_calls", None, ("parallel_tool_calls",))
probe("去掉 tool_choice", None, ("tool_choice",))
probe("去掉 reasoning_effort", None, ("reasoning_effort",))
probe("只留 system+user（去掉第 3 条）", lambda p: p.__setitem__("messages", p["messages"][:2]), ("tools",))
probe("只留 user（无 system）", lambda p: p.__setitem__("messages", p["messages"][1:2]), ("tools",))
probe("system 截断到 500 字", lambda p: p["messages"][0].__setitem__("content", p["messages"][0]["content"][:500]), ("tools",))

print("\n--- 只保留前 N 个工具 ---")
for n in (1, 3, 6, 12):
    probe(f"tools 前 {n} 个", lambda p, n=n: p.__setitem__("tools", (p.get("tools") or [])[:n]))

print("\n--- 工具名 ---")
if base.get("tools"):
    print("  工具列表:", [t.get("function", {}).get("name") for t in base["tools"]])
