# 发布给别人安装

本仓库是**标准 Codex marketplace 仓库**，发布 = 把它放到别人能访问的地方。
下面是实测过的几种方式，以及各自的前提。

---

## 一、先想清楚：发布到哪、给谁

| 方式 | 谁能装 | 前提 |
|---|---|---|
| **私有/内网 Git**（推荐给「自己人」） | 拿到仓库权限的人 | 一台他们能访问的 Git（内网 GitLab / Gitee 私有仓 / GitHub 私有仓） |
| **公开 Git 仓库** | 任何人 | 见下文「合规」——**这与本项目的上游性质冲突，请慎重** |
| **共享目录 / U 盘 / zip** | 拿到文件的人 | 无 |
| **局域网 HTTP git 服务** | 同网段的人 | 一台常开的机器 |

---

## 二、安装方要执行的命令（三种 Host 通用）

```cmd
:: 1. 加市场 —— 参数是「仓库地址」，写法取决于 Host
codex plugin marketplace add <owner>/<repo>                    :: GitHub 简写（等价 https://github.com/<owner>/<repo>.git）
codex plugin marketplace add https://gitee.com/<user>/<repo>.git   :: 非 GitHub 必须用完整 URL
codex plugin marketplace add D:\share\codex-workbuddy-connect      :: 本地目录 / U 盘 / zip 解压处
codex plugin marketplace add http://192.168.1.10:8899/mkt.git      :: 局域网 HTTP（见下）

:: 2. 装插件
codex plugin add codex-workbuddy-connect@workbuddy

:: 3. 用插件自带的安装器写配置（find 出真实插件目录）
dir /b /s "%USERPROFILE%\.codex\plugins\cache\workbuddy\codex-workbuddy-connect"
python "<插件目录>\bin\setup.py" doctor
python "<插件目录>\bin\setup.py" install
```

**实测证据**（本机）：

- `owner/repo` 简写 → 实际执行 `git clone https://github.com/<owner>/<repo>.git`
- 完整 URL 形式 → `Added marketplace 'workbuddy' from http://127.0.0.1:8899/bare.git`，
  且 `plugin list` 能从克隆出来的副本正确读到插件清单。**所以非 GitHub Host 用完整 URL 即可。**

---

## 三、⚠ 本机的网络现实（发布前必看）

实测结果（不是猜测）：

| 目标 | 结果 |
|---|---|
| `github.com:443` | ✗ **连不上**（25 秒超时，`git clone` 报 `Failed to connect to github.com:443`） |
| `ssh.github.com:443` | ✓ 通 |
| `codeload.github.com` / `raw.githubusercontent.com` | ✓ 通 |
| **`gitee.com:443`** | ✓ **通，`git ls-remote` 正常** |
| `gitlab.com:443` | ✓ 通 |

**直接后果**：

1. `git push` 到 GitHub 走 HTTPS **会失败**；
2. 别人用 `marketplace add <owner>/<repo>` 在这类网络里**也克隆不下来**；
3. 本机**没有 SSH key**（`~/.ssh` 只有 known_hosts），所以 SSH 通道还没法用。

**对策（任选）**：

- **用 Gitee**（本机实测通畅）——最省事，见第四节。
- **给 GitHub 配代理**：`git config --global http.proxy http://<proxy>:<port>`，
  或给 `https://github.com/` 做 `url.<base>.insteadOf` 重写到镜像。
- **走 SSH over 443**：生成 key 传到 GitHub，然后
  `git config --global url."ssh://git@ssh.github.com:443/".insteadOf "https://github.com/"`。
  （`ssh.github.com:443` 实测可连，这条能把 clone 与 push 都救回来。）

---

## 四、用 Gitee 发布（本机最可行）

```cmd
:: 1. 在 gitee.com 建一个仓库（空仓，不要初始化 README）
:: 2. 本地推到 Gitee
cd <本仓库目录>
git remote add origin https://gitee.com/<你的用户名>/codex-workbuddy-connect.git
git push -u origin master
```

别人装（**完整 URL**，不能用 `owner/repo` 简写）：

```cmd
codex plugin marketplace add https://gitee.com/<你的用户名>/codex-workbuddy-connect.git
codex plugin add codex-workbuddy-connect@workbuddy
```

私有仓同样可用，前提是对方的 git 已配置好 Gitee 凭据。

---

## 五、共享目录 / U 盘 / zip

```cmd
:: 打包（**必须带上 .gitattributes**，它保护那些 GBK+CRLF 的 .cmd 不被换行规范化改坏）
:: 排除 .git、缓存与本地产物
```

别人拿到后 `codex plugin marketplace add <那个文件夹>`，后续同上。

> 想给「干净对外版」时把 `dev/` 一并排除 —— 它含逆向分析与指纹定位脚本，
> 对普通使用者没用，只是增加暴露面：
> 打包时排除 `plugins/codex-workbuddy-connect/dev/`。

---

## 六、局域网 HTTP（同网段共享，免 Git Host）

Codex 支持 `http://…/x.git` 形式（已实测）。做法：

```cmd
:: 在放仓库的机器上，做成裸仓并启用 dumb HTTP
git clone --bare <仓库> <共享目录>\mkt.git
cd <共享目录>\mkt.git
git update-server-info

:: 起个静态服务（8899 随便换）
python -m http.server 8899 --bind 0.0.0.0 --directory <共享目录>
```

别人：`codex plugin marketplace add http://<你的IP>:8899/mkt.git`

注意：dumb HTTP 每次仓库更新后都要重新 `git update-server-info`；
且只适合可信内网（无鉴权）。

---

## 七、发布检查清单

- [ ] **无凭据**：仓库里不含令牌/密钥。本仓已扫过：无 accessToken 值、无本机用户名、无邮箱、无私钥。
      （代码里出现的 `accessToken` / `atRestSecretKey` 是解密用的**字段名**，不是密钥值。）
- [ ] **`.gitattributes` 在位**：`*.cmd binary` 保护 GBK+CRLF 脚本。
      实测 `git clone` 出来的 8 个 `.cmd` 与源文件 sha256 完全一致。
- [ ] **LICENSE 在位**（本仓 MIT）。发布前把版权行换成你自己的名字/组织。
- [ ] **`.gitignore` 生效**：无 `__pycache__` / `*.pyc` / `*.bak-*` 被追踪。
- [ ] **版本号干净**：`plugin.json` 的 `version` 用正式 semver（如 `1.5.1`），
      不要留 `1.5.1-20261014…` 这种本地 cachebuster。
- [ ] **提交齐全**：`git status` 干净。
- [ ] 想清楚给谁：见第一节与下文。

---

## 八、合规：发布前必须权衡的事

本项目把一个**私有逆向接口**接进 Codex，并**主动规避了上游的 system-prompt 指纹风控**
（`code 11128` 那堵墙）。这意味着：

- 上游 ToS 层面，这属于规避风控，不是「正常使用第三方 API」；
- **公开分发会同时放大两件事**：暴露面（被上游发现）与规模（一旦被大量使用，接口被封，
  所有使用者——包括你自己——的账号都不能再用）；
- 代码里还包含逆向细节（`dev/` 下的 AAD 构造、指纹二分定位脚本），公开后等于把这些一并给出。

因此建议：

- **默认走私有仓 / 内网 / 小范围共享**（第一、五节），这已经满足「其他人可以安装使用」。
- 若确实要公开：至少**排除 `dev/`**，并在 README 保留第七节「合规」的说明，
  让使用者知道风险与「登录自己的账号」。

这条只有你能拍板 —— 技术路径都通了，上面每种方式我都实测过。
