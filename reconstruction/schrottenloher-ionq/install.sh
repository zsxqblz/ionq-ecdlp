#!/usr/bin/env bash
set -euo pipefail

# -------- Configuration --------
# This is the required version of python.
PYTHON=python3.12
# This URL is a specific commit for Qarton, which corresponds to the
# 0.2.1 version 
URL="https://gitlab.inria.fr/capsule/qarton/-/archive/4fdcf6961ad45104a460e5f54d587a6776a73461/qarton-4fdcf6961ad45104a460e5f54d587a6776a73461.zip"
ARCHIVE="qarton-4fdcf6961ad45104a460e5f54d587a6776a73461.zip"
SRC_DIR="qarton-4fdcf6961ad45104a460e5f54d587a6776a73461"
VENV_DIR=".venv-qarton"
TMP_DIR="$(mktemp -d)"

# -------- Cleanup on exit --------
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# -------- Create virtual environment --------
echo "Creating virtual environment with $PYTHON"
$PYTHON -m venv "$VENV_DIR"

# Activate venv
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Upgrade pip tools
pip install --upgrade pip setuptools wheel

# -------- Download archive --------
echo "Downloading qarton archive..."
cd "$TMP_DIR"
curl -L -o "$ARCHIVE" "$URL"

# -------- Decompress --------
echo "Extracting archive..."
unzip -q "$ARCHIVE"

# -------- Install --------
echo "Installing qarton..."
cd "$SRC_DIR"
pip install .

# --------- Additional imports ----------
pip install matplotlib
pip install pytest

echo
echo "qarton installed successfully in virtual environment: $VENV_DIR"
echo "Activate it with: source $VENV_DIR/bin/activate"
