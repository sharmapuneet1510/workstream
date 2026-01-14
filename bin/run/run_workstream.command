#!/bin/bash
set -e
cd "$(dirname "$0")"

# Use .venv if present; otherwise run system python
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

export PYTHONPATH="src"
python3 src/desktop_main.py