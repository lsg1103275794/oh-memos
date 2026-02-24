#!/usr/bin/env python3
"""MemOS CLI Init Wizard - Interactive initialization for new projects."""

import json
import re
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .config import DEFAULT_CONFIG_DIR, MemosConfig, save_config
from .modes import get_all_modes, get_mode

console = Console()

LOGO = r"""
  __  __                  ___  ____
 |  \/  | ___ _ __ ___   / _ \/ ___|
 | |\/| |/ _ \ '_ ` _ \ | | | \___ \
 | |  | |  __/ | | | | || |_| |___) |
 |_|  |_|\___|_| |_| |_| \___/|____/
"""


class ProjectNameError(Exception):
    """Raised when project name is invalid."""
    pass


def validate_project_name(name: str) -> str:
    """Validate and normalize project name."""
    if not name or not name.strip():
        raise ProjectNameError("Project name cannot be empty")
    
    # Reject names with spaces
    if " " in name:
        raise ProjectNameError(
            f"Invalid project name '{name}'. "
            "Must not contain spaces."
        )
    
    normalized = name.lower().strip()
    normalized = re.sub(r"[-.\s]+", "_", normalized)
    
    if not re.match(r"^[a-z][a-z0-9_]*$", normalized):
        raise ProjectNameError(
            f"Invalid project name '{name}'. "
            "Must start with a letter, contain only letters, numbers, and underscores."
        )
    return normalized


def generate_cube_config(
    cube_id: str,
    mode: str,
    neo4j_password: str,
    neo4j_uri: str = "bolt://localhost:7687",
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
    llm_backend: str = "ollama",
    llm_api_base: str = "http://localhost:11434/v1",
) -> dict[str, Any]:
    """Generate cube config.json content."""
    mode_obj = get_mode(mode)
    
    config = {
        "model_schema": "memos.configs.mem_cube.GeneralMemCubeConfig",
        "user_id": cube_id,
        "cube_id": cube_id,
        "config_filename": "config.json",
        "text_mem": {
            "backend": "tree_text",
            "config": {
                "cube_id": cube_id,
                "memory_filename": "textual_memory.json",
                "reorganize": True,
                "extractor_llm": {
                    "backend": "openai",
                    "config": {
                        "model_name_or_path": "qwen2.5:7b" if llm_backend == "ollama" else "LongCat-Flash-Lite",
                        "temperature": 0.6,
                        "max_tokens": 6000,
                        "api_key": "ollama" if llm_backend == "ollama" else "placeholder",
                        "api_base": llm_api_base,
                    },
                },
                "dispatcher_llm": {
                    "backend": "openai",
                    "config": {
                        "model_name_or_path": "qwen2.5:7b" if llm_backend == "ollama" else "LongCat-Flash-Lite",
                        "temperature": 0.6,
                        "max_tokens": 6000,
                        "api_key": "ollama" if llm_backend == "ollama" else "placeholder",
                        "api_base": llm_api_base,
                    },
                },
                "embedder": {
                    "backend": "universal_api",
                    "config": {
                        "model_name_or_path": "BAAI/bge-m3",
                        "provider": "openai",
                        "base_url": llm_api_base,
                        "api_key": "ollama" if llm_backend == "ollama" else "placeholder",
                        "embedding_dims": 1024,
                    },
                },
                "reranker": {
                    "backend": "http_bge",
                    "config": {
                        "url": "https://api.siliconflow.cn/v1/rerank",
                        "model": "netease-youdao/bce-reranker-base_v1",
                        "headers_extra": "{}",
                    },
                },
                "graph_db": {
                    "backend": "neo4j-community",
                    "config": {
                        "uri": neo4j_uri,
                        "user": "neo4j",
                        "password": neo4j_password,
                        "db_name": "neo4j",
                        "use_multi_db": False,
                        "user_name": cube_id,
                        "embedding_dimension": 1024,
                        "vec_config": {
                            "backend": "qdrant",
                            "config": {
                                "collection_name": f"{cube_id}_graph",
                                "vector_dimension": 1024,
                                "distance_metric": "cosine",
                                "host": qdrant_host,
                                "port": qdrant_port,
                            },
                        },
                    },
                },
                "search_strategy": {"bm25": True, "cot": False},
            },
        },
        "act_mem": {},
        "para_mem": {},
    }
    
    overrides = mode_obj.get_cube_config_overrides()
    if overrides:
        config["mode_config"] = overrides
    
    return config


def generate_env_file(
    output_path: Path,
    neo4j_password: str,
    cube_id: str,
    cubes_dir: str,
    api_url: str = "http://localhost:18000",
) -> None:
    """Generate .env file for MCP server."""
    content = f"""# MemOS MCP Server Configuration
# Generated by memosctl init

MEMOS_URL={api_url}
MEMOS_USER={cube_id}
MEMOS_DEFAULT_CUBE={cube_id}
MEMOS_CUBES_DIR={cubes_dir}

NEO4J_HTTP_URL=http://localhost:7474
NEO4J_USER=neo4j
NEO4J_PASSWORD={neo4j_password}

MEMOS_TIMEOUT_TOOL=120
MEMOS_TIMEOUT_STARTUP=30
MEMOS_ENABLE_DELETE=false
MEMOS_LOG_LEVEL=WARNING
"""
    output_path.write_text(content)


def show_welcome():
    """Display welcome message with logo."""
    console.print(Panel(LOGO, title="Welcome to MemOS Setup Wizard!", border_style="blue"))


def select_mode() -> str:
    """Interactive mode selection."""
    console.print("\n[bold]? 选择使用场景:[/bold]\n")
    
    modes = get_all_modes()
    table = Table(show_header=False, box=None, padding=(0, 2))
    
    for i, mode in enumerate(modes, 1):
        table.add_row(f"[bold cyan]{i}[/bold cyan]", f"{mode.emoji}  {mode.display_name}", f"[dim]{mode.description}[/dim]")
    
    console.print(table)
    console.print()
    
    while True:
        choice = Prompt.ask("选择 (输入数字)", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(modes):
                return modes[idx].name
        except ValueError:
            pass
        console.print("[red]无效选择，请重试[/red]")


def run_init_wizard(
    project_name: str | None = None,
    mode: str | None = None,
    neo4j_password: str | None = None,
    output_dir: Path | None = None,
    non_interactive: bool = False,
) -> dict[str, Any]:
    """Run the interactive init wizard."""
    if not non_interactive:
        show_welcome()
    
    # 1. Get project name
    if not project_name:
        if non_interactive:
            project_name = "my_project"
        else:
            while True:
                project_name = Prompt.ask("? 项目名称", default="my_project")
                try:
                    project_name = validate_project_name(project_name)
                    break
                except ProjectNameError as e:
                    console.print(f"[red]{e}[/red]")
    else:
        project_name = validate_project_name(project_name)
    
    cube_id = f"{project_name}_cube"
    
    # 2. Select mode
    if not mode:
        mode = "coding" if non_interactive else select_mode()
    
    mode_obj = get_mode(mode)
    
    # 3. Get Neo4j password
    if not neo4j_password:
        neo4j_password = "12345678" if non_interactive else Prompt.ask("? Neo4j 密码", password=True, default="12345678")
    
    # 4. Select LLM backend
    if non_interactive:
        llm_backend = "ollama"
    else:
        console.print("\n[bold]? 选择 LLM 后端:[/bold]")
        console.print("  [cyan]1[/cyan]  Ollama (本地运行，免费，推荐)")
        console.print("  [cyan]2[/cyan]  OpenAI (需要 API Key)")
        console.print("  [cyan]3[/cyan]  SiliconFlow (国内可用)")
        llm_choice = Prompt.ask("选择", default="1")
        llm_backend = {"1": "ollama", "2": "openai", "3": "siliconflow"}.get(llm_choice, "ollama")
    
    # 5. Create directories and files
    project_dir = output_dir or (DEFAULT_CONFIG_DIR / project_name)
    cubes_dir = project_dir / "cubes"
    cube_dir = cubes_dir / cube_id
    
    project_dir.mkdir(parents=True, exist_ok=True)
    cube_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate cube config
    cube_config = generate_cube_config(cube_id=cube_id, mode=mode, neo4j_password=neo4j_password, llm_backend=llm_backend)
    config_path = cube_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(cube_config, f, indent=2)
    
    # Generate .env file
    env_path = project_dir / ".env"
    generate_env_file(output_path=env_path, neo4j_password=neo4j_password, cube_id=cube_id, cubes_dir=str(cubes_dir))
    
    # Save global config
    global_config = MemosConfig(neo4j_password=neo4j_password, default_mode=mode, active_modes=[mode], cubes_dir=str(cubes_dir))
    save_config(global_config, project_dir / "config.toml")
    
    # Generate Claude Code files (skills, hooks)
    from .generators import generate_claude_files
    claude_files = generate_claude_files(mode=mode, cube_id=cube_id, project_dir=project_dir)
    
    # 6. Show completion message
    if not non_interactive:
        console.print()
        console.print(Panel(
            f"""[green]✅ 配置完成！[/green]

📁 配置目录: [cyan]{project_dir}[/cyan]
🧊 Cube ID:   [cyan]{cube_id}[/cyan]
📝 模式:      [cyan]{mode_obj.emoji} {mode_obj.display_name}[/cyan]

📄 生成的文件:
   - Cube Config: {config_path}
   - .env: {env_path}
   - SKILL.md: {claude_files.get('skill', 'N/A')}
   - Hook: {claude_files.get('hook', 'N/A')}

🚀 下一步:
   1. 启动服务:  [bold]memosctl start[/bold]
   2. 查看状态:  [bold]memosctl status[/bold]
""",
            title="Setup Complete",
            border_style="green",
        ))
    
    return {
        "project_name": project_name,
        "cube_id": cube_id,
        "mode": mode,
        "project_dir": str(project_dir),
        "cube_dir": str(cube_dir),
        "config_path": str(config_path),
        "env_path": str(env_path),
        "claude_files": {k: str(v) for k, v in claude_files.items()},
    }
