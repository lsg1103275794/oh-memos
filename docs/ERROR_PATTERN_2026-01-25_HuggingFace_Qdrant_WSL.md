# [ERROR_PATTERN] HuggingFace Clone & Qdrant Config Bugs

**Project:** MemOS
**Date:** 2026-01-25
**Type:** ERROR_PATTERN

---

## Error Signature

| Field | Value |
|-------|-------|
| Type | HuggingFace Clone Error / Qdrant Connection Error |
| Message | `subprocess.CalledProcessError: git clone https://huggingface.co/datasets/DDSP-SVC-6.3 failed` |
| Context | Registering a memory cube via `/mem_cubes` API |

## Environment

- **OS:** Windows 10/11 with WSL
- **Python:** 3.11
- **Setup:** MemOS API running on Windows, Claude Code running in WSL

---

## Root Cause

### Bug 1: Invalid HuggingFace Clone

**旧代码逻辑 (core.py, product.py):**
```python
if os.path.exists(mem_cube_name_or_path):
    load_from_local()
else:
    # 盲目尝试 HuggingFace 克隆！
    init_from_remote_repo(mem_cube_name_or_path)
```

**问题:** 任何不存在的路径都会被拼接成 `https://huggingface.co/datasets/{path}` 并尝试 git clone。

**示例:**
- 输入: `DDSP-SVC-6.3`
- 错误行为: 尝试 `git clone https://huggingface.co/datasets/DDSP-SVC-6.3`

### Bug 2: WSL 路径无法识别

| 问题路径 | 原因 |
|----------|------|
| `/home/xigou/.memos_cubes/` | Windows 上 `os.path.exists()` 返回 False |
| `/mnt/g/test/` | 需要转换为 `G:/test/` 才能被 Windows 识别 |

### Bug 3: Qdrant 配置优先级

**.env 配置冲突:**
```env
QDRANT_HOST=localhost     # ← 本地配置
QDRANT_PORT=6333          # ← 本地配置
QDRANT_URL=https://...    # ← 云配置
```

**config.py 默认行为:**
```python
"host": os.getenv("QDRANT_HOST", "localhost")  # 总是默认 localhost
```

---

## Solution

### Fix 1: 验证 HuggingFace 仓库格式

**新增函数 `is_valid_huggingface_repo()` (utils.py):**
```python
def is_valid_huggingface_repo(name: str) -> bool:
    # 必须是 username/repo-name 格式
    if name.count('/') != 1:
        return False
    # 不能是路径格式
    if name.startswith('/') or ':' in name:
        return False
    # 验证用户名和仓库名格式
    ...
    return True
```

**测试结果:**
```
DDSP-SVC-6.3 is HF repo: False    ← 不再触发 git clone
user/repo is HF repo: True         ← 有效格式
/mnt/g/test looks like path: True
```

### Fix 2: 跨平台路径处理

**新增函数 `normalize_path()` (utils.py):**

| 输入 | 输出 |
|------|------|
| `/mnt/g/test/` | `G:\test\` (WSL → Windows) |
| `/home/user/...` | `\\wsl$\Ubuntu\home\user\...` (UNC) |
| `C:\Users\...` | `/mnt/c/Users/...` (Windows → WSL) |

### Fix 3: Qdrant 配置智能优先级

**修改 config.py:**
```python
# 旧逻辑
"host": os.getenv("QDRANT_HOST", "localhost")

# 新逻辑: 如果有云 URL，不设置 host/port
"host": None if os.getenv("QDRANT_URL") else os.getenv("QDRANT_HOST", "localhost")
```

---

## Files Modified

| 文件 | 修改内容 |
|------|----------|
| `src/memos/mem_cube/utils.py` | 新增 `is_valid_huggingface_repo()`, `normalize_path()`, `looks_like_local_path()` |
| `src/memos/mem_os/core.py` | 改进 `register_mem_cube()` 逻辑，增加 WSL 路径提示 |
| `src/memos/mem_os/product.py` | 同步更新注册逻辑 |
| `src/memos/api/config.py` | 修复 Qdrant 配置优先级 |
| `.env` | 注释掉 `QDRANT_HOST` 和 `QDRANT_PORT` |

---

## Verification

```bash
# 1. 测试路径验证
python3 -c "
from src.memos.mem_cube.utils import is_valid_huggingface_repo, looks_like_local_path
print(f'DDSP-SVC-6.3 is HF repo: {is_valid_huggingface_repo(\"DDSP-SVC-6.3\")}')
print(f'user/repo is HF repo: {is_valid_huggingface_repo(\"user/repo\")}')
print(f'/mnt/g/test looks like path: {looks_like_local_path(\"/mnt/g/test\")}')
"

# 2. 测试 Qdrant 云连接
curl -s "https://your-qdrant-url:6333/collections" -H "api-key: YOUR_KEY"
```

---

## Prevention

1. **云数据库配置:** 使用 `QDRANT_URL` 时，注释掉 `QDRANT_HOST` 和 `QDRANT_PORT`
2. **WSL → Windows API:** 使用 `/mnt/X/...` 格式路径
3. **Cube 名称:** 使用完整路径，不要使用简单字符串如 `my-project`

---

## Tags

`error`, `bugfix`, `huggingface`, `qdrant`, `wsl`, `path`, `cross-platform`, `config`, `cube-registration`
