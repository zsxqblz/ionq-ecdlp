#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3.12 -m venv .venv-reconstruction
.venv-reconstruction/bin/pip install -r requirements-reconstruction.txt
mkdir -p .deps
curl --fail --location 'https://gitlab.inria.fr/capsule/qarton/-/archive/4fdcf6961ad45104a460e5f54d587a6776a73461/qarton.zip?path=qarton' -o .deps/qarton.zip
.venv-reconstruction/bin/python -m zipfile -e .deps/qarton.zip .deps
