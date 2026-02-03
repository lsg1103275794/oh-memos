# Changelog

All notable changes to the MemOS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **🔄 Embedder 自动降级方案** (`src/memos/embedders/fallback.py`)
  - 当云端嵌入服务(SiliconFlow/OpenAI)失败时，自动回退到本地 Ollama
  - **错误分类**: `classify_error()` 区分瞬态错误(timeout/429/503)和永久错误(401/404)
  - **重试策略**: `RetryPolicy` 实现指数退避 + 随机抖动 (可配置 max_retries, initial_delay, backoff_multiplier)
  - **维度适配**: `DimensionAdapter` 支持三种策略处理主备 embedder 维度不匹配
    - `error`: 报错 (默认，保证数据一致性)
    - `warn_and_continue`: 警告但继续
    - `pad_or_truncate`: 填充或截断
  - **FallbackEmbedder**: 装饰器模式无侵入包装主 embedder
  - **新增异常类型** (`src/memos/exceptions.py`):
    - `TransientEmbedderError`: 可重试错误 (timeout, 429, 500-504)
    - `PermanentEmbedderError`: 立即降级错误 (401, 403, 404)
    - `EmbeddingDimensionMismatchError`: 维度不匹配错误
  - **新增配置类** (`src/memos/configs/embedder.py`): `FallbackConfig`
  - **新增环境变量** (`src/memos/configs/env_loader.py`): 11 个 fallback 相关配置
  - **启用方式**:
    ```bash
    MOS_EMBEDDER_FALLBACK_ENABLED=true
    MOS_EMBEDDER_FALLBACK_MODEL=nomic-embed-text:latest
    ollama pull nomic-embed-text:latest
    ```
  - **重试时序示例**:
    ```
    T=0ms:    Try 1 → 失败 (timeout)
    T=1000ms: Try 2 → 失败 (delay 1s)
    T=3000ms: Try 3 → 失败 (delay 2s)
    T=7000ms: Fallback to Ollama → 成功
    ```

- **🛡️ MCP Fallback Tools for Isolated Projects** (`mcp-server/memos_mcp_server.py`)
  - `memos_register_cube`: Manual cube registration when auto-registration fails
    - Parameters: `cube_id` (required), `cube_path` (optional, auto-detected from MEMOS_CUBES_DIR)
    - Use case: "Cube not found" or "Cube not registered" errors
  - `memos_create_user`: Create user account for "user does not exist" errors
    - Parameters: `user_id` (required), `user_name` (optional, defaults to user_id)
    - Use case: "User 'xxx' does not exist" errors
  - Updated SKILL.md Troubleshooting section with MCP-only recovery steps (no Bash/curl required)
  - Added Quick Recovery Flowchart for common error scenarios
  - **Impact**: Models in completely isolated projects can now self-recover from errors using only MCP tools

- **🔍 Keyword Query Enhancement Module** (`mcp-server/keyword_enhancer.py`)
  - **Extended Stopwords Library**: 1300+ stopwords (816 English + 484 Chinese)
    - Programming terms: function, class, import, return, module, etc.
    - Chinese stopwords from Baidu, HIT, SCU comprehensive lists
  - **Fuzzy Matching**: Levenshtein distance algorithm for typo tolerance
    - Example: "configration" matches "configuration" (92% similarity)
    - Example: "databse" matches "database" (88% similarity)
    - Configurable threshold (default: 0.75)
  - **Structured Field Weighting**: Prioritize matches in metadata fields
    - `key` field match: +5.0 score
    - `tags` match: +3.0 score
    - Text exact match: +2.5 score
    - Text substring: +1.5 score
    - Fuzzy match: +1.0 × similarity
  - **Smart Cube Detection**: Auto-derive cube_id from project path
    - `/mnt/g/test/MemOS` → `memos_cube`
    - `C:\Projects\WebApp` → `webapp_cube`
    - Cross-platform support (Windows/Linux/WSL)

- **🧪 Keyword Enhancer Tests** (`tests/test_keyword_enhancer.py`)
  - Stopwords library validation (1300+ words)
  - Keyword extraction with stopword filtering
  - Levenshtein distance calculation
  - Fuzzy match finding
  - Structured field scoring
  - Smart cube detection (Unix and Windows paths)

- **📋 Keyword Optimization Planning Docs** (`docs/plans/`)
  - `keyword-query-optimization.md` - Task plan with phases
  - `keyword-optimization-findings.md` - Technical research
  - `keyword-optimization-progress.md` - Progress tracking

### Changed

- **⚡ Enhanced MCP Keyword Processing** (`mcp-server/memos_mcp_server.py`)
  - `extract_keywords()` - Now uses extended stopwords library when available
  - `keyword_match_score()` - Added metadata field weighting and fuzzy matching
  - `apply_keyword_rerank()` - Now passes metadata for structured scoring
  - `get_default_cube_id()` - Uses enhanced path detection
  - Backward compatible: Falls back to basic implementation if enhancer unavailable

### Technical Details

**Keyword Scoring Algorithm:**
```
Final Score = base_relativity + keyword_bonus

Where keyword_bonus =
  + 5.0 × (matches in key field)
  + 3.0 × (matches in tags)
  + 2.5 × (exact word boundary matches)
  + 1.5 × (substring matches)
  + 1.0 × similarity (fuzzy matches above threshold)
  + 1.5 × (matched_count / total_keywords)
```

**Fuzzy Matching Example:**
```
Query: "configration error"
Text: "Configuration error in database"

Levenshtein distance("configration", "configuration") = 1
Similarity = 1 - (1/13) = 0.92 > 0.75 threshold
→ Match found with 0.92 score bonus
```

### Fixed

- **🔧 Import Error: parse_json_result and detect_lang** (`mem_reader/utils.py`, `retrieve_utils.py`)
  - **Issue**: `ImportError: cannot import name 'parse_json_result' from 'memos.mem_reader.utils'`
  - **Root Cause**: Functions were defined in `read_multi_modal/utils.py` but imported from parent modules
  - **Fix**: Added re-exports in `memos/mem_reader/utils.py` and `retrieve/retrieve_utils.py`
  - **Impact**: API startup and all memory operations now work correctly

---

### Added

- **🔗 Graph API Endpoints** (start_api.py)
  - **`/graph/trace_path`**: Trace causality paths between two memory nodes (supports max_depth up to 10 hops)
  - **`/graph/schema`**: Export knowledge graph statistics including node/edge counts, relationship distribution, tag frequency, health metrics
  - **`/search` enhancement**: Added `enable_context_analysis` and `chat_history` parameters for LLM-powered context-aware search

- **🧠 New MCP Tools** (memos_mcp_server.py)
  - **`memos_export_schema`**: Export graph structure with health assessment (orphan ratio, connectivity)
  - **`memos_search_context`**: Context-aware search using conversation history for smarter results
  - **`memos_trace_path`**: Trace reasoning paths between memories to understand causality chains

- **🔒 智能项目感知 (Smart Project Awareness)** (project-memory/SKILL.md, memos_mcp_server.py)
  - **Auto-Derivation**: Claude skills now automatically derive `cube_id` from the project directory name (e.g., `MemOS` -> `memos_cube`).
  - **Zero-Config Isolation**: Users only need to copy the skill to `.claude/skills/` to enable isolated memory space for any project.
  - **Mandatory Triggers**: Updated `SKILL.md` with strict rules for when AI MUST use `memos_search` or `memos_get_graph`.
  - **Deployment Docs**: Added step-by-step guides for deploying Claude skills in both English and Chinese READMEs.

- **📊 Enhanced MCP Server Tools** (memos_mcp_server.py)
  - **Mermaid Graph Support**: `memos_get_graph` now generates Mermaid diagrams for visual relationship exploration.
  - **Smart Filtering**: `memos_list` now supports `memory_type` filtering (e.g., list only DECISIONS or ERRORS).
  - **Memory Statistics**: New tool `memos_get_stats` to show memory distribution by type in a cube.
  - **Improved Display**: Search results are now grouped by memory type with automatic code block detection.
  - **Robust Registration**: Enhanced auto-registration logic with forced retry on tool call failure.

### Fixed

- **🔧 Neo4j Cypher Query Syntax** (neo4j.py)
  - **Issue**: `get_schema_statistics()` generated invalid Cypher with duplicate WHERE clauses
  - **Root Cause**: When `user_clause` existed, queries like tag_query and time_query had `WHERE ... WHERE ...`
  - **Fix**: Use conditional WHERE/AND logic to avoid duplicate WHERE clauses
  - **Impact**: `memos_export_schema` now works correctly for multi-tenant mode

- **🔧 MCP Server Robustness & Save Failures** (memos_mcp_server.py)
  - **Issue**: Encountered 502 (Bad Gateway) and 400 (Cube not loaded) errors during memory saving.
  - **Path Healing**: Optimized `ensure_cube_registered` to correctly resolve physical paths for default cubes (e.g., `dev_cube`).
  - **Aggressive Retry**: Implemented automatic cache clearing and re-registration retry logic for `memos_search`, `memos_get_stats`, and `memos_get_graph`.
  - **Reliability**: Server now automatically recovers from backend restarts or cube unloads without user intervention.

- **🔧 MCP Search Result ID Truncation** (memos_mcp_server.py)
  - **Root Cause**: Search results showed truncated IDs (`4a7ddcf7...`) but Neo4j requires full UUID for deletion
  - **Fix**: `format_memories_for_display()` and `memos_get_graph` now return complete UUIDs
  - **Impact**: `memos_delete` can now correctly delete memories using IDs from search results
  - Collaboration: Claude Opus + Gemini (API endpoint fix + multi-DB sync verification)

- **🔧 WSL Environment Variable Passing** (run_mcp.sh, memos_mcp_server.py)
  - **Issue**: Claude Code's `env` config doesn't pass through to Windows Python via WSL bash
  - **Fix**: Added CLI argument parsing (`--memos-enable-delete`, etc.) as fallback
  - **Default**: `MEMOS_ENABLE_DELETE=true` for dev environment in run_mcp.sh
  - All timeout and config variables now support both env vars and CLI args

- **📊 README Architecture Diagrams Update** (README.md)
  - Updated main architecture diagram with complete `tree_text` mode data flow
  - Added **Memory Save Flow**: LLM Extraction → Neo4j + Qdrant → Reorganizer (async)
  - Added **Memory Search Flow**: Qdrant semantic + Neo4j graph traverse → merged results
  - Added **LLM Usage Summary**: Dual LLM use (extraction + relationship detection)
  - Updated Privacy Architecture to include Neo4j local storage
  - Updated MCP tools table: 8 tools (added `memos_list_v2`, `memos_get_stats`, `memos_delete`)

- **🗑️ Memory Deletion & Synchronization Optimization**
  - **API Correction**: Fixed memory deletion endpoint format to `/memories/{mem_cube_id}/{memory_id}` to resolve 500 errors.
  - **Multi-DB Sync**: Verified end-to-end deletion sync across MemCube list, Qdrant (Vector DB), and Neo4j (Graph DB).
  - **Graph Integrity**: Confirmed Neo4j `DETACH DELETE` logic correctly removes nodes and all associated relationships/edges.
  - **Verification Suite**: Developed `verify_mems.py` for automated cross-database deletion verification.
  - **MCP Tool Safety**: Validated `memos_delete` tool with `MEMOS_ENABLE_DELETE` safety flag and batch deletion (`memory_ids`) support.

- **�🔗 Knowledge Graph Relationship Query** (NEW - memos_get_graph)
  - New MCP tool `memos_get_graph` for querying memory relationships
  - Returns CAUSE, RELATE, CONFLICT, CONDITION relationships from Neo4j
  - Direct Neo4j HTTP API integration for relationship queries
  - Example: Query "Neo4j" shows `[Java 17 required] ──CAUSE──> [Neo4j startup failed]`
  - Updated SKILL.md with trigger rules for dependency queries
  - Triggers: "依赖关系", "root cause", "为什么失败", "冲突", "关联"

- **📝 MCP Configuration Examples** (README.md)
  - Added `alwaysAllow` array examples for automatic tool invocation
  - Includes all 5 MCP tools: `memos_search`, `memos_save`, `memos_list`, `memos_suggest`, `memos_get_graph`
  - Added examples for both WSL and pure Windows environments
  - Added Chinese MCP configuration section with full example

- **📄 CLAUDE.md Project Context** (NEW)
  - Created `CLAUDE.md` for project-specific Claude Code context
  - Includes: Memory system behaviors, memory types, configuration, key files
  - Claude reads this at conversation start for better context awareness
  - Added documentation links in README

- **🪝 Claude Code Hooks System** (NEW)
  - Created `.claude/hooks/` directory with 4 hook scripts:
    - `memos_user_prompt.sh` - Confirms memory system active on user input
    - `memos_block_sensitive.sh` - Warns when editing .env/credentials
    - `memos_log_commands.sh` - Logs bash commands to history file
    - `memos_notify_milestone.sh` - Suggests saving milestones for important files
  - Added `.claude/settings.json` with hooks configuration
  - Added `.claude/hooks/README.md` with usage documentation

- **🎬 Cross-Project Memory Demo** (README.md)
  - Added "Scenario 3: Cross-Project Memory Retrieval" with real demo
  - Shows AI searching MemOS memories from different project (DDSP-SVC)
  - Screenshots archived at `docs/ScreenShot/`

- **📊 Optimization Plan v2.0** (`.memos/优化方案.md`)
  - Updated with verification results
  - Architecture evolution diagram (v0.1 → v0.4)
  - Success metrics and next steps

- **🔒 Privacy-First Architecture Section** (README.md)
  - Added visual architecture diagram showing data flow
  - Highlights that original text stays local (Ollama embedding)
  - Only numerical vectors uploaded to Qdrant Cloud
  - Comparison table: "What Stays Local" vs "What Goes to Cloud"
  - Added corresponding Chinese version in 中文文档 section

- **🧠 Neo4j Knowledge Graph Memory Mode** (v0.4.0 preview)
  - Upgraded from `general_text` to `tree_text` memory backend
  - Added Neo4j Community Edition support for graph storage
  - Memory nodes now include: key, memory, background, tags, confidence
  - Dual storage: WorkingMemory + LongTermMemory
  - LLM-powered memory extraction (auto tags, key extraction)
  - Visual graph exploration via Neo4j Browser
  - Configuration: `dev_cube/config.json` with `tree_text` backend

### Fixed

- **🔧 MCP Cube Registration LLM Trigger** (reorganizer.py)
  - Fixed unnecessary LLM calls when loading existing cube
  - Changed `_reorganize_needed` initial value from `True` to `False`
  - Reorganizer now only triggers when new memories are actually added
  - Before: Every `init_from_dir()` → immediate LLM cluster/summarize call
  - After: LLM only called after `handle_add()` processes new nodes
  - Significantly reduces API costs and startup time

- **🔧 Relationship Detection Parser**
  - Fixed `_parse_relation_result()` to extract only first word from LLM response
  - LLM returns `RELATE\n\n**Reasoning:**...` but parser expected single word
  - Now correctly detects CAUSE, RELATE, CONFLICT, CONDITION relationships

- **🔧 Neo4j SourceMessage Serialization**
  - Fixed `build_summary_parent_node()` returning `SourceMessage` objects
  - Neo4j packstream doesn't support custom Python objects
  - Changed to return serializable dicts instead

- **🔧 Neo4jCommunityGraphDB Compatibility**
  - Added missing `status` and `user_name_flag` parameters to `get_by_metadata()`
  - Fixed search API 500 error when using tree_text mode with Neo4j Community Edition

### Changed

- **⚙️ Reorganizer Configuration**
  - Added `MOS_REORGANIZE_MIN_GROUP` env var (default: 10, was hardcoded 20)
  - Added `MOS_REORGANIZE_TIMEOUT` env var (default: 1800s for slow LLM APIs)
  - Allows relationship detection to trigger with fewer candidate nodes

- **📝 SKILL.md Updates**
  - Added `memos_get_graph` to Quick Reference table
  - Added "When to Get Graph" trigger rules section
  - Updated workflow diagram with dependency checking flows

- **📝 README.md Major Update**
  - Added "Two Memory Modes" comparison table
  - Updated architecture diagram showing Neo4j + Qdrant dual storage
  - Added "Knowledge Graph Memory Mode" section with setup guide
  - Added "Enhance with CLAUDE.md" section
  - Updated Requirements table with Neo4j
  - Added Neo4j badge and related link
  - Updated Chinese documentation section

- **📝 Enhanced .env Documentation**
  - Added detailed comments explaining LLM usage in tree_text mode
  - LLM is used for: memory extraction (key, tags, background), confidence scoring, memory categorization
  - Updated `docker/.env.example` with tree_text mode documentation

## [0.3.2] - 2026-01-26

### Changed

- **📝 Simplified SKILL.md** - Refactored from 769 lines to 237 lines
  - Now focuses on **MCP tool usage** instead of script execution
  - Removed detailed CLI script documentation (kept as "Legacy Scripts")
  - Added quick reference table for MCP tools
  - Added clear workflow diagram for MCP-based memory management
  - Kept memory type format templates (ERROR_PATTERN, DECISION, etc.)

- **📦 Archived Legacy Scripts** - Moved to `scripts/legacy/`
  - `memos_init_project.py` → Replaced by MCP auto-registration
  - `memos_save.py` → Replaced by `memos_save` MCP tool
  - `memos_search.py` → Replaced by `memos_search` MCP tool
  - Kept `memos_utils.py` in main scripts folder (utility functions)
  - Added `legacy/README.md` explaining archive reason

### Technical Details

**Old Architecture (Script-based):**
```
User → /project-memory → SKILL.md → Execute Python scripts → API
```

**New Architecture (MCP-powered):**
```
User → /project-memory → SKILL.md → Guide to use MCP tools → MCP Server → API
```

**New Directory Structure:**
```
.claude/skills/project-memory/
├── SKILL.md              # MCP usage guide (237 lines)
└── scripts/
    ├── memos_utils.py    # Utility functions (kept)
    └── legacy/           # Archived scripts
        ├── README.md
        ├── memos_init_project.py
        ├── memos_save.py
        └── memos_search.py
```

**Benefits:**
- Unified interface: MCP handles all memory operations
- Auto-registration: No need to run init scripts
- Simpler maintenance: One codebase (MCP Server) instead of two
- Better UX: AI uses tools directly without shell execution

---

## [0.3.1] - 2026-01-26

### Added

- **🔄 Auto-Register Cube** (`mcp-server/memos_mcp_server.py`)
  - MCP tools now automatically register cubes on first use
  - No more manual `curl` commands needed to create cubes
  - Added `ensure_cube_registered()` unified function
  - Added `_registered_cubes` cache to avoid repeated registration attempts

- **New Environment Variable** `MEMOS_CUBES_DIR`
  - Configurable cube storage directory
  - Default: `G:/test/MemOS/data/memos_cubes`
  - Used for auto-registration path

### Changed

- **Simplified `memos_save`** - Removed duplicate registration logic, now uses shared function
- **Updated `run_mcp.sh`** - Added `MEMOS_CUBES_DIR` export

---

## [0.3.0] - 2026-01-26

### Added

- **🚀 MCP Server for Proactive Memory** (`mcp-server/`)
  - New MCP (Model Context Protocol) Server enabling Claude Code to **proactively** use memory functions
  - No longer need to wait for user to manually call `/project-memory` commands
  - AI can now automatically search memories when encountering errors or making decisions

- **MCP Tools** (`mcp-server/memos_mcp_server.py`)
  - `memos_search` - Search project memories with intelligent triggers
    - Auto-triggers when: encountering errors, user says "之前/上次", modifying code
    - Searches: `ERROR_PATTERN`, `DECISION`, `GOTCHA`, `CODE_PATTERN`, `CONFIG`
  - `memos_save` - Save memories with auto-type detection
    - Auto-triggers when: solving bugs, making decisions, completing tasks
    - Detects memory type from content keywords
  - `memos_list` - List all memories in a project cube
  - `memos_suggest` - Get smart search suggestions based on context

- **MCP Configuration Guide** (`docs/MCP_GUIDE.md`)
  - Complete setup instructions for Claude Code integration
  - Tool reference with parameters and examples
  - Troubleshooting guide
  - Architecture diagram

- **MCP Installation Tools** (`mcp-server/`)
  - `install.py` - Auto-configure Claude Code settings.json
  - `test_server.py` - Verify MCP server functionality
  - `pyproject.toml` - Package configuration for pip install
  - **`run_mcp.sh`** - WSL wrapper script for path translation

### Changed

- **Architecture**: Project now supports two integration modes
  - **Skill Mode (Passive)**: User manually calls `/project-memory` commands
  - **MCP Mode (Proactive)**: AI automatically uses memory tools when appropriate

- **Documentation Structure**: Updated to include MCP documentation
  - Added MCP Guide link to main README
  - Updated Quick Navigation table

### Fixed

- **🐛 WSL MCP Startup Failure** - Critical fix for MCP server not starting in WSL environment
  - **Problem**: Windows Python couldn't process WSL paths (`/mnt/g/...` → `G:\mnt\g\...`)
  - **Solution**: Added `run_mcp.sh` wrapper script that:
    - Uses WSL path to invoke Windows Python: `/mnt/g/.../python.exe`
    - Passes Windows-format path to script: `G:/test/.../script.py`
  - **Config Change**: Use `bash` as command with wrapper script as argument
    ```json
    "command": "bash",
    "args": ["/mnt/g/test/MemOS/mcp-server/run_mcp.sh"]
    ```

### Technical Details

**MCP Server Architecture:**
```
User Input -> Claude Code -> Context Analysis -> MCP Tool Decision
                                                       |
                            +-------------+------------+
                            |                          |
                            v                          v
                  memos_search (proactive)   memos_save (proactive)
                            |                          |
                            v                          v
                       MemOS API (:18000)         MemOS API
                            |                          |
                            v                          v
                  Embedding + Qdrant            Embedding + Qdrant
```

**WSL Path Translation (run_mcp.sh):**
```
Claude Code (WSL bash)
        | runs
        v
    run_mcp.sh
        | invokes (WSL path)
        v
    /mnt/g/.../python.exe
        | with (Windows path)
        v
    G:/test/.../memos_mcp_server.py
        | connects
        v
    MemOS API (localhost:18000)
```

**Proactive Trigger Scenarios:**

| Scenario | Tool Called | Search/Save Type |
|----------|-------------|------------------|
| Error encountered | `memos_search` | `ERROR_PATTERN {type}` |
| User says "之前" | `memos_search` | Related history |
| Code modification | `memos_search` | `GOTCHA`, `CODE_PATTERN` |
| Bug solved | `memos_save` | `ERROR_PATTERN` |
| Decision made | `memos_save` | `DECISION` |
| Task completed | `memos_save` | `MILESTONE` |

---

## [0.2.0] - 2026-01-26

### Added

- **Environment variable priority for cube configs** (`src/memos/mem_cube/utils.py`, `general.py`)
  - New `apply_env_overrides()` function that applies .env settings to cube configs
  - Ensures .env takes priority over hardcoded config.json values
  - Supports all key configurations:
    - Qdrant: `QDRANT_URL`, `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY`, `QDRANT_PATH`
    - Embedder: `MOS_EMBEDDER_BACKEND`, `MOS_EMBEDDER_MODEL`, `OLLAMA_API_BASE`
    - LLM: `MOS_CHAT_MODEL`, `OPENAI_API_KEY`, `OPENAI_API_BASE`, `MOS_CHAT_TEMPERATURE`
  - Logs all overrides for debugging: `[ENV Override] Qdrant URL: xxx -> yyy`

- **Cube ID resolution and caching** (`.claude/skills/project-memory/scripts/memos_utils.py`)
  - `resolve_cube_id()` - Maps project names to full cube paths automatically
  - `load_cube_cache()`, `save_cube_cache()`, `update_cube_cache()` - Persistent cache management
  - `get_registered_cubes()` - Query API for all registered cubes
  - Cache stored at `~/.memos_cube_cache.json`

- **Comprehensive troubleshooting guide** (`.claude/skills/project-memory/SKILL.md`)
  - Cube ID format issues and solutions
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

### Changed

- **Unified configuration via .env** - All infrastructure configs now use environment variables
  - Config priority: `.env` > `config.json` > code defaults
  - Single source of truth for Qdrant, Embedder, LLM settings

- **Improved project-memory skill scripts** (`.claude/skills/project-memory/scripts/`)
  - `memos_save.py`: Now auto-resolves cube names to full paths before API calls
  - `memos_search.py`: Now auto-resolves cube names to full paths before API calls
  - `memos_init_project.py`: Caches cube ID mapping after successful registration
  - All scripts now provide better error messages and hints
  - Default embedder model updated to `nomic-embed-text-v2-moe:latest`

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

- **Cube ID Format Issue**: Scripts now auto-resolve project names to full paths
  - Previously: Had to manually use full paths like `G:/test/MemOS/data/memos_cubes/dev_cube`
  - Now: Just use `dev_cube` and it auto-resolves

- **Embedder Backend Validation**: Fixed env override applying wrong fields to Ollama backend
  - Only applies `api_base` for Ollama
  - Only applies `base_url`, `api_key`, `provider` for universal_api

- **Pydantic Serialization Warning**: Fixed type annotation in `ParserConfigFactory`
  - `config` field now correctly typed as `Union[dict, BaseParserConfig]`
  - Eliminates `PydanticSerializationUnexpectedValue` warning

- **Startup Warnings**: Suppressed harmless warnings during API startup
  - PyTorch/TensorFlow not found (not needed when using Ollama)
  - Pydantic serialization warnings for known edge cases

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
