# Scripts Directory

This directory contains startup and utility scripts for MemOS.

## Structure

```
scripts/
├── templates/           # Template scripts (tracked by git)
│   ├── start_template.bat
│   └── start_template.ps1
├── local/               # Your local scripts (ignored by git)
│   └── README.md
└── README.md
```

## Quick Start

### For New Users

1. Copy a template to `local/`:
   ```cmd
   copy scripts\templates\start_template.bat scripts\local\start.bat
   ```

2. Edit `scripts/local/start.bat` and update paths:
   - `NEO4J_HOME` - Your Neo4j installation
   - `QDRANT_HOME` - Your Qdrant installation

3. Run:
   ```cmd
   scripts\local\start.bat
   ```

### Templates vs Local

| Folder | Git Status | Purpose |
|--------|------------|---------|
| `templates/` | Tracked | Reference scripts with placeholder paths |
| `local/` | Ignored | Your customized scripts with real paths |

## Why This Structure?

- **Templates** provide working examples that anyone can use as starting points
- **Local scripts** contain machine-specific paths that won't work elsewhere
- This keeps the repository clean while still providing useful tools
