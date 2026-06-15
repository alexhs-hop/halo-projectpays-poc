FROM python:3.11-slim-bookworm

RUN pip install --no-cache-dir nibabel "numpy>=2.0" scipy

# Install Node.js + pre-bake @anthropic-ai/claude-code so Harbor agent setup
# uses the fast `npm install -g` path instead of the slow curl/Rust installer.
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && \
    npm install -g @anthropic-ai/claude-code && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a minimal stub for `apk` (Alpine package manager) so Harbor's
# claude-code installer detects it and takes the npm path (fast) rather
# than the curl-based Rust-binary path (slow, times out).
RUN printf '#!/bin/sh\nexit 0\n' > /usr/local/bin/apk && chmod +x /usr/local/bin/apk

# Create an npm wrapper to bypass active network installation of claude-code during agent startup.
RUN printf '%s\n' \
    '#!/bin/sh' \
    'case "$*" in' \
    '  *install*claude-code*)' \
    '    echo "Mocked npm: @anthropic-ai/claude-code is already pre-installed in the Docker image. Skipping network download."' \
    '    exit 0' \
    '    ;;' \
    '  *)' \
    '    exec /usr/bin/npm "$@"' \
    '    ;;' \
    'esac' \
    > /usr/local/bin/npm && chmod +x /usr/local/bin/npm

WORKDIR /app

COPY data /app/data
