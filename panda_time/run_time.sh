#!/bin/sh
# Main run of PROTOKOL.md: setting A, then B, then the analysis.
cd "$(dirname "$0")"
PY=../.pbenv/bin/python
$PY exp_time.py A > results/exp_time_A.log 2>&1 || exit 1
$PY exp_time.py B > results/exp_time_B.log 2>&1 || exit 1
$PY analyze_time.py > results/analysis_time.txt 2>&1
echo finished
