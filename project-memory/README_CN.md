# Project Memory 技能 (增强版)

<div align="center">

**Claude Code 智能项目记忆**

*让 AI 真正理解你的项目历史*

[![MemOS](https://img.shields.io/badge/Powered%20by-MemOS-blue)](https://github.com/MemTensor/MemOS)
[![Claude Code](https://img.shields.io/badge/For-Claude%20Code-orange)](https://claude.ai)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## 增强版新特性

| 特性 | 描述 |
|------|------|
| 🧠 **智能触发器** | 根据语言模式自动判断何时搜索/保存 |
| 🔴 **错误模式学习** | 记住错误签名和解决方案，下次秒解 |
| 📦 **代码模式库** | 保存可复用代码模板，检测相似代码时建议复用 |
| 🔗 **决策链追踪** | 追踪决策演进历史，理解"为什么" |
| ⚠️ **主动提醒** | 在你重蹈覆辙之前预警 |
| 🕸️ **知识图谱** | 关联相关记忆，提供更好的上下文 |

---

## 工作原理

```
┌─────────────────────────────────────────────────────────────────┐
│                       智能记忆工作流                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  用户操作            智能触发              AI 响应               │
│  ────────           ────────             ────────               │
│                                                                  │
│  "之前怎么做的"  ───>  语言检测      ───>  搜索历史记录          │
│  "last time..."                                                  │
│                                                                  │
│  写代码         ───>  模式匹配      ───>  建议使用模板          │
│                                          "要用 CODE_PATTERN 吗?" │
│                                                                  │
│  遇到错误       ───>  签名匹配      ───>  显示解决方案          │
│                                          来自 ERROR_PATTERN     │
│                                                                  │
│  危险操作       ───>  GOTCHA 匹配   ───>  主动警告              │
│                                          "上次这样做时..."       │
│                                                                  │
│  完成任务       ───>  自动评估      ───>  提示保存记忆          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 记忆类型

### 标准类型

| 类型 | 图标 | 用途 |
|------|------|------|
| `[MILESTONE]` | ✅ | 重要里程碑 |
| `[BUGFIX]` | 🐛 | Bug 修复及解决方案 |
| `[FEATURE]` | ✨ | 新功能实现 |
| `[DECISION]` | 🏗️ | 架构/设计决策 |
| `[GOTCHA]` | ⚠️ | 坑点和注意事项 |
| `[CONFIG]` | ⚙️ | 配置变更 |
| `[PROGRESS]` | 📊 | 进度更新 |

### 增强类型 (新增)

| 类型 | 图标 | 用途 |
|------|------|------|
| `[ERROR_PATTERN]` | 🔴 | 可复用的错误签名 + 解决方案 |
| `[CODE_PATTERN]` | 📦 | 可复用的代码模板 |
| `[DECISION_CHAIN]` | 🔗 | 决策演进时间线 |
| `[KNOWLEDGE]` | 📚 | 项目通用知识 |

---

## 智能触发器

### 语言模式检测

| 你说的话 | AI 自动执行 |
|----------|------------|
| "之前"、"上次"、"以前" | 搜索历史记录 |
| "还记得"、"remember" | 搜索特定记忆 |
| "为什么"、"原因" | 搜索决策记录 |
| "错误"、"error"、"怎么解决" | 搜索 ERROR_PATTERN |
| "类似"、"similar" | 搜索 CODE_PATTERN |
| "进度"、"status" | 搜索里程碑 |

### 代码上下文检测

| 你在做的事 | AI 自动执行 |
|-----------|------------|
| 打开文件编辑 | 搜索该文件相关的记忆 |
| 出现错误信息 | 搜索匹配的 ERROR_PATTERN |
| 创建新文件 | 搜索类似的文件模式 |
| 修改配置 | 搜索 CONFIG 历史 |
| 写重复代码 | 建议使用已有的 CODE_PATTERN |

---

## 错误模式学习

解决错误后，AI 会结构化保存以便下次秒识别：

```markdown
[ERROR_PATTERN] Project: my-api | Date: 2025-01-25

## 错误签名
- 类型: ModuleNotFoundError
- 信息: No module named 'uvicorn'
- 场景: Windows 便携环境

## 根本原因
PATH 没有设置 conda_venv/Scripts

## 解决方案
1. 检查 Python 路径: `where python`
2. 设置 PATH: `set PATH=%CD%\conda_venv;%CD%\conda_venv\Scripts;%PATH%`

## 预防措施
始终使用 run.bat 启动，它会正确设置 PATH

Tags: error, ModuleNotFoundError, PATH, windows
```

**下次遇到同样错误** → AI 立即显示解决方案！

---

## 代码模式库

保存可复用的代码模式：

```markdown
[CODE_PATTERN] Project: my-api | Pattern: 异步重试装饰器

## 用途
通用的指数退避重试装饰器

## 模板
```python
def async_retry(retries=3, delay=1.0, backoff=2.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # ... 重试逻辑
        return wrapper
    return decorator
```

## 使用位置
- src/services/api.py:25
- src/db/connection.py:42
```

**当 AI 检测到类似代码** → 建议："要使用现有模式吗？"

---

## 决策链追踪

追踪决策如何演进：

```markdown
[DECISION_CHAIN] Project: my-api | Topic: 认证方式

## 演进时间线
| 日期 | 决策 | 理由 |
|------|------|------|
| 01-10 | Session | 简单熟悉 |
| 01-15 | JWT | 无状态可扩展 |
| 01-25 | JWT + Refresh | 平衡安全和体验 |

## 当前决策
JWT + Refresh Token

## 为何改变
Session 不好扩展；纯 JWT 有安全顾虑
```

**当你在认证相关代码工作时** → AI 展示决策历史和理由

---

## 主动提醒

AI 在你重蹈覆辙之前警告：

```
⚠️ 注意：上次修改 redis.conf 时遇到了连接超时问题。
   记得在配置更改后重启 Redis 容器。

   相关记忆: [GOTCHA-REDIS-001]
```

### 提醒触发优先级

| 优先级 | 类型 | 触发时机 |
|--------|------|----------|
| 🔴 高 | 坑点/错误预防 | 危险操作之前 |
| 🟡 中 | 代码模式建议 | 写类似代码时 |
| 🟢 低 | 进度检查点 | 完成 3+ 任务后 |

---

## 快速开始

### 安装

```bash
# 复制 skill 到 Claude Code 技能目录
cp -r project-memory ~/.claude/skills/

# 运行安装脚本获取 CLI 命令
bash ~/.claude/skills/project-memory/scripts/linux/install.sh

# Windows
%USERPROFILE%\.claude\skills\project-memory\scripts\windows\install.cmd
```

### CLI 命令

```bash
memos-init                           # 初始化项目
memos-save "内容" -t TYPE            # 保存记忆
memos-search "关键词"                # 搜索记忆
```

### 记忆类型选项

```bash
memos-save "修复了登录 bug" -t BUGFIX
memos-save "选择了 PostgreSQL" -t DECISION
memos-save "认证系统完成" -t MILESTONE
memos-save "Docker 需要 2GB 内存" -t GOTCHA
memos-save "重试装饰器模式" -t CODE_PATTERN
memos-save "连接错误解决方案" -t ERROR_PATTERN
```

---

## 目录结构

```
project-memory/
├── SKILL.md                    # AI 行为指令 (增强版)
├── README.md                   # 英文文档
├── README_CN.md                # 本文件
├── LICENSE
├── references/
│   └── examples.md             # 记忆格式示例 (增强版)
└── scripts/
    ├── memos_init_project.py   # 初始化项目
    ├── memos_save.py           # 保存记忆
    ├── memos_search.py         # 搜索记忆
    ├── linux/
    │   ├── install.sh
    │   ├── memos-init.sh
    │   ├── memos-save.sh
    │   └── memos-search.sh
    └── windows/
        ├── install.cmd
        ├── install.ps1
        ├── memos-init.cmd
        ├── memos-save.cmd
        └── memos-search.cmd
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API 地址 |
| `MEMOS_USER` | `dev_user` | 默认用户 ID |
| `MEMOS_CUBES_DIR` | `~/.memos_cubes` | 记忆存储目录 |

---

## 前置要求

- [MemOS](https://github.com/MemTensor/MemOS) 运行在 `localhost:18000`
- Python 3.10+
- Claude Code CLI

---

## 使用场景示例

### 场景 1：错误识别

```
👤 你：启动应用时出现 "ConnectionRefusedError"

🤖 AI：[搜索 ERROR_PATTERN...]

    找到匹配的错误模式！

    📌 ERROR_PATTERN: ConnectionRefusedError - Redis 启动

    根本原因：应用启动时 Redis 容器还没准备好

    解决方案：
    1. 在 docker-compose.yml 中给 Redis 添加 healthcheck
    2. 使用 `depends_on: condition: service_healthy`

    [GOTCHA-REDIS-001]
```

### 场景 2：代码复用

```
👤 你：我需要给这个 API 调用添加重试逻辑

🤖 AI：我注意到你有一个现成的模式！

    📦 CODE_PATTERN: 异步重试装饰器

    已在以下位置使用：
    - src/services/api.py:25
    - src/db/connection.py:42

    要使用这个模式以保持一致性吗？
```

### 场景 3：决策上下文

```
👤 你：我们为什么用 JWT 而不是 session？

🤖 AI：[搜索 DECISION_CHAIN...]

    🔗 DECISION_CHAIN: 认证方式

    演进历程：
    • 01-10: Session → 简单但不好扩展
    • 01-15: JWT → 无状态但有安全顾虑
    • 01-25: JWT + Refresh → 当前方案（平衡）

    当前理由：需要支持多端（web、mobile、CLI）
    各有不同的安全需求
```

---

## 相关链接

- [MemOS](https://github.com/MemTensor/MemOS) - 记忆后端
- [Claude Code](https://claude.ai) - Anthropic CLI
- [完整示例](references/examples.md) - 记忆格式模板

---

## 许可证

MIT License
