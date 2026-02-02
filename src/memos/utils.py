import functools
import time
import traceback

from memos.log import get_logger


logger = get_logger(__name__)


def timed_with_status(
    func=None,
    *,
    log_prefix="",
    log_args=None,
    log_extra_args=None,
    fallback=None,
):
    """
    Parameters:
    - log: enable timing logs (default True)
    - log_prefix: prefix; falls back to function name
    - log_args: names to include in logs (str or list/tuple of str), values are taken from kwargs by name.
    - log_extra_args:
        - can be a dict: fixed contextual fields that are always attached to logs;
        - or a callable: like `fn(*args, **kwargs) -> dict`, used to dynamically generate contextual fields at runtime.
    """

    if isinstance(log_args, str):
        effective_log_args = [log_args]
    else:
        effective_log_args = list(log_args) if log_args else []

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            exc_type = None
            exc_message = None
            result = None
            success_flag = False

            try:
                result = fn(*args, **kwargs)
                success_flag = True
                return result
            except Exception as e:
                exc_type = type(e)
                stack_info = "".join(traceback.format_stack()[:-1])
                exc_message = f"{stack_info}{traceback.format_exc()}"
                success_flag = False

                if fallback is not None and callable(fallback):
                    result = fallback(e, *args, **kwargs)
                    return result
                else:
                    raise
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000.0

                ctx_parts = []
                # 1) Collect parameters from kwargs by name
                for key in effective_log_args:
                    val = kwargs.get(key)
                    ctx_parts.append(f"{key}={val}")

                # 2) Support log_extra_args as dict or callable, so we can dynamically
                #    extract values from self or other runtime context
                extra_items = {}
                try:
                    if callable(log_extra_args):
                        extra_items = log_extra_args(*args, **kwargs) or {}
                    elif isinstance(log_extra_args, dict):
                        extra_items = log_extra_args
                except Exception as e:
                    logger.warning(f"[TIMER_WITH_STATUS] log_extra_args callback error: {e!r}")

                if extra_items:
                    ctx_parts.extend(f"{key}={val}" for key, val in extra_items.items())

                ctx_str = f" [{', '.join(ctx_parts)}]" if ctx_parts else ""

                status = "SUCCESS" if success_flag else "FAILED"
                status_info = f", status: {status}"
                if not success_flag and exc_type is not None:
                    status_info += (
                        f", error_type: {exc_type.__name__}, error_message: {exc_message}"
                    )

                msg = (
                    f"[TIMER_WITH_STATUS] {log_prefix or fn.__name__} "
                    f"took {elapsed_ms:.0f} ms{status_info}, args: {ctx_str}"
                )

                logger.info(msg)

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


def timed(func=None, *, log=True, log_prefix=""):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            if log is not True:
                return result

            # 100ms threshold
            if elapsed_ms >= 100.0:
                logger.info(f"[TIMER] {log_prefix or fn.__name__} took {elapsed_ms:.0f} ms")

            return result

        return wrapper

    # Handle both @timed and @timed(log=True) cases
    if func is None:
        return decorator
    return decorator(func)


# Sensitive field names to mask in logs
SENSITIVE_FIELDS = frozenset({
    "api_key", "api-key", "apikey",
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token",
    "secret", "secret_key", "client_secret",
    "authorization", "auth",
    "credential", "credentials",
    "private_key", "privatekey",
})


def mask_sensitive_value(value: str, visible_chars: int = 4) -> str:
    """Mask a sensitive value, showing only the first few characters."""
    if not value or len(value) <= visible_chars:
        return "***"
    return f"{value[:visible_chars]}***"


def mask_sensitive_config(config, _seen: set | None = None) -> str:
    """
    Convert a config object to string with sensitive fields masked.

    Handles Pydantic models, dicts, and other objects.
    Masks fields like api_key, password, token, secret, etc.

    Args:
        config: Config object (Pydantic model, dict, or any object)
        _seen: Internal set to track seen objects and prevent infinite recursion

    Returns:
        String representation with sensitive values masked
    """
    if _seen is None:
        _seen = set()

    # Prevent infinite recursion
    obj_id = id(config)
    if obj_id in _seen:
        return "..."
    _seen.add(obj_id)

    try:
        # Handle None
        if config is None:
            return "None"

        # Handle Pydantic models
        if hasattr(config, "model_dump"):
            data = config.model_dump()
        elif hasattr(config, "dict"):
            data = config.dict()
        elif isinstance(config, dict):
            data = config
        else:
            # For other objects, try to get __dict__ or just str()
            if hasattr(config, "__dict__"):
                data = vars(config)
            else:
                return str(config)

        # Mask sensitive fields
        masked_data = _mask_dict_recursive(data, _seen)
        return str(masked_data)

    except Exception:
        # Fallback: just return type name
        return f"<{type(config).__name__}>"


def _mask_dict_recursive(data: dict, _seen: set) -> dict:
    """Recursively mask sensitive fields in a dict."""
    masked = {}
    for key, value in data.items():
        key_lower = key.lower().replace("_", "").replace("-", "")

        # Check if this is a sensitive field
        is_sensitive = any(
            s.replace("_", "").replace("-", "") in key_lower
            for s in SENSITIVE_FIELDS
        )

        if is_sensitive and isinstance(value, str) and value:
            masked[key] = mask_sensitive_value(value)
        elif isinstance(value, dict):
            masked[key] = _mask_dict_recursive(value, _seen)
        elif isinstance(value, list):
            masked[key] = [
                _mask_dict_recursive(item, _seen) if isinstance(item, dict) else item
                for item in value
            ]
        elif hasattr(value, "model_dump") or hasattr(value, "dict"):
            # Nested Pydantic model
            masked[key] = mask_sensitive_config(value, _seen)
        else:
            masked[key] = value

    return masked
