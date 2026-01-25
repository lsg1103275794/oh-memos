import copy
import logging
import os
import platform
import re
import subprocess
import tempfile

from memos.configs.mem_cube import GeneralMemCubeConfig


logger = logging.getLogger(__name__)


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
            with open('/etc/os-release', 'r') as f:
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
                with open('/proc/version', 'r') as f:
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
