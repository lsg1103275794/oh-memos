# MemOS CLI (memosctl)

Command-line tool for MemOS - Multi-mode Memory Management for AI assistants.

## Installation

```bash
pip install memos-cli
```

Or install from source:

```bash
cd memos-cli
pip install -e .
```

## Quick Start

### Initialize a new project

```bash
# Interactive wizard
memosctl init

# Non-interactive with options
memosctl init --name my_project --mode coding --password myneo4jpass --yes
```

### Manage services

```bash
# Check status
memosctl status

# Start services
memosctl start

# Start specific mode
memosctl start --mode student

# Stop services
memosctl stop
```

## Available Modes

| Mode | Description | Port |
|------|-------------|------|
| 🖥️ coding | For programmers and AI assistants | 18001 |
| 📚 student | For course notes and academic work | 18002 |
| 📅 daily | For personal journaling (coming soon) | 18003 |
| ✍️ writing | For creative writing (coming soon) | 18004 |

## Configuration

Configuration is stored in `~/.memos/config.toml`:

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

When you run `memosctl init`, the following files are created:

```
~/.memos/<project>/
├── config.toml           # CLI configuration
├── .env                  # MCP server environment
├── cubes/
│   └── <project>_cube/
│       └── config.json   # Cube configuration
└── .claude/
    ├── skills/
    │   └── <mode>-memory/
    │       └── SKILL.md  # AI behavior rules
    └── hooks/
        └── node/
            └── memos_<mode>_hook.js
```

## License

Apache-2.0
