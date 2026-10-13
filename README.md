# codex-workbuddy-connect

把 **WorkBuddy AI 桌面端**已登录的模型接进 **Codex**（CLI 与桌面端）——不需要 OpenAI 订阅，
也不需要 Codex 套餐。打完包就是一个标准的 **Codex plugin marketplace** 仓库。

```
Codex ──► 127.0.0.1:8787（本地代理）──► workbuddy.ai ──► 真实模型
           │  解密桌面端登录态
           │  Responses ⇄ Chat Completions 转换
           │  记录/同步「实际在用」的模型
           │  生成模型切换列表
```

---

## 仓库结构

这是 **marketplace 仓库**的形态（`.agents/plugins/marketplace.json` + `plugins/<名字>/`）：

```
codex-workbuddy-connect/
├─ .agents/plugins/marketplace.json          市场索引（Codex 据此发现插件）
├─ README.md                                  本文件：怎么装
└─ plugins/codex-workbuddy-connect/           插件本体
   ├─ .codex-plugin/plugin.json               插件清单（必填项已按官方 schema 校验）
   ├─ skills/                                 codex-workbuddy-connect、query-current-model
   ├─ commands/                               /workbuddy-setup、/workbuddy-status
   ├─ hooks/hooks.json                        SessionStart：代理没跑就自动拉起
   ├─ scripts/                                codex-wb.cmd、start-wbproxy.cmd、hook 入口
   ├─ bin/                                    代理与安装器（Python）
   ├─ install.cmd / uninstall.cmd / status.cmd / doctor.cmd
   └─ README.md                               插件的详细文档（排错、费率、坑）
```

---

## 安装

### 前置条件

| 项 | 要求 | 说明 |
|---|---|---|
| **Windows** | — | 依赖 `%LOCALAPPDATA%`、直接调 `.exe`，非跨平台 |
| **WorkBuddy AI 桌面端** | 已安装**且已登录** | 凭据来源。**不需要常驻运行** |
| **Python** | 3.10+，含 `cryptography` | 用于 AES-256-GCM 解密 |
| **Codex** | 0.153.x（已验证） | 0.16x 的 unified-exec helper 在本机会失败，别盲目升 |

缺什么先跑 `doctor.cmd` —— 它会逐项告诉你。

### 方式一：从本地/共享目录装（自己人之间传）

```cmd
:: 1. 把市场加进来（路径换成你放这个仓库的位置）
codex plugin marketplace add C:\path\to\codex-workbuddy-connect

:: 2. 装插件
codex plugin add codex-workbuddy-connect@workbuddy
```

### 方式二：从 Git 仓库装（放到 GitHub 后）

```cmd
codex plugin marketplace add <owner>/codex-workbuddy-connect
codex plugin add codex-workbuddy-connect@workbuddy
```

### 方式三：个人市场（默认路径）

把 `plugins/codex-workbuddy-connect/` 拷到 `~/plugins/`，并把
`.agents/plugins/marketplace.json` 的条目合并进 `~/.agents/plugins/marketplace.json`，
然后：

```cmd
codex plugin add codex-workbuddy-connect@personal
```

个人市场是**隐式发现**的，不需要 `marketplace add`。

### 装完之后：跑一次安装

插件只是把文件铺好；还需要把 provider 写进 Codex 配置：

```cmd
:: 找到插件真实位置
dir /b /s "%USERPROFILE%\.codex\plugins\cache\workbuddy\codex-workbuddy-connect"

:: 体检 → 安装（幂等）
python "<插件根>\bin\setup.py" doctor
python "<插件根>\bin\setup.py" install
```

在 Codex 会话里也可以直接打 `/workbuddy-setup`（本插件带的命令），让 agent 替你跑。

---

## 用法

```cmd
codex --profile wb                          新会话走 WorkBuddy
<插件>\scripts\codex-wb.cmd                等价，且代理没跑会自动拉起
<插件>\scripts\codex-wb.cmd -m hy3         换模型
```

桌面端（Codex app）同理，但**必须新建会话**：provider 与模型是**逐会话绑定**的。

**免费档**（实测 0 积分）：`hy3`、`deepseek-v4.1-flash`、`step-5-preview`。
⚠ `hy4-preview` 名字像免费但**收费**（0.02）。

---

## SessionStart hook：需要信任一次

插件带的 hook 在会话开始时确保代理在跑。**Codex 默认不让 hook 自动执行**，首次在 TUI /
桌面端开会话时会问：

> Hooks need review — Hooks can run outside the sandbox after you trust them.
> [Trust all and continue] [Continue without trusting (hooks won't run)]

选 **Trust all and continue** 即可。不信任也能用，只是代理要自己拉（`codex-wb.cmd` 会拉）。

自动化场景可以跳过信任：`codex exec --dangerously-bypass-hook-trust ...`

---

## 更新插件

版本号变了才需要重装（cache 按版本号分目录）。本地开发时用官方的 cachebuster 流程：

```cmd
python plugins\codex-workbuddy-connect\bin\bump-plugin.py plugins\codex-workbuddy-connect
codex plugin add codex-workbuddy-connect@workbuddy
```

---

## 卸载

```cmd
codex plugin remove codex-workbuddy-connect@workbuddy
codex plugin marketplace remove workbuddy
python "<插件根>\bin\setup.py" uninstall      :: 回退写进 config.toml 的内容
```

---

## 关于分发

- **凭据是 per-machine / per-account 的**：仓库里不含任何账号信息，也不含令牌。
  每个使用者要自己装 WorkBuddy 桌面端、自己登录。
- 上游是**私有逆向接口**，绕过其 system prompt 指纹属于主动规避风控。
  **技术上可以拷给别人用，但请勿公开分发、打包发布或写教程。**
  自己人之间小范围传没问题，别放到公开仓库/网盘/社交平台 —— 一旦被大规模使用，接口被封，
  所有人的号都不能用了。
- 别滥用免费档：高频跑会触发上游账号级限流（`code 14003`，429），影响的是自己的号。

---

## 详细文档

插件内部文档（排错表、费率实测、踩过的坑、dev 诊断脚本）见
[`plugins/codex-workbuddy-connect/README.md`](plugins/codex-workbuddy-connect/README.md)。
