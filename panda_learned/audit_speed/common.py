"""Independent loader and scorer. Nothing imported from analyze_speed/analyze_g."""
import numpy as np
ROOT="."
NPZ=ROOT+"/panda_learned/results/gate_speed.npz"
ARMS=["m0","m1","m2","weak","analytic"]; PERIOD=[8.,4.]; DELAY=[.02,.04,.07,.09]; LAG=[0.,.025,.04]; GAP=[.4,.25]
OPT=["none",.01,.02,.04,.08]; HOLES=5; SEEDS=20
RIM=.25; DEPTH=.06
def load():
    z=np.load(NPZ); return z["data"],z["und"],[str(k) for k in z["keys"]]
def succ(a,keys,c=.005):
    lat=a[...,keys.index("lat")]; tilt=a[...,keys.index("tilt")]; ez=a[...,keys.index("end_z")]
    return (RIM-ez>=.9*DEPTH)&(lat<=c)&(tilt<=np.arctan(2*c/DEPTH))
# axes of ok[arm]: model,T,h,tau,gap,opt,hole,seed
def policy(sel,te):
    """sel,te: (M,T,h,tau,gap,opt,hole,seed) booleans. returns KURAL,KAPI0,TABLOK,ORACLE"""
    S=te.mean(axis=(0,1,2,3,4,6,7))
    rate=sel.astype(float).mean(axis=(4,6,7))      # M,T,h,tau,opt
    best=rate.argmax(-1)
    teopt=te.astype(float).mean(axis=(4,6,7))      # M,T,h,tau,opt
    tab=np.take_along_axis(teopt,best[...,None],-1).mean()
    return S[0],S[2],tab,te.any(axis=5).mean()
