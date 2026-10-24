#!/bin/bash
set -euo pipefail

# Only run in Claude Code cloud sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

export PATH="$HOME/.local/bin:$PATH"
if ! command -v poetry >/dev/null 2>&1; then
  python3 -m pip install --user --quiet poetry
fi

# Keep the virtualenv inside the project so it is cached with the container
export POETRY_VIRTUALENVS_IN_PROJECT=true
poetry install --no-interaction

# Sanity check: the wemake-python-styleguide flake8 plugin is installed
poetry run python -c "import wemake_python_styleguide"

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"$PWD/.venv/bin:$HOME/.local/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi
