#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    echo "Не найдено локальное Python-окружение .venv."
    exit 1
fi

osascript - "$PROJECT_DIR" "$PYTHON" <<'APPLESCRIPT'
on run arguments
    set projectDir to item 1 of arguments
    set pythonPath to item 2 of arguments
    tell application "Terminal"
        activate
        do script "cd " & quoted form of projectDir & " && " & quoted form of pythonPath & " -m profi_order_monitor.browser.downloader"
        do script "cd " & quoted form of projectDir & " && " & quoted form of pythonPath & " -m profi_order_monitor.monitor"
    end tell
end run
APPLESCRIPT
