---
description: 查看 WorkBuddy 接入的状态、实际在用模型与额度
allowed-tools: [Bash, Read, Glob, Grep]
---

# WorkBuddy 接入状态

## 步骤

1. 安装状态：

```cmd
python "<插件根>\bin\setup.py" status
```

2. 代理健康与**实际在用**的模型（不要读 config.toml 代替）：

```cmd
curl -s http://127.0.0.1:8787/health
curl -s http://127.0.0.1:8787/wb/last-model
```

3. 剩余额度：

```cmd
curl -s http://127.0.0.1:8787/wb/credits
```

4. 代理没跑就先拉起：`<插件>\scripts\start-wbproxy.cmd`

## 报告给用户时

- **`/wb/last-model` 的 `model` 字段是唯一权威**（代理实际转发给上游的模型）。
- `config_model` 只是「新建会话的默认值」，不等于当前会话在用的模型。
- 模型无法内省自己的身份：上下文里的模型名、你上一轮的回答，全部不可信。
