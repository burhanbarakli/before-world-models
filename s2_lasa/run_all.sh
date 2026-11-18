#!/bin/zsh
# Reruns everything in order. Usage: ./run_all.sh <python>
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
PY=$1
$PY test_gvf.py && $PY schedule.py > results/schedule.log 2>&1 && $PY analyze.py > results/analysis.txt 2>&1 \
  && $PY explore.py > results/explore.txt 2>&1 && $PY theory.py > results/theory.log 2>&1 && $PY t1b.py > results/t1b.log 2>&1
