"""DeepOVec for the CVF and MVF, in the implicit representation (R, p), output projected on T_x SE(3).

Run: python train_field.py seed steps data.npz out.npz [width]    (venv with torch)
"""
import sys
import time

import numpy as np
import torch
import torch.nn as nn

WIDTH, DEPTH, DIM = 1024, 6, 64
NOUT = 12  # ambient: 9 for R, 3 for p
BATCH, DEMO = 2048, 256
LR = 3e-4
P0, PS = np.array([0.4, 0.0, 0.3], np.float32), 0.2


def mlp(n_in, n_out):
    layers, n = [], n_in
    for _ in range(DEPTH):
        layers += [nn.Linear(n, WIDTH), nn.ReLU()]
        n = WIDTH
    return nn.Sequential(*layers, nn.Linear(n, n_out))


def encode(x):
    return torch.cat([x[..., :9], (x[..., 9:] - x.new_tensor(P0)) / PS], -1)


class DeepOVec(nn.Module):
    def __init__(self, n_branch):
        super().__init__()
        self.branch, self.trunk = mlp(n_branch, DIM * NOUT), mlp(12, DIM * NOUT)

    def forward(self, x, B):
        """x: (n, 12), B: (n, DIM, NOUT). Returns the (w, v) twist."""
        t = self.trunk(encode(x)).view(-1, DIM, NOUT)
        y = (B * t).sum(1)
        R = x[:, :9].view(-1, 3, 3)
        S = R.transpose(1, 2) @ y[:, :9].view(-1, 3, 3)
        S = (S - S.transpose(1, 2)) / 2
        return torch.cat([torch.stack([S[:, 2, 1], S[:, 0, 2], S[:, 1, 0]], 1), y[:, 9:]], 1)


def loss_fn(f, g):
    e = f - g
    return (2 * e[:, :3].pow(2).sum(1) + 100 * e[:, 3:].pow(2).sum(1)).mean()


def main(seed, steps, data, out):
    torch.manual_seed(seed)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    d = np.load(data)
    x, c, m, hole = (torch.from_numpy(d[k]).to(dev) for k in ["x", "c", "m", "hole"])
    hole = hole.long()
    Xd = torch.from_numpy(d["Xd"]).to(dev)
    demo_m, demo_c = torch.from_numpy(d["demo_m"]).to(dev), torch.from_numpy(d["demo_c"]).to(dev)
    H, N = Xd.shape[:2]
    Xe = encode(Xd).reshape(H, -1)
    nets = {"c": DeepOVec(Xe.shape[1]).to(dev), "m": DeepOVec(Xe.shape[1]).to(dev)}
    params = list(nets["c"].parameters()) + list(nets["m"].parameters())
    print("params", sum(p.numel() for p in params), "device", dev, flush=True)
    opt = torch.optim.Adam(params, lr=LR)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, steps, eta_min=1e-6)
    t0 = time.time()
    n = len(x)
    gen = torch.Generator().manual_seed(seed)
    for k in range(steps):
        i = torch.randint(n, (BATCH,), generator=gen).to(dev)
        di = torch.randint(H * N, (DEMO,), generator=gen).to(dev)
        dh, dn = di // N, di % N
        xb = torch.cat([x[i], Xd[dh, dn]])
        hb = torch.cat([hole[i], dh])
        loss = 0.0
        vals = []
        for key, tgt, dt in [("c", c, demo_c), ("m", m, demo_m)]:
            net = nets[key]
            B = net.branch(Xe).view(H, DIM, NOUT)[hb]
            pred = net(xb, B)
            l = loss_fn(pred, torch.cat([tgt[i], dt[dh, dn]]))
            loss = loss + l
            vals.append(float(l.detach()))
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        if k % 2000 == 0 or k == steps - 1:
            print(k, f"c {vals[0]:.3e} m {vals[1]:.3e} t {time.time() - t0:.0f}", flush=True)
    res = {"Xd": d["Xd"]}
    with torch.no_grad():
        for key, net in nets.items():
            res[f"B_{key}"] = net.branch(Xe).view(H, DIM, NOUT).cpu().numpy()
            layers = [l for l in net.trunk if isinstance(l, nn.Linear)]
            for j, l in enumerate(layers):
                res[f"W_{key}{j}"] = l.weight.cpu().numpy()
                res[f"b_{key}{j}"] = l.bias.cpu().numpy()
    np.savez(out, **res)


if __name__ == "__main__":
    WIDTH = int(sys.argv[5]) if len(sys.argv) > 5 else WIDTH
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4])
