#!/bin/zsh
# Waits for train_all.sh, then the field errors, the speed-gate experiment and its analysis.
SP="${SP:?set SP to a scratch directory holding the pbenv/ and venv/ Python environments}"
PY="$SP/pbenv/bin/python"
cd "$(dirname "$0")"
while pgrep -f "train_all.sh" >/dev/null; do sleep 30; done
[ -f models/model3.npz ] || { echo "training stopped without model 3"; exit 1; }
for m in 0 1 2 3; do OMP_NUM_THREADS=8 VECLIB_MAXIMUM_THREADS=8 "$PY" field_error.py models/model$m.npz; done > results/field_error.txt 2>&1 || exit 1
"$PY" gate_speed.py > results/gate_speed.log 2>&1 || { echo "gate_speed failed"; exit 1; }
"$PY" analyze_speed.py > results/analysis_speed.txt 2>&1 || { echo "analyze_speed failed"; exit 1; }
echo finished
