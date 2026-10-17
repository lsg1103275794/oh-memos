# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="oh-memos" \
      org.opencontainers.image.description="Persistent project memory API for AI assistants" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MEMOS_BASE_PATH=/data/runtime \
    MEMOS_CUBES_DIR=/data/cubes \
    MOS_CUBE_PATH=/data/cubes \
    HF_HOME=/data/runtime/huggingface

WORKDIR /app

RUN groupadd --gid 10001 memos \
    && useradd --uid 10001 --gid memos --create-home --shell /usr/sbin/nologin memos

COPY docker/requirements.txt /tmp/requirements.txt
# No torch: every model backend this image serves is a remote API (see requirements.txt).
RUN pip install -r /tmp/requirements.txt

COPY pyproject.toml README.md ./
# Only the package itself. A bare `COPY src ./src` would also drag in the
# developer's src/.env, src/logs/ and src/bin/ (a ~2GB local runtime).
COPY src/oh_memos ./src/oh_memos
# MEMOS_BASE_PATH must already point at a writable path here: oh_memos/log.py
# creates its log file at import time, and /app belongs to root.
RUN mkdir -p /data/cubes /data/runtime \
    && chown -R memos:memos /data \
    && pip install --no-deps . \
    && python -m pip check \
    && python -c "import importlib.util; assert importlib.util.find_spec('torch') is None, 'torch must not be installed'; from oh_memos.api.start_api import app; from oh_memos.configs import llm_defaults; assert llm_defaults.chat_model() == '', 'build image must not carry a baked-in model name'" \
    && ! python -m pip list --format=freeze | grep -E '^(nvidia-|triton==|torch[a-z]*==)' \
    && rm -rf /data/runtime/* /data/runtime/.[!.]*

COPY docker/dev_cube.config.template /opt/oh-memos/dev_cube.config.template
COPY docker/entrypoint.sh /usr/local/bin/oh-memos-entrypoint
RUN chmod 0555 /usr/local/bin/oh-memos-entrypoint \
    && chown -R memos:memos /data

USER memos
EXPOSE 18000

ENTRYPOINT ["/usr/local/bin/oh-memos-entrypoint"]
CMD ["python", "-m", "uvicorn", "oh_memos.api.start_api:app", "--host", "0.0.0.0", "--port", "18000"]
