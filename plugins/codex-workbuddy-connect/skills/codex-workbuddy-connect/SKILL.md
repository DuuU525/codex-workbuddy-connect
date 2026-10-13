---
name: codex-workbuddy-connect
description: >-
  把 WorkBuddy AI 桌面端已登录的模型接进 Codex（CLI 与桌面端），或排查该接入的问题。
  Use when the user wants to use WorkBuddy/CodeBuddy models in Codex, asks about the
  workbuddy model provider, the local proxy on 127.0.0.1:8787, the free WorkBuddy models
  (hy3 / deepseek-v4.1-flash / step-5-preview), the /workbuddy-setup or /workbuddy-status
  commands, model-switching not taking effect, or 429 rate limits from the WorkBuddy upstream.
metadata:
  short-description: WorkBuddy 模型接入 Codex
---

# Codex × WorkBuddy Connect

让 Codex 用 WorkBuddy AI 桌面端的登录态当模型源 —— 不需要 OpenAI 订阅，也不需要 Codex 套餐。
Codex 只出它的 agent 骨架（读写文件、跑命令、apply_patch、多轮工具循环），模型换成 WorkBuddy 的。

```
Codex ──► 127.0.0.1:8787（本地代理）──► workbuddy.ai ──► 真实模型
           │  解密桌面端登录态
           │  Responses ⇄ Chat Completions 转换
           │  记录/同步「实际在用」的模型
           │  生成模型切换列表
```

## 这个插件把代码装在哪

插件自己的目录就是安装源。所有脚本都在插件根下：

| 路径 | 用途 |
|---|---|
| `install.cmd` | 一键安装（写 config.toml provider / profile / 模型目录 / 技能 / 指令规则） |
| `uninstall.cmd` | 卸载（只回退本插件写入的内容） |
| `doctor.cmd` | 环境体检：Python / cryptography / 桌面端 / 凭据 / Codex / 端口 |
| `status.cmd` | 看安装状态与实际在用模型 |
| `scripts\codex-wb.cmd` | 启动 Codex：代理没跑会自动拉起 |
| `scripts\start-wbproxy.cmd` | 只启动代理（`--verbose` 看请求流水） |
| `bin\wbproxy.py` | 本地代理本体 |
| `bin\wbdiscover.py` | 路径自动发现（桌面端 / Python / Codex / 凭据） |

**插件被安装后会被复制到** `%USERPROFILE%\.codex\plugins\cache\<marketplace>\<plugin>\<version>\`，
所以上表里的路径要按那个真实位置拼。先找到它：

```cmd
dir /b /s "%USERPROFILE%\.codex\plugins\cache\workbuddy\codex-workbuddy-connect"
```

## 装完之后怎么用

```cmd
codex --profile wb                        新会话走 WorkBuddy
<插件>\scripts\codex-wb.cmd               等价，且代理没跑会自动拉起
<插件>\scripts\codex-wb.cmd -m hy3        换模型
```

桌面端（ChatGPT.exe / Codex app）同理，但**必须新建会话** —— provider 与模型是**逐会话绑定**的，
旧会话记着自己创建时的设置，改配置不会让它跟随。

## 免费档（实测 0 积分）

`hy3`、`deepseek-v4.1-flash`、`step-5-preview`。

⚠ `hy4-preview` **名字带 preview 但是收费的**（实测 0.02）——别凭名字判断。
默认档取 `deepseek-v4.1-flash`（免费里上下文 300k / 输出 128k 最大）。

## 「当前在用哪个模型」必须现查

模型**无法内省自己的身份**，而 `config.toml` 里的 `model` 只是**新建会话的默认值** ——
在会话里用选择器切换是**运行时覆盖，不会写回配置**。所以不要读配置回答，要问代理：

```cmd
curl -s http://127.0.0.1:8787/wb/last-model
```

代理是唯一看到真实 `model` 字段的一方。`/health` 也带 `last_model`。
细节见同插件的 `query-current-model` 技能。

## 上游 429（`exceeded retry limit, last status: 429`）

这是**上游账号级限流**，不是代理的 bug。响应体 `code 14003`，官方提示
「等待约 1 分钟，或切换到负载较低的模型」。429 不计费。
实测连续 8 次请求就会出现 `200,429,200,429…` 交替 —— 按账号整体活跃度算，不看你打得多快。
代理日志里会有一行可读摘要（默认就记，不需要 `--verbose`）：

```
[wbproxy] 上游错误 429: code=14003 / too many requests / 建议等待约 1 分钟后重试，或切换到负载较低的模型。
```

## 排错顺序

1. 代理在不在：`curl -s http://127.0.0.1:8787/health`
2. 起不来 → `doctor.cmd`，看是缺桌面端、缺凭据、还是缺 cryptography
3. 起来了但报错 → 看日志 `%TEMP%\wbproxy.log`
4. 报 429 → 见上，等 1 分钟或换模型
5. 桌面端看不到 WorkBuddy 模型 → 模型目录 `model_catalog.json` 没生成对，重跑 `install.cmd`
6. 桌面端旧会话不跟随 → 新建会话

## 合规

上游是**私有逆向接口**，绕过其 system prompt 指纹属于主动规避风控。
**自己人小范围用没问题，不要公开分发、打包发布或写教程。**
让每个使用者登录自己的账号，不要传别人的凭据文件。
