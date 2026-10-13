---
description: 把 WorkBuddy 接入 Codex（安装 / 修复 / 重装）
argument-hint: "[--skip-doctor] [--no-skill] [--no-agents-rule]"
allowed-tools: [Bash, Read, Glob, Grep]
---

# 安装 WorkBuddy → Codex 接入

用户调用了本命令，参数：`$ARGUMENTS`

## 步骤

1. 先做体检，把结果如实报给用户：

```cmd
python "<插件根>\bin\setup.py" doctor
```

2. 若体检标了 `!!`，按提示补齐后再继续（缺 Python/cryptography、未登录 WorkBuddy 桌面端、
   缺 Codex 都属要先解决的项）。**不要**自己下载或安装 WorkBuddy 桌面端 —— 让用户自己装并登录。

3. 体检通过后安装：

```cmd
python "<插件根>\bin\setup.py" install $ARGUMENTS
```

4. 安装完了跑 `status` 确认：

```cmd
python "<插件根>\bin\setup.py" status
```

5. 用一句话告诉用户怎么开始用：`codex --profile wb`，或者桌面端**新建会话**。

## 注意

- `<插件根>` 是插件被安装后的真实目录，用这个命令找到它：
  `dir /b /s "%USERPROFILE%\.codex\plugins\cache\workbuddy\codex-workbuddy-connect"`
- 安装是幂等的：重复运行不会改动已就绪的内容，也不会累积空行。
- 不要修改 `config.toml` 里本插件以外的段落。
- 如果安装失败（退出码非 0），把 `!!` 那行原样贴给用户，不要自己猜。
