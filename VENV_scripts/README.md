# MemOS Unified Venv Setup

This folder provides standardized scripts to create a single Python virtual environment that works for both the MemOS core project and `memos-cli`.

## Why Venv?

- **Simpler**: No need to install Conda/Miniconda
- **Portable**: Works with any Python 3.10+ installation
- **Consistent**: Same environment across dev/prod
- **Lighter**: No conda overhead

## Requirements

- Python 3.10+ (with `pip` and `venv` module)
- No Conda required

## Quick Start

### Windows (cmd)

```bat
VENV_scripts\setup_venv.bat
```

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File VENV_scripts/setup_venv.ps1
```

### macOS/Linux

```bash
bash VENV_scripts/setup_venv.sh
```

## Options

| Option | Windows (bat) | PowerShell | Bash |
|--------|---------------|------------|------|
| Install all extras | `set INSTALL_ALL=true` | `-InstallAll` | `INSTALL_ALL=true` |
| Clean rebuild | `set CLEAN=true` | `-Clean` | `CLEAN=true` |
| Custom Python | `set PYTHON_BIN=py -3.11` | `-Python "py -3.11"` | `PYTHON_BIN=python3.11` |

### Examples

```bash
# Install with all optional dependencies
INSTALL_ALL=true bash VENV_scripts/setup_venv.sh

# Clean rebuild with Python 3.11
CLEAN=true PYTHON_BIN=python3.11 bash VENV_scripts/setup_venv.sh

# PowerShell with all options
powershell -ExecutionPolicy Bypass -File VENV_scripts/setup_venv.ps1 -InstallAll -Clean
```

## Activate Later

After setup, activate the venv to use MemOS:

```bash
# Windows (cmd)
.\.venv\Scripts\activate.bat

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

## What Gets Installed

1. **Main project** (`pip install -e .`):
   - Core: `memos` package
   - Default extras: `tree-mem`, `mcp-server`
   - All extras (if `-InstallAll`): includes torch, sentence-transformers, etc.

2. **memos-cli** (`pip install -e memos-cli`):
   - CLI tool: `memosctl`

## Migrating from Conda

If you previously used `conda_venv`:

1. Run the setup script to create `.venv`
2. The `start.bat` script auto-detects `.venv` (preferred) or `conda_venv` (fallback)
3. Once `.venv` works, you can safely delete `conda_venv`

## Directory Structure

```
MemOS/
├── .venv/                    # Created by setup scripts
│   ├── Scripts/ (Windows)    # python.exe, activate.bat, pip.exe
│   └── bin/ (Linux/macOS)    # python, activate, pip
├── VENV_scripts/
│   ├── setup_venv.bat        # Windows cmd
│   ├── setup_venv.ps1        # Windows PowerShell
│   ├── setup_venv.sh         # Linux/macOS
│   └── README.md             # This file
└── conda_venv/               # Legacy (can be removed)
```

## Troubleshooting

### "py is not recognized"

Windows: Install Python from [python.org](https://www.python.org/downloads/) and ensure "Add to PATH" is checked.

### "Permission denied" on PowerShell

Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### "Module not found" after activation

Ensure you're in the project root and the venv is activated:

```bash
cd /path/to/MemOS
source .venv/bin/activate  # or .\.venv\Scripts\activate.bat on Windows
pip list | grep memos
```
