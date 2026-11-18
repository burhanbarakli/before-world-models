#!/bin/bash
cd "$(dirname "$0")"
PY="../.pbenv/bin/python"
"$PY" tare.py >> results/tare.log 2>&1 && "$PY" analyze_tare.py > results/analysis_tare.txt 2>&1 && echo finished
