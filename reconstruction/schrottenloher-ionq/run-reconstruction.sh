#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/.deps/qarton-4fdcf6961ad45104a460e5f54d587a6776a73461-qarton${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p results
exec .venv-reconstruction/bin/python -u -m "$@"
