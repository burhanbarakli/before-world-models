# Before adding a world model

**Read the write-up:** [English](https://burhanbarakli.github.io/before-world-models/) ·
[Türkçe](https://burhanbarakli.github.io/before-world-models/tr/)

We wanted to add a world model on top of BCSDM (Lee et al., *IEEE Transactions on Robotics*, 2026), a method that
learns stable robot motion from demonstrations. Before training any model, every experiment measured the gap
between a simple hand-made rule and an oracle that knows the true state. In six experiments (more than 600,000
PyBullet runs with a simulated Franka Panda), a rule of a few lines took almost all of what a model could gain. The
one open case is a poor wrist force sensor, or none.

This repository holds the write-up, and the protocols, code and results of every experiment.

## Layout

| Folder | Experiment |
|---|---|
| [`docs/`](docs/) | The write-up (GitHub Pages): `index.md` English, `tr/index.md` Turkish, `figures/` |
| [`toy_eta/`](toy_eta/) | Toy test: does a learned forward model choose η better than cheap alternatives? |
| [`s2_lasa/`](s2_lasa/) | Time-varying η on LASA mapped to S² (theory checks and a schedule test) |
| [`panda_gate1/`](panda_gate1/) | Panda under delay and lag: success vs η, the one-constant delay rule |
| [`panda_learned/`](panda_learned/) | Learned fields: the speed gate |
| [`panda_contact/`](panda_contact/) | Insertion with contact: spiral search vs knowing the hole position |
| [`panda_time/`](panda_time/) | Time to find the hole: moment rule vs oracle |
| [`panda_rival/`](panda_rival/) | A better hand-made rival (MOMENT-2) vs an oracle that knows the hole from the first touch |
| [`panda_sensor/`](panda_sensor/) | Realistic wrist force/torque sensor errors |
| [`panda_tare/`](panda_tare/) | Re-zeroing the sensor just before contact |

Each folder has a `PROTOKOL.md`, written before its main run, with a "Sapmalar" (deviations) section at the end, and
a `README.md` with the results. These are in Turkish; the write-up in `docs/` is in English and Turkish.

## Checkpoints

The trained BCSDM vector fields (four networks, about 14 MB each) are in
[`panda_learned/models/`](panda_learned/models/), with a README on their contents and how to load them. They are the
only trained networks of the study; no world model was trained.

## Running

The PyBullet experiments use Python 3.11 with `numpy`, `scipy` and `pybullet` (we used conda-forge pybullet 3.25).
Folders call `../.pbenv/bin/python`; create an environment there or edit the run scripts. Audit scripts under
`*/audit*/` were one-off checks and expect to be run from the repository root. Figures for the write-up:
`python docs/figures/make_figures.py` (needs `numpy` and `matplotlib`).

The holder geometry and the demonstrations of the paper are not published, so the task is our own reconstruction
and the numbers are not directly comparable with the paper's.
