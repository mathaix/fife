#!/usr/bin/env bash
# Smoke-run the Act 1 and Act 2 demos. Act 3 (the issue agent) is driven by GitHub issues: see README.
set -euo pipefail
cd "$(dirname "$0")"
python demos/act1_hello.py
python demos/act2_isolation.py
python demos/act2_snapshots.py
