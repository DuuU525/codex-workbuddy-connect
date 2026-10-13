# WorkBuddy AI → Hermes

把 **WorkBuddy AI（国际版）桌面端**的登录态变成 Hermes 可用的模型源。
装完即可在 Hermes 里用 `--provider workbuddy-ai` 调用它的全部 27 个对话模型
（GPT-6 / GPT-5.6 / GPT-5.5 / GLM-5.3 / Kimi-K3 / Gemini-3.5-Flash / Hy3 …）。

```
WorkBuddy AI 桌面端 (已登录)
        │  ① 跑它自带的 Electron 取 at-rest 密钥
        │  ② 解密 %LOCALAPPDATA%\CodeBuddyExtension\...\workbuddy-desktop-ai.info
        ▼
   wbproxy.py  ← 本机 OpenAI 兼容端点 (127.0.0.1:8787)
        │  ③ 转发 /v2/chat/completions，处理令牌刷新 / 强制流式 / developer 折回
        ▼
   Hermes  provider "workbuddy-ai"
```

## 组成

| 文件 | 作用 |
|---|---|
| `wbproxy.py` | 本地代理：解密凭据、转发对话、刷新令牌、报积分。零第三方依赖（仅 stdlib + `cryptography`）。 |
| `~/AppData/Local/hermes/plugins/model-providers/workbuddy-ai/__init__.py` | Hermes provider 插件：注册 `workbuddy-ai`，代理没跑就自动拉起。 |
| `_probe_*.py` / `_test_*.py` | 逆向上游时的探针与端到端测试，留档用。 |

## 快速开始

不需要手动起代理——插件会在第一次用到时自动拉起。直接：

```bash
hermes chat -q "你好" -m hy3 --provider workbuddy-ai          # hy3 免费
hermes chat -q "重构这个函数" -m gpt-5.6-luna --provider workbuddy-ai   # 便宜主力档
```

会话内切换：`/model --provider workbuddy-ai` 或 `/model gpt-5.6-luna`。

## 手动运维

```bash
# 独立启动（调试用，--verbose 打印每步）
python wbproxy.py --verbose

# 额度与账号
curl -s http://127.0.0.1:8787/health      # 账号 + 令牌到期
curl -s http://127.0.0.1:8787/wb/credits  # 剩余积分、按套餐拆分
curl -s http://127.0.0.1:8787/v1/models   # 实时模型目录
```

环境变量：`WORKBUDDY_AI_AUTH_FILE`（凭据路径）、`WORKBUDDY_AI_APP`（Electron 可执行文件）、
`WORKBUDDY_AI_PROXY_PORT`、`WORKBUDDY_AI_PROXY_AUTOSTART=0`（关自动拉起）、
`WORKBUDDY_AI_PROXY_SCRIPT`（代理脚本路径）。

## 上游协议要点（全部实测，非推测）

| 事实 | 证据 |
|---|---|
| 凭据加密：`{$wbEncrypted:1, envelope}` AES-256-GCM，密钥须由 WorkBuddy 自己的 Electron 提供 | `process._linkedBinding("electron_browser_workbuddy_storage").loggerGet()` → `{version:1, atRestSecretKey}`；`protectorKey = sha256(secret)`；AAD 为 `WB-AAD\0\x01 len("WBEV1") sym-v1 suite keyId \x02\x00\x00` |
| 对话端点 `POST /v2/chat/completions` | — |
| **必须 `stream: true`** | 否则 `400 code 11101 Non-stream chat request is currently not supported` |
| **首条消息必须是 `system`** | 否则 `400 code 11128 Illegal API invocation from an unapproved channel` |
| **完全不接受 `developer` 角色**（任何位置） | 同上错误码；Hermes 对 OpenAI 系模型恰好会把 system 改写成 developer，故代理必须折回 |
| 模型目录 `GET /v3/config`，UA 须为 `WorkBuddyAI/<App版本>` | 不带产品名的 UA 会被拒（400 code 12403） |
| 令牌刷新 `POST /v2/plugin/auth/token/refresh`，头 `X-Refresh-Token` | 只在此端点带该头 |
| 额度 `POST /v2/billing/meter/get-user-resource`，body `{PageNumber,PageSize,ProductCode:"p_tcaca"}` | 返回按套餐的 `CapacityRemain/Size` |
| 响应里 `usage.credit` 即本次消耗积分 | 实测 hy3 为 0，gpt-5.6-luna 一次 28s/4 工具调用的 agent 任务为 0.45 |
| 兼容字段：`max_tokens`、`max_completion_tokens`、`temperature`、`reasoning`、`reasoning_effort`、`stream_options`、`response_format`(json_schema/json_object)、`tool_choice`、`parallel_tool_calls` | 逐个实发验证通过 |

## 换算参考（实测，非官方口径）

- 免费档（`x0.00`）：`hy3`、`deepseek-v4.1-flash`、`step-5-preview` → **不扣积分**
- 便宜主力：`gpt-6-luna` x0.07、`gpt-5.6-luna` x0.14、`glm-5.3-flash` x0.06、`kimi-k2.6` x0.52
- 贵档：`gpt-6-astra` x6.67（是 luna 的 48 倍）、`gpt-5.6-sol` x3.47
- 实测一次 28 秒、4 次工具调用的 agent 任务（luna）≈ **0.45 积分**

## 风险

- 走的是 WorkBuddy **未公开的私有接口**（逆向所得），上游一改即失效；登录态与积分走你自己的账号。
- 凭据解密依赖 WorkBuddy AI 桌面端本身：App 卸载、升级改动绑定名、或换机器未登录，代理都会启动失败。
- 仅供本机个人使用。
