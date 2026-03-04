# oh-memos CLI (oh-memosctl)

Command-line tool for oh-memos - Multi-mode Memory Management for AI assistants.

## Installation

```bash
pip install oh-memos-cli
```

Or install from source:

```bash
cd oh-memos-cli
pip install -e .
```

## Quick Start

### Initialize a new project

```bash
# Interactive wizard
oh-memosctl init

# Non-interactive with options
oh-memosctl init --name my_project --mode coding --password myneo4jpass --yes
```

### Manage services

```bash
# Check status
oh-memosctl status

# Start services
oh-memosctl start

# Start specific mode
oh-memosctl start --mode student

# Stop services
oh-memosctl stop
```

## Available Modes

| Mode | Description | Port |
|------|-------------|------|
| 🖥�?coding | For programmers and AI assistants | 18001 |
| 📚 student | For course notes and academic work | 18002 |
| 📅 daily | For personal journaling (coming soon) | 18003 |
| ✍️ writing | For creative writing (coming soon) | 18004 |

## Configuration

Configuration is stored in `~/.oh-memos/config.toml`:

```toml
[api]
url = "http://localhost:18000"
timeout = 30.0

[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
password = "your-password"

[qdrant]
host = "localhost"
port = 6333

[modes]
default = "coding"
active = ["coding"]
```

## Generated Files

When you run `oh-memosctl init`, the following files are created:

```
~/.oh-memos/<project>/
├── config.toml           # CLI configuration
├── .env                  # MCP server environment
├── cubes/
�?  └── <project>_cube/
�?      └── config.json   # Cube configuration
└── .claude/
    ├── skills/
    �?  └── <mode>-memory/
    �?      └── SKILL.md  # AI behavior rules
    └── hooks/
        └── node/
            └── oh-memos_<mode>_hook.js
```

## License

Apache-2.0
