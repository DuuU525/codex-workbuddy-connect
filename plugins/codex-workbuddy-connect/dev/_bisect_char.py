"""把触发点精确到字符，并验证是不是某个短语。"""
import json
import sys

import _devcommon  # noqa: F401  （提供 BIN / TMP / WORK 等路径）
import wbproxy  # noqa: E402

base = json.loads(open(str(_devcommon.TMP / "wb_chat.json"), encoding="utf-8").read())
SYS = base["messages"][0]["content"]
creds = wbproxy.Credentials()

print("SYS[160:200] =", repr(SYS[160:200]))
print("SYS[178:186] =", repr(SYS[178:186]))
print()


def probe(label, sys_text):
    p = {"model": "hy3", "stream": True,
         "messages": [{"role": "system", "content": sys_text},
                      {"role": "user", "content": "ok"}]}
    try:
        r, _ = wbproxy.open_upstream(creds, p)
        n = sum(1 for _ in wbproxy.iter_sse(r)); r.close()
        print(f"  {label:50} OK")
        return True
    except wbproxy.UpstreamError as e:
        try:
            j = json.loads(e.detail); print(f"  {label:50} {e.status} code={j.get('code')}")
        except Exception:
            print(f"  {label:50} {e.status}")
        return False
    except Exception as e:
        print(f"  {label:50} {type(e).__name__}")
        return False


print("--- 逐字符推进前缀 ---")
for mid in range(174, 192):
    probe(f"[0:{mid}] ...{SYS[max(0,mid-12):mid]!r}", SYS[:mid])

print("\n--- 片段单独作为 system ---")
for frag in ["You are expected to be precise, safe, and helpful.",
             "precise, safe, and helpful.",
             "safe, and helpful.",
             "helpful.",
             "Your capabilities:",
             "You are expected to be precise"]:
    probe(repr(frag), frag)

print("\n--- 在良性 system 后追加片段 ---")
for frag in ["You are expected to be precise, safe, and helpful.",
             "Your capabilities:",
             "ok. Your capabilities:"]:
    probe("良善+ " + repr(frag), "You are a helpful assistant. " + frag)
