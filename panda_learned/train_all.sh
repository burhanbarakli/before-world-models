#!/bin/zsh
# seed steps: three paper-recipe models and one weak model, each on its own data.
SP="${SP:?set SP to a scratch directory holding the pbenv/ and venv/ Python environments}"
cd "$(dirname "$0")"
for pair in "1 20000" "2 20000" "3 4000"; do
  set -- ${=pair}
  [ -f models/model$1.npz ] && continue
  OMP_NUM_THREADS=8 VECLIB_MAXIMUM_THREADS=8 "$SP/pbenv/bin/python" make_data.py $1 1000000 "$SP/learned/train$1.npz" || exit 1
  "$SP/venv/bin/python" train_field.py $1 $2 "$SP/learned/train$1.npz" models/model$1.npz 512 > results/model$1.log 2>&1 || exit 1
  rm "$SP/learned/train$1.npz"
done
echo done
