# MemOS 数据库迁移工具

一键备份和恢复 MemOS 数据库，用于迁移到其他电脑。

## 备份内容

| 组件 | 备份内容 | 说明 |
|------|----------|------|
| Neo4j | `data/` 目录 | 知识图谱数据 |
| Qdrant | `storage/` 目录 | 向量数据库 |
| 配置 | `.env`, `memos_cubes/` | 环境变量和 Cube 配置 |
| 用户配置 | `~/.memos/` | MCP 用户配置 |

## 使用方法

### 备份（在旧电脑上）

```bat
:: 1. 停止所有服务
scripts\local\stop_db_silent.bat

:: 2. 运行备份
scripts\migrate\backup.bat
```

备份文件保存在 `backups/memos_backup_YYYYMMDD_HHMM.zip`

### 恢复（在新电脑上）

```bat
:: 1. 安装必要软件
::    - Python 3.10+
::    - Neo4j Community
::    - Qdrant
::    - Ollama

:: 2. 克隆/复制 MemOS 项目

:: 3. 创建 venv 环境
VENV_scripts\setup_venv.bat

:: 4. 复制备份文件到 backups 目录

:: 5. 确保 Neo4j 和 Qdrant 已停止

:: 6. 运行恢复
scripts\migrate\restore.bat backups\memos_backup_YYYYMMDD_HHMM.zip

:: 7. 编辑 .env 更新路径（如果数据库安装位置不同）
notepad .env

:: 8. 编辑启动脚本更新数据库路径
notepad scripts\local\start.bat

:: 9. 启动服务
scripts\local\start.bat
```

## 配置路径

在 `backup.bat` 和 `restore.bat` 中修改这些路径：

```bat
set "NEO4J_HOME=D:\User\neo4j-community-5.15.0"
set "QDRANT_HOME=D:\User\Qdrant"
```

## 注意事项

1. **备份前停止服务**：确保 Neo4j 和 Qdrant 已停止，否则可能备份不完整

2. **版本兼容性**：
   - Neo4j 版本应该相同或兼容
   - Qdrant 版本应该相同或兼容

3. **路径差异**：新电脑上的数据库安装路径可能不同，恢复后需要更新 `.env` 和启动脚本

4. **密码**：Neo4j 密码保存在数据中，恢复后使用原密码

5. **旧数据保留**：恢复时会将现有数据重命名为 `*_old`，可手动删除

## 手动迁移

如果自动脚本不适用，可以手动复制：

### Neo4j
```bat
:: 备份
xcopy /E /I "D:\Neo4j\data" "backup\neo4j_data"

:: 恢复
xcopy /E /I "backup\neo4j_data" "D:\Neo4j\data"
```

### Qdrant
```bat
:: 备份
xcopy /E /I "D:\Qdrant\storage" "backup\qdrant_storage"

:: 恢复
xcopy /E /I "backup\qdrant_storage" "D:\Qdrant\storage"
```

### 配置文件
```bat
:: 备份
copy .env backup\.env
xcopy /E /I data\memos_cubes backup\memos_cubes

:: 恢复
copy backup\.env .env
xcopy /E /I backup\memos_cubes data\memos_cubes

:: 覆盖本地数据库
scripts\migrate\backup.bat                                                                                              :: 把 backups\memos_backup_xxx.zip 拷到 U盘/网盘  

然后在新电脑上运行恢复脚本
scripts\migrate\restore.bat backups\memos_backup_xxx.zip

```

---

*文档更新：2026-02-08*
