"""对照实验桩：重放真实 Responses 事件流，可配初始静默时长与是否发保活注释。

用来判定「Codex 是否因流静默而重连」，以及「SSE 注释行能否当保活」。
"""
import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CAPTURE = str(_devcommon.TMP / "sse_capture.txt")
ARGS = None
POST_COUNT = 0
LOCK = threading.Lock()


def load_events():
    """把抓下来的原始 SSE 文本切成 (event名, data) 列表。"""
    out = []
    name = None
    for line in open(CAPTURE, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("event: "):
            name = line[7:]
        elif line.startswith("data: ") and name:
            out.append((name, line[6:]))
            name = None
    return out


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            body = json.dumps({"models": []}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        global POST_COUNT
        n = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(n) if n else None
        with LOCK:
            POST_COUNT += 1
            idx = POST_COUNT
        print(f"[stub] 收到第 {idx} 次 POST {self.path}", flush=True)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        # 初始静默期（模拟上游首字节很慢）
        if ARGS.delay > 0:
            if ARGS.keepalive <= 0:
                time.sleep(ARGS.delay)
            else:
                left = ARGS.delay
                while left > 0:
                    step = min(ARGS.keepalive, left)
                    time.sleep(step)
                    left -= step
                    try:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                    except Exception as e:
                        print(f"[stub] 保活写失败: {e}", flush=True)
                        return

        try:
            for name, data in load_events():
                self.wfile.write(f"event: {name}\ndata: {data}\n\n".encode("utf-8"))
                self.wfile.flush()
        except Exception as e:
            print(f"[stub] 写事件失败: {e}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8799)
    ap.add_argument("--delay", type=float, default=0, help="首字节前的静默秒数")
    ap.add_argument("--keepalive", type=float, default=0, help="保活间隔秒；0=不发")
    ARGS = ap.parse_args()
    print(f"[stub] 监听 {ARGS.port}  delay={ARGS.delay}s keepalive={ARGS.keepalive}s", flush=True)
    ThreadingHTTPServer(("127.0.0.1", ARGS.port), Handler).serve_forever()
