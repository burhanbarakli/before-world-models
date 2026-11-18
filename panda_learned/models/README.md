# Learned BCSDM vector fields (checkpoints)

The four trained guiding-field networks used in the speed-gate experiment ([`../`](../)) and in every later Panda
experiment (`panda_contact`, `panda_time`, `panda_rival`, `panda_sensor`, `panda_tare`). They are the only trained
networks of this study; no world model was trained (see the [write-up](https://burhanbarakli.github.io/before-world-models/)).

| File | Training | Use |
|---|---|---|
| `model0.npz` | Paper recipe, 20,000 steps | Learned field, model 0 |
| `model1.npz` | Paper recipe, 20,000 steps, other seed and data | Learned field, model 1 |
| `model2.npz` | Paper recipe, 20,000 steps, other seed and data | Learned field, model 2 |
| `model3.npz` | Deliberately weak: 4,000 steps | Weak model (does a worse field change the decision?) |

Each file is about 14 MB.

## What is inside

Two networks per file, in NumPy arrays (float32): the contracting field (`c`) and the mimicking field (`m`), in the
DeepOVec form of the paper, on SE(3) in the implicit representation (rotation matrix `R` and position `p`).

| Key | Shape | Meaning |
|---|---|---|
| `W_c0 … W_c6`, `b_c0 … b_c6` | 6 hidden layers of 512 (ReLU), output 768 | Contracting-field network |
| `W_m0 … W_m6`, `b_m0 … b_m6` | same | Mimicking-field network |
| `B_c`, `B_m` | (5, 64, 12) | Per-hole basis: the output (64 × 12) is combined with it and projected on the tangent space of SE(3) |
| `Xd` | (5, 501, 12) | The five reference demonstrations (one per hole), 501 points, flattened `R` (9) and `p` (3) |

Input: flattened `R` (9 numbers) and `(p − [0.4, 0, 0.3]) / 0.2` (3 numbers).

## Loading

```python
import numpy as np
from learned import LearnedRef   # panda_learned/learned.py, NumPy only
# ref: a field_se3.Reference for the same hole (panda_gate1/field_se3.py)
field = LearnedRef(ref, "models/model0.npz", hole_i=0, T=8.0)
(cw, cv), (mw, mv), _, _ = field.field(R, p)   # contracting and mimicking parts as (angular, linear)
```

`learned.Net` shows the forward pass in plain NumPy.

## How they were made

- Data: `make_data.py` (1,000,000 samples per model, from the analytic field of `panda_gate1/field_se3.py`).
- Training: `train_field.py` (PyTorch), called by `train_all.sh` with width 512.
- Training logs: `../results/model0.log … model3.log`. Field errors: `../results/field_error.txt`.
- Error against the paper's sampling: c rms 0.118–0.122, m rms 0.022–0.023 for models 0–2; the weak model has about
  twice these.

The holder geometry and the demonstrations of the paper are not published, so these fields are trained on our own
reconstruction of the task and are not the paper's networks.
