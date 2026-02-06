# CLI 安装向导设计文档

> **Status**: Implementing (Phase 1-3 Complete)
> **Created**: 2026-02-06
> **Updated**: 2026-02-06
> **Author**: Claude Opus + 李死狗

---

## 概述

创建一个交互式 CLI 安装向导 (`memosctl`)，让用户根据使用场景选择数据库配置，降低入门门槛，实现场景化定制。

## 当前实现状态

已完成:
- ✅ Phase 1: CLI 框架 (init, start, stop, status)
- ✅ Phase 2: MCP 服务器启动器
- ✅ Phase 3: 学生模式日历视图

详见 `docs/plans/` 目录中的各阶段计划。

## 动机

当前问题：
1. 用户需要手动配置 `.env`、`config.json` 等多个文件
2. 默认配置（如数据库密码 `12345678`）不安全
3. 所有用户使用相同的 memory type 体系，不适合非编码场景
4. 入门门槛高，需要理解 Neo4j/Qdrant/Ollama 等技术栈

## 目标用户场景

### 1. 编码开发 (Coding) ✅ 已实现

**用户画像**: 程序员、AI 助手用户（如 Claude Code）

**端口**: 18001

**Memory Types**:
| Type | 用途 | 示例 |
|------|------|------|
| `BUGFIX` | 一次性 bug 修复 | 修复了登录超时问题 |
| `ERROR_PATTERN` | 可复用的错误模式 | ModuleNotFoundError 解决方案 |
| `DECISION` | 技术决策 | 选择 Redis 而非 Memcached |
| `CODE_PATTERN` | 代码模板 | React Hook 最佳实践 |
| `CONFIG` | 配置变更 | 更新了 Nginx 配置 |
| `GOTCHA` | 陷阱/注意事项 | WSL 路径格式问题 |
| `MILESTONE` | 里程碑 | v2.0 发布 |
| `FEATURE` | 新功能 | 添加了用户认证 |

**关系类型**: `CAUSE`, `RELATE`, `CONDITION`, `CONFLICT`

**特殊功能**:
- Git commit 关联
- 代码片段高亮
- Stack trace 解析

---

### 2. 学生学习 (Student) ✅ 已实现

**用户画像**: 学生、课程学习者、知识整理者

**端口**: 18002

**Memory Types**:
| Type | 用途 | 示例 |
|------|------|------|
| `NOTE` | 课堂笔记 | 线性代数第三章笔记 |
| `CONCEPT` | 概念解释 | 什么是特征值 |
| `FORMULA` | 公式定理 | 欧拉公式 e^(iπ)+1=0 |
| `EXAMPLE` | 例题/案例 | 积分例题解法 |
| `SUMMARY` | 章节总结 | 第一单元知识点汇总 |
| `QUESTION` | 疑问待解 | 为什么要用拉格朗日乘数法 |
| `INSIGHT` | 理解感悟 | 微积分和物理的联系 |
| `REVIEW` | 复习记录 | 期中考试复习 |

**关系类型**: `PREREQUISITE`, `EXPLAINS`, `APPLIES`, `EXTENDS`, `CONTRADICTS`

**特殊功能**:
- 📅 学期日历视图 (`memosctl calendar`)
- 按周/课程过滤
- 复习提醒
- 知识图谱可视化

---

### 3. 写作创作 (Writing)

**用户画像**: 小说作者、博客写手、剧本创作者

**Memory Types**:
| Type | 用途 | 示例 |
|------|------|------|
| `DRAFT` | 草稿片段 | 第三章开头的两个版本 |
| `OUTLINE` | 大纲/结构 | 全书十二章结构 |
| `CHARACTER` | 角色设定 | 主角李明的性格背景 |
| `PLOT` | 情节点 | 第五章的反转设计 |
| `SETTING` | 世界观/场景 | 2050年的上海描述 |
| `RESEARCH` | 调研资料 | 关于唐朝服饰的考证 |
| `INSPIRATION` | 灵感记录 | 梦中想到的结局 |
| `REVISION` | 修改记录 | 把被动语态改为主动 |

**关系类型**: `DEVELOPS`, `REFERENCES`, `CONTRADICTS`, `FORESHADOWS`, `PARALLELS`

**特殊功能**:
- 角色关系图可视化
- 时间线视图
- 大纲层级展开
- 写作统计（字数、进度）

---

### 4. 日常记录 (Daily Journal)

**用户画像**: 个人用户、生活记录者、习惯追踪者

**Memory Types**:
| Type | 用途 | 示例 |
|------|------|------|
| `JOURNAL` | 日记 | 今天和朋友去了西湖 |
| `THOUGHT` | 随想/反思 | 关于时间管理的思考 |
| `PLAN` | 计划/目标 | 本周健身计划 |
| `HABIT` | 习惯追踪 | 连续第30天早起 |
| `MOOD` | 情绪记录 | 今天心情不错 |
| `EVENT` | 事件记录 | 参加了小王的婚礼 |
| `DREAM` | 梦境记录 | 梦见在海边飞翔 |
| `GRATITUDE` | 感恩记录 | 感谢妈妈做的晚餐 |

**关系类型**: `FOLLOWS`, `TRIGGERS`, `RELATES`, `RECALLS`

**特殊功能**:
- 日历视图
- 情绪标签/趋势图
- 习惯打卡统计
- 照片/语音附件支持

---

### 5. 企业备忘 (Enterprise)

**用户画像**: 团队、企业用户、项目管理者

**Memory Types**:
| Type | 用途 | 示例 |
|------|------|------|
| `MEETING` | 会议记录 | 2026-02-06 周例会 |
| `ACTION_ITEM` | 待办事项 | @张三 完成API文档 |
| `POLICY` | 政策/规范 | 代码审查流程 |
| `CONTACT` | 联系人信息 | 客户王总的联系方式 |
| `PROJECT` | 项目状态 | Q1 产品路线图 |
| `RISK` | 风险记录 | 供应商交付延迟风险 |
| `KNOWLEDGE` | 知识库 | 如何申请报销 |
| `ANNOUNCEMENT` | 公告 | 春节放假安排 |

**关系类型**: `ASSIGNS`, `BLOCKS`, `DEPENDS`, `ESCALATES`, `SUPERSEDES`

**特殊功能**:
- 多用户/多租户支持
- 权限控制（查看/编辑/删除）
- @提及和通知
- 与飞书/钉钉集成
- 审计日志

---

## CLI 设计

### 已实现命令

```bash
# 初始化新项目（交互式向导）
memosctl init
memosctl init --name my_project --mode coding --password mypass --yes

# 启动/停止服务
memosctl start                    # 启动所有模式
memosctl start --mode coding      # 启动指定模式
memosctl stop                     # 停止所有服务

# 查看状态
memosctl status                   # 显示服务和 MCP 状态

# 学生模式日历视图
memosctl calendar                         # 当前学期笔记
memosctl calendar -s 2026-Spring          # 指定学期
memosctl calendar -c "数学"               # 按课程过滤
memosctl calendar -w 3                    # 第3周笔记
memosctl calendar -v week                 # 周视图
memosctl calendar -v month                # 月度概览

# 查看版本
memosctl version
```

### 命令结构（含规划中）

```bash
# 初始化新项目
memosctl init [--name <cube_name>] [--mode <coding|writing|daily|enterprise>]

# 交互式安装
memosctl init
? 选择使用场景:
  ❯ 🖥️  编码开发 (Coding)
    ✍️  写作创作 (Writing)
    📅  日常记录 (Daily Journal)
    🏢  企业备忘 (Enterprise)

? 项目名称: my_project
? 设置 Neo4j 密码: ********
? 设置 Qdrant API Key (可选，回车跳过):
? 选择 LLM 后端:
  ❯ Ollama (本地，免费)
    OpenAI (云端，需 API Key)
    SiliconFlow (云端，国内可用)

✅ 配置完成！
   - Cube: my_project
   - 模式: 编码开发
   - 配置文件: ~/.memos/my_project/

🚀 启动服务: memosctl start
📖 查看帮助: memosctl --help
```

### 其他命令

```bash
# 启动服务
memosctl start [--port 18000]

# 停止服务
memosctl stop

# 查看状态
memosctl status

# 列出所有 cube
memosctl list

# 切换 cube
memosctl use <cube_name>

# 备份
memosctl backup [--output <path>]

# 恢复
memosctl restore <backup_file>

# 迁移模式（如从日常迁移到写作）
memosctl migrate --from daily --to writing
```

---

## 技术实现

### 技术栈选择

| 方案 | 优点 | 缺点 |
|------|------|------|
| **Python + Typer** | 与现有代码库一致、Rich 美化输出 | 需要 Python 环境 |
| **Node.js + Inquirer** | 交互体验好、可打包二进制 | 技术栈分裂 |
| **Go + Cobra** | 单二进制分发、跨平台 | 需要学习新语言 |
| **Rust + Clap** | 性能好、单二进制 | 开发周期长 |

**推荐**: Python + Typer + Rich（与现有代码库一致）

### 目录结构（实际实现）

```
memos-cli/
├── memosctl/
│   ├── __init__.py           # 版本信息
│   ├── __main__.py           # Entry point
│   ├── cli.py                # Main CLI commands (Typer)
│   ├── config.py             # TOML 配置管理
│   ├── modes.py              # 模式定义 (coding, student, ...)
│   ├── init_wizard.py        # Interactive init wizard
│   ├── service.py            # Start/stop/status 服务管理
│   ├── mcp_launcher.py       # MCP 服务器进程管理
│   ├── generators.py         # SKILL.md/Hook 模板生成
│   ├── calendar_cmd.py       # 学生模式日历视图
│   └── templates/            # Jinja2 模板
│       ├── skill.md.j2
│       └── hook.js.j2
├── tests/
│   ├── test_config.py
│   ├── test_modes.py
│   ├── test_init_wizard.py
│   ├── test_service.py
│   ├── test_mcp_launcher.py
│   ├── test_generators.py
│   └── test_calendar.py
├── pyproject.toml
└── README.md
```

### 配置模板示例

**coding/config.json**:
```json
{
  "mode": "coding",
  "memory_types": [
    "BUGFIX", "ERROR_PATTERN", "DECISION", "CODE_PATTERN",
    "CONFIG", "GOTCHA", "MILESTONE", "FEATURE", "PROGRESS"
  ],
  "relation_types": ["CAUSE", "RELATE", "CONDITION", "CONFLICT"],
  "default_tags": ["coding", "debug", "architecture"],
  "features": {
    "git_integration": true,
    "code_highlight": true,
    "stack_trace_parser": true
  }
}
```

**writing/config.json**:
```json
{
  "mode": "writing",
  "memory_types": [
    "DRAFT", "OUTLINE", "CHARACTER", "PLOT", "SETTING",
    "RESEARCH", "INSPIRATION", "REVISION"
  ],
  "relation_types": ["DEVELOPS", "REFERENCES", "CONTRADICTS", "FORESHADOWS"],
  "default_tags": ["writing", "creative", "fiction"],
  "features": {
    "character_graph": true,
    "timeline_view": true,
    "word_count": true
  }
}
```

---

## 实现路线图

### Phase 1: CLI 框架 ✅ 完成

- [x] 创建 `memos-cli` 项目结构
- [x] 实现 `memosctl init` 交互式向导
- [x] 支持自定义 Neo4j/Qdrant 密码
- [x] 生成 `.env` 文件
- [x] 编码模式 (coding) 和学生模式 (student) 定义
- [x] TOML 配置管理
- [x] SKILL.md 和 Hook 模板生成
- [x] 18 个单元测试通过

**提交**: `90df4df` - feat(cli): complete Phase 1 CLI framework

### Phase 2: MCP 服务器集成 ✅ 完成

- [x] PID 文件管理进程
- [x] 跨平台进程启动 (Windows/Linux)
- [x] 模式专属端口 (coding:18001, student:18002)
- [x] 后台/前台启动支持
- [x] 优雅关闭处理
- [x] 6 个新测试通过

**提交**: `2734d77` - feat(cli): add MCP server launcher for process management

### Phase 3: 学生模式日历视图 ✅ 完成

- [x] `memos_calendar` MCP 工具
- [x] `memosctl calendar` CLI 命令
- [x] 学期/周/日过滤
- [x] list/week/month 三种视图
- [x] 课程过滤功能
- [x] 9 个新测试通过

**提交**: `5713d43` - feat(cli): add student mode calendar view (Phase 3)

### Phase 4: 日常记录模式 (Planned)

- [ ] 设计日常模式的 memory types
- [ ] 创建日常模式配置模板
- [ ] 调整 LLM 提取 prompt
- [ ] 创建日常模式 SKILL.md
- [ ] 日历视图复用

### Phase 5: 写作模式 (Planned)

- [ ] 设计写作模式的 memory types
- [ ] 实现角色关系图功能
- [ ] 实现时间线视图
- [ ] 创建写作模式 SKILL.md
- [ ] 调整 LLM 提取 prompt（适配创作语境）

### Phase 6: 企业模式 (Planned)

- [ ] 设计企业模式的 memory types
- [ ] 实现多用户/权限系统
- [ ] 实现 @提及功能
- [ ] 飞书/钉钉集成
- [ ] 审计日志

### Phase 7: 分发与文档 (Planned)

- [ ] PyPI 发布
- [ ] 可选：打包为独立二进制（PyInstaller）
- [ ] 完善文档和教程
- [ ] 录制演示视频

---

## 风险与挑战

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 不同模式间迁移复杂 | 用户锁定 | 提供 `memosctl migrate` 命令 |
| LLM 提取在非编码场景表现差 | 记忆质量下降 | 针对每种模式调整 prompt |
| 企业模式安全要求高 | 合规风险 | 审计日志、加密存储 |
| 维护多套模板成本高 | 开发效率降低 | 模板继承机制、自动化测试 |

---

## 参考资料

- [Typer 文档](https://typer.tiangolo.com/)
- [Rich 文档](https://rich.readthedocs.io/)
- [beads CLI 实现](https://github.com/steveyegge/beads)

---

## 附录：交互式安装流程示意

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   __  __                  ___  ____                             │
│  |  \/  | ___ _ __ ___   / _ \/ ___|                            │
│  | |\/| |/ _ \ '_ ` _ \ | | | \___ \                            │
│  | |  | |  __/ | | | | || |_| |___) |                           │
│  |_|  |_|\___|_| |_| |_| \___/|____/                            │
│                                                                 │
│  Welcome to MemOS Setup Wizard!                                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ? 选择使用场景 (Use arrow keys)                                 │
│                                                                 │
│    ❯ 🖥️  编码开发 (coding)                                      │
│         适合程序员、AI助手用户 · Port 18001                      │
│         Memory Types: BUGFIX, ERROR_PATTERN, DECISION...        │
│                                                                 │
│      📚  学生学习 (student) ✓ 已实现                             │
│         适合学生、课程学习者 · Port 18002                        │
│         Memory Types: NOTE, CONCEPT, FORMULA...                 │
│         特色: 日历视图 (memosctl calendar)                       │
│                                                                 │
│      ✍️  写作创作 (writing) ○ 规划中                             │
│         适合小说作者、博客写手                                    │
│         Memory Types: DRAFT, OUTLINE, CHARACTER...              │
│                                                                 │
│      📅  日常记录 (daily) ○ 规划中                               │
│         适合个人日记、习惯追踪                                    │
│         Memory Types: JOURNAL, THOUGHT, PLAN...                 │
│                                                                 │
│      🏢  企业备忘 (enterprise) ○ 规划中                          │
│         适合团队协作、项目管理                                    │
│         Memory Types: MEETING, ACTION_ITEM, POLICY...           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ? 项目名称: my_study                                            │
│                                                                 │
│  ? 设置 Neo4j 密码: ••••••••                                    │
│    (至少8位，包含字母和数字)                                      │
│                                                                 │
│  ? 选择 LLM 后端:                                                │
│    ❯ Ollama (本地运行，免费，推荐)                               │
│      OpenAI (需要 API Key)                                      │
│      SiliconFlow (国内可用)                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✅ 配置完成！                                                   │
│                                                                 │
│  📁 配置文件: ~/.memos/my_study/                                 │
│  🧊 Cube ID:   my_study_cube                                    │
│  📝 模式:      学生学习                                          │
│                                                                 │
│  🚀 下一步:                                                      │
│     1. 启动服务:  memosctl start                                 │
│     2. 查看日历:  memosctl calendar                              │
│     3. 配置 MCP:  见 ~/.memos/my_study/MCP_GUIDE.md             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
