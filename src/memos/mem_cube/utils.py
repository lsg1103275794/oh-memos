import copy
import logging
import os
import platform
import re
import subprocess
import tempfile

from memos.configs.mem_cube import GeneralMemCubeConfig


logger = logging.getLogger(__name__)


# ============== Environment Variable Overrides ==============

def apply_env_overrides(config: GeneralMemCubeConfig) -> GeneralMemCubeConfig:
    """Apply environment variable overrides to cube configuration.

    This ensures that .env settings take priority over hardcoded config.json values.
    Only overrides values if the environment variable is set (non-empty).

    Supported environment variables:
        Qdrant:
            - QDRANT_URL: Cloud endpoint URL (if set, host/port are ignored)
            - QDRANT_HOST: Local host (only used if QDRANT_URL is not set)
            - QDRANT_PORT: Local port (only used if QDRANT_URL is not set)
            - QDRANT_API_KEY: API key for cloud
            - QDRANT_PATH: Local storage path

        Embedder:
            - MOS_EMBEDDER_BACKEND: Backend type ("ollama" or "universal_api")
            - MOS_EMBEDDER_MODEL: Model name
            - OLLAMA_API_BASE: Ollama API base URL
            - MOS_EMBEDDER_API_BASE: Universal API base URL
            - MOS_EMBEDDER_API_KEY: Universal API key
            - MOS_EMBEDDER_PROVIDER: Universal API provider
            - EMBEDDING_DIMENSION: Vector dimension

        LLM (extractor):
            - MOS_CHAT_MODEL: Model name
            - OPENAI_API_KEY: API key
            - OPENAI_API_BASE: API base URL
            - MOS_CHAT_TEMPERATURE: Temperature
            - MOS_MAX_TOKENS: Max tokens

    Args:
        config: The cube configuration to modify

    Returns:
        GeneralMemCubeConfig: Modified configuration with env overrides applied
    """
    config_dict = config.model_dump(mode="json")
    modified = False

    # Helper to get env var, returns None if empty
    def get_env(key: str) -> str | None:
        val = os.environ.get(key, "").strip()
        return val if val else None

    # ===== Qdrant Vector DB Overrides =====
    if "text_mem" in config_dict and config_dict["text_mem"].get("config"):
        text_config = config_dict["text_mem"]["config"]

        if "vector_db" in text_config and text_config["vector_db"].get("config"):
            vec_config = text_config["vector_db"]["config"]
            qdrant_url = get_env("QDRANT_URL")

            if qdrant_url:
                # Cloud mode: use URL, clear host/port
                if vec_config.get("url") != qdrant_url:
                    logger.info(f"[ENV Override] Qdrant URL: {vec_config.get('url')} -> {qdrant_url}")
                    vec_config["url"] = qdrant_url
                    vec_config["host"] = None
                    vec_config["port"] = None
                    modified = True
            else:
                # Local mode: use host/port
                qdrant_host = get_env("QDRANT_HOST")
                qdrant_port = get_env("QDRANT_PORT")
                if qdrant_host and vec_config.get("host") != qdrant_host:
                    logger.info(f"[ENV Override] Qdrant host: {vec_config.get('host')} -> {qdrant_host}")
                    vec_config["host"] = qdrant_host
                    modified = True
                if qdrant_port and vec_config.get("port") != int(qdrant_port):
                    logger.info(f"[ENV Override] Qdrant port: {vec_config.get('port')} -> {qdrant_port}")
                    vec_config["port"] = int(qdrant_port)
                    modified = True

            qdrant_api_key = get_env("QDRANT_API_KEY")
            if qdrant_api_key and vec_config.get("api_key") != qdrant_api_key:
                logger.info("[ENV Override] Qdrant API key: *** -> ***")
                vec_config["api_key"] = qdrant_api_key
                modified = True

            qdrant_path = get_env("QDRANT_PATH")
            if qdrant_path and vec_config.get("path") != qdrant_path:
                logger.info(f"[ENV Override] Qdrant path: {vec_config.get('path')} -> {qdrant_path}")
                vec_config["path"] = qdrant_path
                modified = True

            embedding_dim = get_env("EMBEDDING_DIMENSION")
            if embedding_dim and vec_config.get("vector_dimension") != int(embedding_dim):
                logger.info(f"[ENV Override] Vector dimension: {vec_config.get('vector_dimension')} -> {embedding_dim}")
                vec_config["vector_dimension"] = int(embedding_dim)
                modified = True

        # ===== Embedder Overrides =====
        if "embedder" in text_config and text_config["embedder"].get("config"):
            emb_config = text_config["embedder"]["config"]
            current_backend = text_config["embedder"].get("backend", "ollama")
            emb_backend = get_env("MOS_EMBEDDER_BACKEND")

            if emb_backend and current_backend != emb_backend:
                logger.info(f"[ENV Override] Embedder backend: {current_backend} -> {emb_backend}")
                text_config["embedder"]["backend"] = emb_backend
                current_backend = emb_backend
                modified = True

            emb_model = get_env("MOS_EMBEDDER_MODEL")
            if emb_model and emb_config.get("model_name_or_path") != emb_model:
                logger.info(f"[ENV Override] Embedder model: {emb_config.get('model_name_or_path')} -> {emb_model}")
                emb_config["model_name_or_path"] = emb_model
                modified = True

            # Apply backend-specific overrides only
            if current_backend == "ollama":
                # Ollama specific: only api_base
                ollama_base = get_env("OLLAMA_API_BASE")
                if ollama_base and emb_config.get("api_base") != ollama_base:
                    logger.info(f"[ENV Override] Ollama API base: {emb_config.get('api_base')} -> {ollama_base}")
                    emb_config["api_base"] = ollama_base
                    modified = True
            elif current_backend == "universal_api":
                # Universal API specific
                emb_api_base = get_env("MOS_EMBEDDER_API_BASE")
                if emb_api_base and emb_config.get("base_url") != emb_api_base:
                    logger.info(f"[ENV Override] Embedder API base: {emb_config.get('base_url')} -> {emb_api_base}")
                    emb_config["base_url"] = emb_api_base
                    modified = True

                emb_api_key = get_env("MOS_EMBEDDER_API_KEY")
                if emb_api_key and emb_config.get("api_key") != emb_api_key:
                    logger.info("[ENV Override] Embedder API key: *** -> ***")
                    emb_config["api_key"] = emb_api_key
                    modified = True

                emb_provider = get_env("MOS_EMBEDDER_PROVIDER")
                if emb_provider and emb_config.get("provider") != emb_provider:
                    logger.info(f"[ENV Override] Embedder provider: {emb_config.get('provider')} -> {emb_provider}")
                    emb_config["provider"] = emb_provider
                    modified = True

        # ===== LLM/Extractor Overrides =====
        if "extractor_llm" in text_config and text_config["extractor_llm"].get("config"):
            llm_config = text_config["extractor_llm"]["config"]

            chat_model = get_env("MOS_CHAT_MODEL")
            if chat_model and llm_config.get("model_name_or_path") != chat_model:
                logger.info(f"[ENV Override] LLM model: {llm_config.get('model_name_or_path')} -> {chat_model}")
                llm_config["model_name_or_path"] = chat_model
                modified = True

            openai_key = get_env("OPENAI_API_KEY")
            if openai_key and llm_config.get("api_key") != openai_key:
                logger.info("[ENV Override] OpenAI API key: *** -> ***")
                llm_config["api_key"] = openai_key
                modified = True

            openai_base = get_env("OPENAI_API_BASE")
            if openai_base and llm_config.get("api_base") != openai_base:
                logger.info(f"[ENV Override] OpenAI API base: {llm_config.get('api_base')} -> {openai_base}")
                llm_config["api_base"] = openai_base
                modified = True

            chat_temp = get_env("MOS_CHAT_TEMPERATURE")
            if chat_temp:
                temp_float = float(chat_temp)
                if llm_config.get("temperature") != temp_float:
                    logger.info(f"[ENV Override] LLM temperature: {llm_config.get('temperature')} -> {temp_float}")
                    llm_config["temperature"] = temp_float
                    modified = True

            max_tokens = get_env("MOS_MAX_TOKENS")
            if max_tokens:
                max_int = int(max_tokens)
                if llm_config.get("max_tokens") != max_int:
                    logger.info(f"[ENV Override] LLM max_tokens: {llm_config.get('max_tokens')} -> {max_int}")
                    llm_config["max_tokens"] = max_int
                    modified = True

    if modified:
        logger.info("Environment variable overrides applied to cube config")
        return GeneralMemCubeConfig.model_validate(config_dict)

    return config


# ============== HuggingFace Validation ==============


def is_valid_huggingface_repo(name: str) -> bool:
    """Check if a string looks like a valid HuggingFace repository name.

    Valid HF repo formats:
    - username/repo-name
    - organization/repo-name

    NOT valid (these look like local paths or simple names):
    - DDSP-SVC-6.3 (no slash, simple name)
    - /mnt/g/test/project (absolute path)
    - C:/Users/project (Windows path)
    - ./relative/path (relative path)

    Args:
        name: String to check

    Returns:
        bool: True if it looks like a valid HF repo name
    """
    if not name or not isinstance(name, str):
        return False

    # Must contain exactly one slash (username/repo format)
    if name.count('/') != 1:
        return False

    # Should not look like a path
    if name.startswith('/') or name.startswith('./') or name.startswith('../'):
        return False
    if name.startswith('\\') or ':' in name:  # Windows paths
        return False

    # Split and validate parts
    parts = name.split('/')
    if len(parts) != 2:
        return False

    username, repo = parts

    # Both parts should be non-empty and look like valid identifiers
    if not username or not repo:
        return False

    # HF usernames/repos typically use alphanumeric, hyphens, underscores
    # and shouldn't start with special characters
    valid_pattern = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$')
    if not valid_pattern.match(username) or not valid_pattern.match(repo):
        return False

    return True


def get_wsl_distro_name() -> str | None:
    """Get the current WSL distribution name.

    Returns:
        Distribution name or None if not in WSL or cannot determine.
    """
    try:
        # Try to get from WSL_DISTRO_NAME environment variable
        distro = os.environ.get('WSL_DISTRO_NAME')
        if distro:
            return distro

        # Try to read from /etc/os-release
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('NAME='):
                        name = line.split('=')[1].strip().strip('"')
                        # Common mappings
                        if 'Ubuntu' in name:
                            # Try to get version
                            for line2 in f:
                                if line2.startswith('VERSION_ID='):
                                    version = line2.split('=')[1].strip().strip('"')
                                    return f"Ubuntu-{version}"
                            return "Ubuntu"
                        return name
    except:
        pass
    return None


def normalize_path(path: str) -> str | None:
    """Normalize a path string for the current platform.

    Handles:
    - WSL paths (/mnt/c/...) when running on Windows
    - WSL home paths (/home/...) when running on Windows (converts to UNC path)
    - Windows paths (C:\\...) when running on WSL/Linux
    - Standard Unix/Windows paths

    Args:
        path: Path string to normalize

    Returns:
        Normalized path or None if invalid
    """
    if not path or not isinstance(path, str):
        return None

    system = platform.system().lower()

    # Handle WSL path on Windows
    if system == 'windows':
        # Convert /mnt/X/... to X:/...
        wsl_match = re.match(r'^/mnt/([a-zA-Z])(/.*)$', path)
        if wsl_match:
            drive = wsl_match.group(1).upper()
            rest = wsl_match.group(2)
            return f"{drive}:{rest}".replace('/', '\\')

        # Convert /home/... or /usr/... etc to \\wsl$\<distro>\...
        # These are pure WSL paths that need UNC conversion
        if path.startswith('/') and not path.startswith('/mnt/'):
            # Try common WSL distro names
            for distro in ['Ubuntu-24.04', 'Ubuntu-22.04', 'Ubuntu-20.04', 'Ubuntu', 'Debian', 'kali-linux']:
                unc_path = f"\\\\wsl$\\{distro}{path}".replace('/', '\\')
                if os.path.exists(unc_path):
                    return unc_path
            # Also try wsl.localhost format
            for distro in ['Ubuntu-24.04', 'Ubuntu-22.04', 'Ubuntu-20.04', 'Ubuntu', 'Debian']:
                unc_path = f"\\\\wsl.localhost\\{distro}{path}".replace('/', '\\')
                if os.path.exists(unc_path):
                    return unc_path
            # Return None - path cannot be normalized for Windows
            return None

    # Handle Windows path on Linux/WSL
    elif system == 'linux':
        # Check if we're in WSL
        is_wsl = os.path.exists('/proc/version')
        if is_wsl:
            try:
                with open('/proc/version') as f:
                    if 'microsoft' in f.read().lower():
                        # Convert C:/... or C:\... to /mnt/c/...
                        win_match = re.match(r'^([a-zA-Z]):[/\\](.*)$', path)
                        if win_match:
                            drive = win_match.group(1).lower()
                            rest = win_match.group(2).replace('\\', '/')
                            return f"/mnt/{drive}/{rest}"
            except:
                pass

    # Return original path with normalized separators
    if system == 'windows':
        return path.replace('/', '\\')
    else:
        return path.replace('\\', '/')


def path_exists(path: str) -> bool:
    """Check if a path exists, with cross-platform support.

    Args:
        path: Path to check

    Returns:
        bool: True if path exists
    """
    if not path:
        return False

    # Try original path first
    if os.path.exists(path):
        return True

    # Try normalized path
    normalized = normalize_path(path)
    if normalized and normalized != path:
        return os.path.exists(normalized)

    return False


def looks_like_local_path(name: str) -> bool:
    """Check if a string looks like a local file path (not a repo name).

    Args:
        name: String to check

    Returns:
        bool: True if it looks like a local path
    """
    if not name:
        return False

    # Absolute paths
    if name.startswith('/') or name.startswith('\\'):
        return True

    # Windows drive paths
    if len(name) > 2 and name[1] == ':':
        return True

    # Relative paths
    if name.startswith('./') or name.startswith('../'):
        return True
    if name.startswith('.\\') or name.startswith('..\\'):
        return True

    # Contains path separators in unusual positions
    if '\\' in name:
        return True

    # Multiple slashes (not HF format)
    if name.count('/') > 1:
        return True

    return False


def download_repo(repo: str, base_url: str, dir: str | None = None) -> str:
    """Download a repository from a remote source.

    Args:
        repo (str): The repository name (must be in format: username/repo-name).
        base_url (str): The base URL of the remote repository.
        dir (str, optional): The directory where the repository will be downloaded.
            If None, a temporary directory will be created.

    Returns:
        str: The local directory where the repository is downloaded.

    Raises:
        ValueError: If repo is not a valid HuggingFace repository name.
        subprocess.CalledProcessError: If git clone fails.
    """
    # Validate repo name format
    if not is_valid_huggingface_repo(repo):
        if looks_like_local_path(repo):
            raise ValueError(
                f"'{repo}' looks like a local path, not a HuggingFace repository name. "
                f"Use a local path that exists on your system, or provide a valid "
                f"HuggingFace repo in 'username/repo-name' format."
            )
        else:
            raise ValueError(
                f"'{repo}' is not a valid HuggingFace repository name. "
                f"Expected format: 'username/repo-name' (e.g., 'my-org/my-dataset'). "
                f"If this is a local project, create a local cube directory first."
            )

    if dir is None:
        dir = tempfile.mkdtemp()
    repo_url = f"{base_url}/{repo}"

    logger.info(f"Cloning HuggingFace repository: {repo_url}")

    # Clone the repo
    try:
        subprocess.run(["git", "clone", repo_url, dir], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        raise subprocess.CalledProcessError(
            e.returncode, e.cmd,
            output=e.output,
            stderr=f"Failed to clone HuggingFace repo '{repo}'. "
                   f"Make sure the repository exists and is accessible. "
                   f"Original error: {stderr}".encode()
        )

    return dir


def merge_config_with_default(
    existing_config: GeneralMemCubeConfig, default_config: GeneralMemCubeConfig
) -> GeneralMemCubeConfig:
    """
    Merge existing cube config with default config, preserving critical fields.

    This method updates general configuration fields (like API keys, model parameters)
    while preserving critical user-specific fields (like user_id, cube_id, graph_db settings).

    Args:
        existing_config (GeneralMemCubeConfig): The existing cube configuration loaded from file
        default_config (GeneralMemCubeConfig): The default configuration to merge from

    Returns:
        GeneralMemCubeConfig: Merged configuration
    """

    # Convert configs to dictionaries
    existing_dict = existing_config.model_dump(mode="json")
    default_dict = default_config.model_dump(mode="json")

    logger.info(
        f"Starting config merge for user {existing_config.user_id}, cube {existing_config.cube_id}"
    )

    # Define fields that should be preserved from existing config
    preserve_fields = {"user_id", "cube_id", "config_filename", "model_schema"}

    # Preserve graph_db from existing config if it exists, but merge some fields
    preserved_graph_db = None
    if "text_mem" in existing_dict and "text_mem" in default_dict:
        existing_text_config = existing_dict["text_mem"].get("config", {})
        default_text_config = default_dict["text_mem"].get("config", {})

        if "graph_db" in existing_text_config and "graph_db" in default_text_config:
            existing_graph_config = existing_text_config["graph_db"]["config"]
            default_graph_config = default_text_config["graph_db"]["config"]
            existing_backend = existing_text_config["graph_db"]["backend"]
            default_backend = default_text_config["graph_db"]["backend"]

            # Detect backend change
            backend_changed = existing_backend != default_backend

            if backend_changed:
                logger.info(
                    f"Detected graph_db backend change: {existing_backend} -> {default_backend}. "
                    f"Migrating configuration..."
                )
                # Start with default config as base when backend changes
                merged_graph_config = copy.deepcopy(default_graph_config)

                # Preserve user-specific fields if they exist in both configs
                preserve_graph_fields = {
                    "auto_create",
                    "user_name",
                    "use_multi_db",
                }
                for field in preserve_graph_fields:
                    if field in existing_graph_config:
                        merged_graph_config[field] = existing_graph_config[field]
                        logger.debug(
                            f"Preserved graph_db field '{field}': {existing_graph_config[field]}"
                        )

                # Clean up backend-specific fields that don't exist in the new backend
                # This approach is generic: remove any field from merged config that's not in default config
                # and not in the preserve list
                fields_to_remove = []
                for field in list(merged_graph_config.keys()):
                    if field not in default_graph_config and field not in preserve_graph_fields:
                        fields_to_remove.append(field)

                for field in fields_to_remove:
                    removed_value = merged_graph_config.pop(field)
                    logger.info(
                        f"Removed {existing_backend}-specific field '{field}' (value: {removed_value}) "
                        f"during migration to {default_backend}"
                    )
            else:
                # Same backend: merge configs while preserving user-specific fields
                logger.debug(f"Same graph_db backend ({default_backend}), merging configurations")
                preserve_graph_fields = {
                    "auto_create",
                    "user_name",
                    "use_multi_db",
                }

                # Start with existing config as base
                merged_graph_config = copy.deepcopy(existing_graph_config)

                # Update with default config except preserved fields
                for key, value in default_graph_config.items():
                    if key not in preserve_graph_fields:
                        merged_graph_config[key] = value
                        logger.debug(
                            f"Updated graph_db field '{key}': {existing_graph_config.get(key)} -> {value}"
                        )

                # Handle use_multi_db transition
                if not default_graph_config.get("use_multi_db", True) and merged_graph_config.get(
                    "use_multi_db", True
                ):
                    merged_graph_config["use_multi_db"] = False
                    # For Neo4j: db_name becomes user_name in single-db mode
                    if "neo4j" in default_backend and "db_name" in merged_graph_config:
                        merged_graph_config["user_name"] = merged_graph_config.get("db_name")
                        merged_graph_config["db_name"] = default_graph_config.get("db_name")
                    logger.info("Transitioned to single-db mode (use_multi_db=False)")

            preserved_graph_db = {
                "backend": default_backend,
                "config": merged_graph_config,
            }

    # Use default config as base
    merged_dict = copy.deepcopy(default_dict)

    # Restore preserved fields from existing config
    for field in preserve_fields:
        if field in existing_dict:
            merged_dict[field] = existing_dict[field]
            logger.debug(f"Preserved field '{field}': {existing_dict[field]}")

    # Restore graph_db if it was preserved
    if preserved_graph_db and "text_mem" in merged_dict:
        merged_dict["text_mem"]["config"]["graph_db"] = preserved_graph_db
        logger.debug(f"Preserved graph_db with merged config: {preserved_graph_db}")

    # Create new config from merged dictionary
    merged_config = GeneralMemCubeConfig.model_validate(merged_dict)

    logger.info(
        f"Successfully merged cube config for user {merged_config.user_id}, cube {merged_config.cube_id}"
    )

    return merged_config
