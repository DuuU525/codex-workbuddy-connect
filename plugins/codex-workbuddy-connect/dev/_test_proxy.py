"""代理端到端测试：非流式、流式、工具调用。

默认走免费档模型（见 _devcommon.FREE_MODEL），跑一次 0 积分。
上游偶发 429（账号级限流 code 14003）已被识别并给提示，不会抛堆栈。
"""
import json
import os
import urllib.error
import urllib.request
import _devcommon  # noqa: F401  （路径常量 + 费用保护）

BASE = "http://127.0.0.1:8787"
RETRY_WAIT = int(os.environ.get("WB_429_WAIT") or 65)   # 上游提示等待约 1 分钟


def post(payload, stream, _tries=0):
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer workbuddy-local"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            if not stream:
                return json.loads(r.read().decode("utf-8"))
            lines = [l.decode("utf-8", "replace").strip() for l in r if l.strip()]
        return lines
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        if e.code == 429:
            print(f"  !! 上游 429（账号级限流）：{body}")
            print("     这是上游行为，不是代理的 bug；等待约 1 分钟或换低负载模型重试。")
            if _tries == 0:
                import time
                print(f"     {RETRY_WAIT}s 后自动重试一次（可用 WB_429_WAIT 调整）…")
                time.sleep(RETRY_WAIT)
                return post(payload, stream, _tries=1)
        raise SystemExit(f"  请求失败：HTTP {e.code} {body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"  连不上代理 {BASE}：{e.reason}\n"
                         f"  先启动代理：scripts\\start-wbproxy.cmd")


print("=== 1. 非流式（含中文）===")
d = post({"model": _devcommon.FREE_MODEL, "stream": False,
          "messages": [{"role": "user", "content": "用一句话说明你是谁"}]}, False)
if "choices" in d:
    c = d["choices"][0]
    print("  内容:", (c["message"].get("content") or "")[:180])
    print("  思考长度:", len(c["message"].get("reasoning_content") or ""))
    print("  finish:", c["finish_reason"])
    u = d.get("usage") or {}
    print("  usage: prompt=%s completion=%s credit=%s" % (u.get("prompt_tokens"), u.get("completion_tokens"), u.get("credit")))
else:
    print("  错误:", json.dumps(d, ensure_ascii=False)[:500])

print("\n=== 2. 流式 ===")
lines = post({"model": _devcommon.FREE_MODEL, "stream": True,
              "messages": [{"role": "user", "content": "数到三"}]}, True)
print("  SSE 行数:", len(lines))
print("  首帧:", lines[0][:150])
print("  末帧:", lines[-1][:150])

print("\n=== 3. 工具调用 ===")
d = post({"model": _devcommon.FREE_MODEL, "stream": False,
          "messages": [{"role": "user", "content": "北京天气如何？用工具查。"}],
          "tools": [{"type": "function", "function": {
              "name": "get_weather", "description": "Get current weather for a city",
              "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                             "required": ["city"]}}}]}, False)
msg = (d.get("choices") or [{}])[0].get("message") or {}
tcs = msg.get("tool_calls") or []
print("  是否触发工具:", bool(tcs))
if tcs:
    for t in tcs:
        print("   ", json.dumps(t, ensure_ascii=False)[:260])
print("  finish:", (d.get("choices") or [{}])[0].get("finish_reason"))
