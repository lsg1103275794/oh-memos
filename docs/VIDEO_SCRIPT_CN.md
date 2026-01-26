# MemOSLocal-SM 视频文案大纲

> 为 AI 打造的隐私优先持久记忆系统

---

## [VIDEO] 视频标题建议

- 「让 AI 拥有真正的记忆 - MemOS 本地部署全攻略」
- 「告别遗忘！用 MemOS 给 Claude/GPT 装上永久记忆」
- 「开源项目分享：隐私优先的 AI 记忆操作系统」

---

## [SCRIPT] 视频脚本大纲

### 开场 (30秒)

> "你有没有遇到过这种情况：和 AI 聊了很久的项目，第二天它就全忘了？
> 今天给大家介绍一个开源项目 MemOS，让 AI 真正拥有跨会话、跨项目的持久记忆。"

**画面建议**: 展示 AI 对话中"我不记得之前的对话"的尴尬场景

---

### 第一部分：痛点引入 (1分钟)

**现有问题:**
- AI 对话是"一次性"的，关闭就忘
- 每次都要重复说明项目背景
- 跨项目的经验无法复用
- 云端记忆存在隐私顾虑

**画面建议**:
- 展示重复输入项目背景的场景
- 对比：有记忆 vs 无记忆的对话体验

---

### 第二部分：MemOS 是什么 (2分钟)

**核心概念:**
```
+-------------------------------------------+
|           MemOS Memory System             |
+-------------------------------------------+
|                                           |
|  [*] Memory Cube (记忆立方体)             |
|      +-- 每个项目一个独立的记忆空间       |
|                                           |
|  [*] Memory Types:                        |
|      * ERROR_PATTERN - 错误模式           |
|      * DECISION - 架构决策                |
|      * BUGFIX - Bug 修复记录              |
|      * CODE_PATTERN - 代码模式            |
|      * MILESTONE - 项目里程碑             |
|                                           |
|  [*] Smart Retrieval:                     |
|      * 语义搜索 (向量相似度)              |
|      * 知识图谱 (关系推理)                |
|                                           |
+-------------------------------------------+
```

**画面建议**: 展示架构图动画

---

### 第三部分：核心特性演示 (3分钟)

#### 特性 1: 自动记忆保存

```
场景: 解决一个 Bug 后，AI 自动保存经验

[演示]
User: "这个 HuggingFace 模型加载报错了"
AI: *解决问题*
AI: *自动保存* "ERROR_PATTERN: HuggingFace 在 WSL 环境需要设置 HF_HUB_OFFLINE=1"
```

#### 特性 2: 跨项目记忆检索

```
场景: 在新项目中，AI 主动调用之前的经验

[演示]
User: "帮我配置 Neo4j"
AI: *搜索记忆* -> 找到之前项目的 Neo4j 配置经验
AI: "根据之前在 MemOS 项目的经验，建议使用以下配置..."
```

#### 特性 3: 知识图谱模式

```
场景: 展示 Neo4j 中的记忆关系网络

[演示]
- 打开 Neo4j Browser (localhost:7474)
- 展示记忆节点之间的关联关系
- 演示图谱查询
```

**画面建议**: 实际操作录屏，展示 MCP 工具调用过程

---

### 第四部分：本地部署教程 (3分钟)

#### 环境准备

```
需要的组件:
[*] Python 3.10+ (便携版即可)
[*] Ollama (本地嵌入模型)
[*] Qdrant (向量数据库，单文件)
[*] Neo4j Community (可选，知识图谱)
```

#### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/lsg1103275794/MemOSLocal-SM

# 2. 安装依赖
pip install -e .

# 3. 配置 .env
cp .env.example .env

# 4. 启动数据库
start_db.bat

# 5. 启动 API
run.bat

# 6. 配置 Claude Code MCP
# 编辑 ~/.claude.json
```

**画面建议**: 快进演示完整安装过程

---

### 第五部分：与 Claude Code 集成 (2分钟)

#### MCP 配置

```json
{
  "mcpServers": {
    "memos": {
      "command": "python",
      "args": ["path/to/memos_mcp_server.py"],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user"
      }
    }
  }
}
```

#### 主动模式演示

```
[演示场景]
1. 遇到错误 -> AI 自动搜索历史解决方案
2. 完成任务 -> AI 主动保存经验
3. 新项目开始 -> AI 提示相关历史记忆
```

**画面建议**: 展示 Claude Code 终端中的 MCP 工具调用日志

---

### 第六部分：隐私优势 (1分钟)

```
+-------------------------------------------+
|           100% Local Deployment           |
+-------------------------------------------+
| [*] 数据存储在本地磁盘                    |
| [*] 无需云端账号                          |
| [*] 离线可用                              |
| [*] 完全掌控你的 AI 记忆                  |
+-------------------------------------------+
```

**对比表格:**

| 特性 | MemOS Local | 云端方案 |
|------|-------------|----------|
| 数据位置 | 本地 | 云服务器 |
| 隐私性 | 完全私有 | 依赖服务商 |
| 离线使用 | Yes | No |
| 成本 | 免费 | 可能付费 |

---

### 结尾 (30秒)

> "MemOS 让 AI 从'金鱼记忆'进化到'大象记忆'。
>
> 项目完全开源，欢迎 Star 和贡献！
>
> 链接在评论区，我们下期见！"

**画面建议**: 展示 GitHub 页面，显示 Star 按钮

---

## [MATERIALS] 补充素材

### 演示数据准备

```bash
# 预先保存一些演示用的记忆
curl -X POST http://localhost:18000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "memory_content": "[ERROR_PATTERN] HuggingFace 模型在 WSL 环境加载失败，需要设置 HF_HUB_OFFLINE=1"
  }'
```

### 关键截图清单

- [ ] MemOS API 文档页面 (localhost:18000/docs)
- [ ] Qdrant Dashboard (localhost:6333/dashboard)
- [ ] Neo4j Browser 知识图谱
- [ ] Claude Code MCP 调用日志
- [ ] 跨项目记忆检索效果

### 背景音乐建议

- 轻快的电子/Lo-fi 风格
- 避免有歌词的音乐

---

## [DESCRIPTION] 视频描述模板

```
【开源项目】MemOSLocal-SM - 为 AI 打造的隐私优先持久记忆系统

[Features]
* 跨会话持久记忆
* 跨项目经验复用
* 知识图谱关系推理
* 100% 本地运行，保护隐私

[Tech Stack]
* Qdrant 向量数据库
* Neo4j 知识图谱
* Ollama 本地嵌入
* MCP 协议集成 Claude Code

[Links]
GitHub: https://github.com/lsg1103275794/MemOSLocal-SM

[Docs]
* 部署指南: docs/DB/LOCAL_DEPLOYMENT_CN.md
* MCP 配置: docs/MCP_GUIDE.md

#AI #开源 #Claude #记忆系统 #本地部署
```

---

## [DURATION] 视频时长建议

| 版本 | 时长 | 内容 |
|------|------|------|
| 短视频版 | 2-3分钟 | 痛点 + 核心特性演示 |
| 完整版 | 8-10分钟 | 全部内容 |
| 教程版 | 15-20分钟 | 详细部署步骤 |

---

<div align="center">

**Good luck with your video!**

</div>
