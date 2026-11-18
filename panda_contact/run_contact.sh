#!/bin/zsh
# The main contact run, then the pre-registered analysis.
cd "$(dirname "$0")"
PY=../.pbenv/bin/python
$PY exp_contact.py 2>&1 | grep -v "pybullet build" > results/exp_contact.log &&
$PY analyze_contact.py > results/analysis_contact.txt 2>&1 &&
echo finished
