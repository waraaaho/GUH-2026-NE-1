#!/usr/bin/env bash
set -e

# Restartable one-command launcher for the local Chrome replay workbench.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

PORT="${1:-8000}"
echo "Starting Resilient SAR Chrome Replay Workbench on http://127.0.0.1:${PORT} ..."
exec python3 -m sar_swarm.demo_sim --serve --port "$PORT"
