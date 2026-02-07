# MemOS Windows 环境部署指南

> 使用 Python venv 统一管理后端环境

---

## 前置要求

### 1. 安装 Python 3.10+

从官网下载安装：https://www.python.org/downloads/

**安装时注意**：
- ✅ 勾选 "Add Python to PATH"
- ✅ 勾选 "Install py launcher"

验证安装：

```bat
py --list
:: 应显示类似: -3.12-64 *
```

### 2. 安装数据库服务

| 服务 | 下载地址 | 默认端口 |
|------|----------|----------|
| Neo4j Community | https://neo4j.com/download/ | 7474/7687 |
| Qdrant | https://qdrant.tech/documentation/quick-start/ | 6333 |
| Ollama | https://ollama.com/download | 11434 |

---

## 快速部署

### 步骤 1：创建 venv 环境

```bat
cd G:\test\MemOS

:: 使用 Python 3.12 创建 venv
py -3.12 -m venv .venv

:: 激活环境
.venv\Scripts\activate.bat

:: 升级 pip
python -m pip install --upgrade pip
```

### 步骤 2：安装依赖

**最小安装**（MCP Server + 知识图谱）：

```bat
pip install -e ".[tree-mem,mcp-server]"
pip install -e memos-cli
```

**完整安装**（所有功能）：

```bat
pip install -e ".[all]"
pip install -e memos-cli
```

### 步骤 3：配置环境变量

复制 `.env.example` 为 `.env` 并编辑：

```bat
copy .env.example .env
notepad .env
```

关键配置项：

```ini
# Neo4j 数据库
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Qdrant 向量数据库
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Ollama LLM
OLLAMA_HOST=http://localhost:11434
```

### 步骤 4：配置启动脚本

```bat
:: 复制模板
copy scripts\templates\start_template.bat scripts\local\start.bat

:: 编辑数据库路径
notepad scripts\local\start.bat
```

修改以下路径为你的实际安装位置：

```bat
set "NEO4J_HOME=D:\Your\Path\neo4j-community-5.x.x"
set "QDRANT_HOME=D:\Your\Path\Qdrant"
```

### 步骤 5：启动服务

```bat
scripts\local\start.bat
```

---

## 验证安装

### 检查 CLI

```bat
.venv\Scripts\activate.bat
python -m memosctl.cli --help
python -m memosctl.cli status
```

### 检查 API

浏览器访问：
- API 文档：http://localhost:18000/docs
- Qdrant 控制台：http://localhost:6333/dashboard
- Neo4j 浏览器：http://localhost:7474

---

## 常见问题

### Q: `py -3.12` 找不到

**A**: 检查 Python 安装时是否勾选了 "Install py launcher"。或者直接使用完整路径：

```bat
C:\Users\你的用户名\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv
```

### Q: `.venv\Scripts\activate.bat` 找不到

**A**: 可能创建了 Linux 格式的 venv（有 `bin` 而不是 `Scripts`）。删除重建：

```bat
rmdir /s /q .venv
py -3.12 -m venv .venv
dir .venv\Scripts  :: 确认有 activate.bat
```

### Q: PowerShell 执行策略限制

**A**: 运行以下命令允许脚本执行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: 缺少模块 (ImportError)

**A**: 安装缺失的依赖：

```bat
:: 单个模块
pip install chonkie

:: 或安装所有依赖
pip install -e ".[all]"
```

### Q: SOCKS 代理错误

**A**: 安装 httpx socks 支持：

```bat
pip install httpx[socks]
```

### Q: Neo4j 连接失败

**A**:
1. 确认 Neo4j 已启动：`netstat -ano | findstr 7687`
2. 检查密码是否正确
3. 首次使用需在 Neo4j Browser (http://localhost:7474) 修改默认密码

---

## 目录结构

```
MemOS/
├── .venv/                    # Python 虚拟环境
│   └── Scripts/
│       ├── activate.bat      # 激活脚本
│       └── python.exe        # Python 解释器
├── .env                      # 环境变量配置
├── scripts/
│   ├── local/
│   │   └── start.bat         # 启动脚本（本地配置）
│   └── templates/
│       └── start_template.bat # 启动脚本模板
├── src/memos/                # 核心代码
├── memos-cli/                # CLI 工具
├── mcp-server/               # MCP 服务器
└── VENV_scripts/             # venv 安装脚本
```

---

## 日常使用

### 激活环境

每次打开新终端后：

```bat
cd G:\test\MemOS
.venv\Scripts\activate.bat
```

提示符会变成 `(.venv) G:\test\MemOS>`

### 启动服务

```bat
scripts\local\start.bat
```

### 停止服务

按 `Ctrl+C` 停止 API，然后选择是否停止数据库。

### 更新依赖

```bat
.venv\Scripts\activate.bat
pip install -e ".[all]" --upgrade
```

---

## 附录：手动安装脚本

如果自动脚本失败，可以手动执行：

```bat
@echo off
cd /d G:\test\MemOS

echo [1/5] Creating venv...
py -3.12 -m venv .venv

echo [2/5] Activating...
call .venv\Scripts\activate.bat

echo [3/5] Upgrading pip...
python -m pip install --upgrade pip

echo [4/5] Installing MemOS...
pip install -e ".[all]"

echo [5/5] Installing CLI...
pip install -e memos-cli

echo Done!
python -m memosctl.cli version
```

---

## 附录：IDE 自动激活 venv

### VS Code

复制配置模板：

```bat
:: 创建 .vscode 目录
mkdir .vscode

:: 复制配置（重命名为 settings.json）
copy VENV_scripts\IDE_CONFIG .vscode\settings.json
```

配置效果：
- ✅ 打开项目时自动识别 `.venv` 解释器
- ✅ 新建终端自动激活 venv（显示 `(.venv)` 前缀）
- ✅ 运行/调试 Python 文件使用 venv 环境

### PyCharm

1. `File` → `Settings` → `Project` → `Python Interpreter`
2. 点击齿轮 → `Add` → `Existing environment`
3. 选择 `.venv\Scripts\python.exe`

### 拷贝到新电脑

1. 复制整个项目文件夹（**不含** `.venv` 目录）
2. 运行 `VENV_scripts\setup_venv.bat` 创建新的 venv
3. 复制 VS Code 配置：`copy VENV_scripts\IDE_CONFIG .vscode\settings.json`
4. 打开 IDE，自动识别环境

---

*文档更新：2026-02-08*
