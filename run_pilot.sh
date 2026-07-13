#!/usr/bin/env bash
# Usage: ANTHROPIC_API_KEY=sk-... ./run_pilot.sh [config]
set -euo pipefail
cd "$(dirname "$0")"
CFG="${1:-configs/pilot.json}"
python3 -m fmr.runner "$CFG"
OUT=$(python3 -c "import json;print(json.load(open('$CFG'))['out_dir'])")
python3 -m fmr.analyze "$OUT"
echo "Done. See $OUT/summary.json and $OUT/*.png"
