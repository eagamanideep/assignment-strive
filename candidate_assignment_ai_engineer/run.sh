#!/usr/bin/env bash
# One-step setup + launch for macOS / Linux. Usage: ./run.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi

.venv/bin/python -m streamlit run app.py
