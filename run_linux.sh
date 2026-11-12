#!/usr/bin/env bash
# ===========================================================================================
#  OoT Remake Randomizer - start the generator on Linux
#
#  Run:   ./run_linux.sh   (or: bash run_linux.sh)
#  Uses the private environment that setup_linux.sh made in ".venv". If it's missing, or a package
#  is missing (for example after downloading a new version), it installs them first.
# ===========================================================================================
set -u
cd "$(dirname "$(readlink -f "$0")")" || exit 1
VENV="$PWD/.venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "First start: running the setup..."
    bash ./setup_linux.sh || exit 1
fi

# the packages the randomizer imports when it starts
if ! "$VENV/bin/python" -c 'import raven, openpyxl' >/dev/null 2>&1; then
    echo "Installing missing packages from requirements.txt..."
    "$VENV/bin/python" -m pip install --upgrade -r requirements.txt || {
        echo "Installing the packages failed. The messages above say why."; exit 1; }
fi

exec "$VENV/bin/python" ootr_remake.pyw "$@"
