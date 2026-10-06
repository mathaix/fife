#!/usr/bin/env bash
# Smoke-run every demo end to end. Demo 07 needs ANTHROPIC_API_KEY.
set -euo pipefail
cd "$(dirname "$0")"
python demos/prewarm.py
python demos/01_hello.py
python demos/02_your_data.py
python demos/03_isolation.py
echo | python demos/04_tunnel.py
python demos/05_fan_out.py
python demos/06_snapshots.py
python demos/07_ai_interpreter.py
