#!/bin/sh
# Main run of PROTOKOL.md, then the analysis.
cd "$(dirname "$0")"
PY=../.pbenv/bin/python
$PY rival.py > results/rival.log 2>&1 || exit 1
$PY analyze_rival.py > results/analysis_rival.txt 2>&1
echo finished
