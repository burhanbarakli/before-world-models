# toy_eta: does a learned forward model select BCSDM's eta better than cheap alternatives?

Analytic field only (no neural field): GVF(x; eta) = MVF(x) + eta CVF(x) in R^2, clipped at Vmax.

## Run

    python sim.py test                       # sanity tests
    python sim.py stability                  # question 2
    python sim.py sweep --n 30               # question 1
    python sim.py run --seeds 4 --n 9        # main experiment, tables.npz
    python analyze.py                        # regret.csv, regret_by_family.csv, paired.csv,
                                             # prediction_error.csv, schedule_regret.csv

Needs numpy and torch (CPU). Everything is seeded (`--seed`).

## Setup as run

- Demos: 3 curves (S, spiral arc, wave), arc length 2 m, 200 points, peak speed 0.6 m/s, 4.5 s,
  terminal speed 0. dt = 0.02 s, Vmax = 1.2 m/s, horizon 350 steps (7 s).
- Starts: within the first 5% of the demo, offset 0.15-0.30 m to either side.
- Gate: on the demo at 45-75% of arc length, half width 2.5 cm. Goal radius 3 cm.
- Cost, lower is better, weights fixed before any selector was run:
  J = 2.0 S + 1.0 G + 1.0 R + 0.1 U
  - S: path-length-weighted 1 - cos(angle between displacement and demo tangent at x*), over
    4-step displacements. The paper's mimicking definition. The late cut at low eta and the early
    jump at high eta both cost.
  - G: gate miss, 0 if passed, otherwise 0.5 to 1 with lateral miss distance.
  - R: goal miss on the last 10 steps, same form.
  - U: log(1 + command total variation / demo velocity total variation).
- Plant: x+ = x + dt (a+ + drift(x) + noise), a+ = a + alpha (k softthresh(u_{t-d}, delta) - a).
  Actuator noise 0.01 m/s, sensor noise 0.2 mm, always on.
  Families, 8: ideal, delay (h 0.02-0.2 s), lag (T 0.03-0.3 s), gain (k 0.7-1.25),
  friction (per-axis Coulomb-like delta 0.02-0.08 m/s), drift (sinusoidal field, 0.03-0.1 m/s),
  delay+lag, all five.
- Candidates: eta = 0.25 ... 64, 9 values, factor 2.
- Score table on the true plant: 6 starts per candidate, one noise draw each. Regret is measured
  on this table, so F has zero regret by construction.

## Selectors

- A_ideal: best single eta on the ideal family, from other seeds. A_pop: same over all families.
  This one is an addition: it asks whether per-plant selection is needed at all.
- B: nominal kinematic rollouts.
- C: grey box. Grid over delay (0-12 steps), lag, deadzone; least squares for gain. No drift term.
- D: 3 MLPs, 2 hidden layers of 64, Gaussian NLL, bootstrap, early stopping, predicting velocity
  residual from the last 12 commands, last 2 velocities, position. Closed-loop rollout per member.
  D_pen: mean J + 1.0 std J across members. D_nopen: mean J.
- B, C, D score 6 simulated starts drawn from the same distribution as, but distinct from, the
  evaluation starts. They also simulate the sensor noise (assumed known), not the actuator noise.
- E_k: k candidates spaced on the grid, one real trial each, from one common start, 350
  transitions per trial. E_unpaired_k: a different start per trial. E_3starts_kx3: 3 common starts
  per candidate. E_hill_k: hill climb from A_ideal.
- F: oracle.

Excitation log: field rollouts with eta cycling through 1, 4, 16, 2, 8, 0.5, plus 0.03 m/s white
command noise. 200 transitions = 3 episodes of 66 steps; 1000 = 3 of 333; 5000 = 15 of 333.

## Post-hoc addition

C+ (`python sim.py cplus --seeds 4 --n 9`): C plus a ridge fit of a 5x5 RBF map from position to
velocity bias, lambda = 1, first setting tried. Added after the main results showed that D's lead
over C sits in the drift plants. Same plants and true-score tables, fresh logs. It was not in the
design, and it was built knowing the drift depends on position only.

## Results

Full output: `results/analysis.txt`. Tables: `results/regret.csv`, `regret_by_family.csv`,
`paired.csv`, `prediction_error.csv`, `schedule_regret.csv`, `stability.json`, `sweep.json`.
Raw per-instance tables: `results/tables.npz`, `results/cplus.npz`. 288 instances
(8 families x 9 x 4 seeds).

Changes made along the way:

- Decay sanity test moved to a straight demo. On curves Euler steps leave a 1.5-6.5 mm floor.
- Hidden size 96 to 64, and coarse-to-fine nearest-point search, both for speed. The search is off
  by up to 9 mm on 0.1-0.2% of random points, near the medial axis.
- Coordinate-search infinite loop in analyze.py fixed on the pilot, before the full run.
- Multi-start and unpaired E variants added after a 24-instance pilot showed E getting no better
  with more trials. The cause is overfitting to its single trial start.
- Stability onset uses command total variation. A distance threshold would flag bend tracking
  error. This criterion also flags ringing, so lag-only onsets are not instability.
