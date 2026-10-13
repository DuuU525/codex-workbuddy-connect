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

## 给别人安装使用

### 给对方什么

三种给法，任选其一（三种都在本机实测过）：

| 给法 | 怎么给 | 对方怎么装 |
|---|---|---|
| **Git 仓库**（推荐） | 推到 GitHub（公开或私有）或公司内网 Git | `codex plugin marketplace add <owner>/<repo>` |
| **共享目录 / U 盘** | 把整个仓库文件夹拷过去 | `codex plugin marketplace add <那个文件夹>` |
| **压缩包** | 打包成 zip 发过去 | 解压后 `codex plugin marketplace add <解压出的文件夹>` |

> 打包时**必须保留 `.gitattributes`**：它把 `*.cmd` 标记为 binary，防止 git 的换行规范化
> 破坏那些 GBK+CRLF 的中文脚本。仓库已配好，打包 zip 时也照原样带上。
> （实测：`git clone` 出来的 8 个 `.cmd` 与源文件 sha256 完全一致。）

### 对方需要什么

| 项 | 要求 | 说明 |
|---|---|---|
| **Windows** | — | 依赖 `%LOCALAPPDATA%`、直接调 `.exe`，非跨平台 |
| **WorkBuddy AI 桌面端** | 已安装**且已登录** | 凭据来源。**不需要常驻运行** |
| **Python** | 3.10+，含 `cryptography` | 用于 AES-256-GCM 解密 |
| **Codex** | 0.153.x（已验证） | 0.16x 的 unified-exec helper 在本机会失败，别盲目升 |

缺什么先跑 `doctor.cmd` —— 它会逐项告诉你，并给出补法。

### 对方要执行的命令

```cmd
:: 1. 加市场（三种给法只差这一个参数）
codex plugin marketplace add <owner>/<repo>        :: GitHub
codex plugin marketplace add D:\share\codex-workbuddy-connect   :: 共享目录/U盘
codex plugin marketplace add %USERPROFILE%\Downloads\codex-workbuddy-connect  :: zip 解压处

:: 2. 装插件
codex plugin add codex-workbuddy-connect@workbuddy

:: 3. 体检（缺 Python / 没登录 WorkBuddy 等会在这里报出来）
python "%USERPROFILE%\.codex\plugins\cache\workbuddy\codex-workbuddy-connect\<版本>\bin\setup.py" doctor

:: 4. 安装（幂等，可反复跑）
python "%USERPROFILE%\.codex\plugins\cache\workbuddy\codex-workbuddy-connect\<版本>\bin\setup.py" install
```

第 3、4 步也可以让 Codex 自己跑 —— 会话里打 **`/workbuddy-setup`**（本插件带的命令），
它就是替你执行体检 + 安装。

### 另一种给法：个人市场（不用 marketplace add）

把 `plugins/codex-workbuddy-connect/` 拷到 `~/plugins/`，并把
`.agents/plugins/marketplace.json` 的条目合并进 `~/.agents/plugins/marketplace.json`，然后
`codex plugin add codex-workbuddy-connect@personal`。
个人市场是**隐式发现**的，不需要 `marketplace add`。

### 装完怎么算成功

```cmd
codex plugin list -m workbuddy      :: 应显示 installed, enabled
codex --profile wb                  :: 能进会话
```

进会话后问一句「当前实际在用哪个模型」，或直接 `curl -s http://127.0.0.1:8787/wb/last-model`。
（**别让模型读 config.toml 回答** —— 那是新建会话的默认值，不是当前会话在用的。）

### 更新与重装

Codex 按**版本号**物化插件，版本不变不会重读，所以改了内容要先升版本：

```cmd
python <插件根>\bin\bump-plugin.py <插件目录>
codex plugin add codex-workbuddy-connect@workbuddy
```

⚠ **重装前先确保没有进程"待在"插件目录里**：Codex 会先给旧缓存目录改名，有进程把它当工作目录
（比如你自己 `cd` 进去过、或代理进程还在跑）就会报
`failed to back up plugin cache entry: 拒绝访问 (os error 5)`。
处理：停掉代理（`taskkill /F /IM python.exe` 里挑 wbproxy 那个）、退出在那个目录里的终端，
必要时重启桌面端，然后重试。

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
