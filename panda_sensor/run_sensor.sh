#!/bin/sh
# Main run of PROTOKOL.md, then the analysis. Start detached: nohup caffeinate -ims ./run_sensor.sh > results/run_sensor.out 2>&1 &
# A rerun resumes from results/sensor.npz.partial.pkl.
cd "$(dirname "$0")"
PY=../.pbenv/bin/python
$PY sensor.py >> results/sensor.log 2>&1 || exit 1
$PY analyze_sensor.py > results/analysis_sensor.txt 2>&1
echo finished
