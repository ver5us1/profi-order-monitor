#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m venv "$PROJECT_DIR/.venv"
PYTHON="$PROJECT_DIR/.venv/bin/python"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e "$PROJECT_DIR"
"$PYTHON" -m playwright install chromium

echo "Окружение подготовлено. Личные параметры хранятся в .env."
