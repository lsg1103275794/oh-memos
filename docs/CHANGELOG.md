# Changelog

All notable changes to the MemOS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Cube ID resolution and caching** (`.claude/skills/project-memory/scripts/memos_utils.py`)
  - `resolve_cube_id()` - Maps project names to full cube paths
  - `load_cube_cache()`, `save_cube_cache()`, `update_cube_cache()` - Persistent cache management
  - `get_registered_cubes()` - Query API for all registered cubes
  - Cache stored at `~/.memos_cube_cache.json`

- **Comprehensive troubleshooting guide** (`.claude/skills/project-memory/SKILL.md`)
  - Cube ID format issues
  - WSL path recognition problems
  - API connection errors
  - HuggingFace clone errors
  - Qdrant connection priority
  - Debug mode instructions

- **Cross-platform path utilities** (`src/memos/mem_cube/utils.py`)
  - `is_valid_huggingface_repo()` - Validates HuggingFace repository name format
  - `normalize_path()` - Normalizes paths across Windows/Linux/WSL
  - `path_exists()` - Cross-platform path existence check
  - `looks_like_local_path()` - Detects if string looks like a file path
  - `get_wsl_distro_name()` - Detects current WSL distribution name

- **WSL to Windows UNC path conversion**
  - `/home/user/...` paths now convert to `\\wsl$\Ubuntu\home\user\...` on Windows
  - Automatically tries common distro names (Ubuntu-24.04, Ubuntu-22.04, etc.)

- **Enhanced error messages** for cube registration failures
  - Clear distinction between local path errors and HuggingFace repo errors
  - Specific guidance for WSL path issues when running MemOS on Windows
  - Helpful suggestions for resolving common issues

- **Error pattern documentation** (`docs/ERROR_PATTERN_2026-01-25_HuggingFace_Qdrant_WSL.md`)
  - Detailed bug analysis and solutions for future reference

### Known Issues (To Fix)

- **Cube ID format inconsistency**: After registration, `mem_cube_id` must be the full path used during registration (e.g., `G:/test/MemOS/data/memos_cubes/dev_cube`) rather than just the cube name (`dev_cube`)
- **Workaround**: Use the full path when calling `/memories` endpoint

### Changed

- **Improved project-memory skill scripts** (`.claude/skills/project-memory/scripts/`)
  - `memos_save.py`: Now auto-resolves cube names to full paths before API calls
  - `memos_search.py`: Now auto-resolves cube names to full paths before API calls
  - `memos_init_project.py`: Caches cube ID mapping after successful registration
  - All scripts now provide better error messages and hints

- **Improved cube registration logic** (`core.py`, `product.py`)
  - No longer incorrectly treats local paths as HuggingFace repository names
  - WSL paths (`/mnt/c/...`) now properly converted to Windows paths when needed
  - Windows paths (`C:\...`) now properly converted to WSL paths when needed

### Fixed

- **Critical Bug**: Cube registration no longer attempts `git clone` for invalid inputs
  - Previously: Any non-existent path would trigger a HuggingFace clone attempt
  - Now: Only valid `username/repo-name` format triggers remote clone
  - Example: `DDSP-SVC-6.3` no longer becomes `https://huggingface.co/datasets/DDSP-SVC-6.3`

- **WSL Path Handling**: Fixed path recognition in WSL environment
  - `/mnt/g/test/project` now correctly detected as local path on Windows
  - Automatic path format conversion between WSL and Windows

- **Qdrant Cloud Priority Bug**: Fixed config loading when both local and cloud settings exist
  - Previously: `QDRANT_HOST=localhost` would override `QDRANT_URL` in some code paths
  - Now: If `QDRANT_URL` is set, `host` and `port` are automatically set to `None`
  - This ensures cloud database is used when configured

### Security

- Added validation to prevent arbitrary git clone commands from untrusted input

---

## Version History

### Path Handling Fix (2026-01-25)

**Problem:**
When registering a memory cube, the system would incorrectly interpret:
1. Simple names like `DDSP-SVC-6.3` as HuggingFace repos
2. WSL paths like `/mnt/f/CyberAI/SVC/project` as HuggingFace repos

This caused `git clone` failures with cryptic error messages.

**Root Cause:**
```python
# OLD CODE (problematic)
if os.path.exists(mem_cube_name_or_path):
    # Load from local
else:
    # ALWAYS try HuggingFace - even for invalid inputs!
    GeneralMemCube.init_from_remote_repo(mem_cube_name_or_path)
```

**Solution:**
```python
# NEW CODE (robust)
if actual_path_exists:
    # Load from local (with cross-platform normalization)
elif is_valid_huggingface_repo(name):
    # Only clone if valid HF format: username/repo-name
elif looks_like_local_path(name):
    raise FileNotFoundError("Path does not exist...")
else:
    raise ValueError("Not a valid path or HF repo...")
```

**Files Modified:**
- `src/memos/mem_cube/utils.py` - Added path utilities
- `src/memos/mem_os/core.py` - Updated registration logic
- `src/memos/mem_os/product.py` - Updated registration logic

---

## Contributing

When adding entries to this changelog:
1. Add under `[Unreleased]` section
2. Use categories: Added, Changed, Deprecated, Removed, Fixed, Security
3. Include file paths when relevant
4. Explain the "why" not just the "what"
