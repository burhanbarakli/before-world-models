# rule rerun with disturbance time taken from the undisturbed t_rim of the TABLE eta of that cell (test seeds only)
import sys,itertools,multiprocessing as mp
sys.dont_write_bytecode=True
sys.path.insert(0,"./panda_gate1")
sys.path.insert(0,sys.argv[1] if len(sys.argv)>1 else '.')
import numpy as np, gate_rule as GR, gate1 as G, gate1g as Gg, robot as Rb
from lib import ok,D,scoreM
R=np.concatenate([np.load('trim0.npy'),np.load('trim1.npy')])
t=np.full((3,4,3,5,10),np.nan)
for r in R: t[tuple(int(x) for x in r[:5])]=r[5]
o=ok(D,.005).astype(float); tab=scoreM(o[...,:10].mean((5,6)),o[...,10:].mean((5,6)))['tab']
rb=None
def f(c):
    global rb
    if rb is None: rb=Rb.Panda()
    iT,ih,il,ig=c; T,h,tau,gap=GR.PERIOD[iT],GR.DELAY[ih],GR.LAG[il],GR.GAP[ig]
    eta=GR.rule(h,tau); out=np.zeros((5,10,5))
    for ho,hole in enumerate(GR.HOLES):
        ref=Rb.reference_for(rb,hole,T); td=t[iT,ih,il,ho,tab[iT,ih,il]]-gap
        for s in range(10,20):
            w,v=GR.draw(rb,ref,ho,s,gap); r=Rb.run(rb,ref,hole,eta,h,tau,(td,w,v),tf=T+4.0)
            out[ho,s-10]=[r[x] for x in G.KEYS]
    return out
if __name__=="__main__":
    cells=list(itertools.product(range(3),range(4),range(3),range(2)))
    with mp.Pool(4) as p:
        res=[]
        for i,r in enumerate(p.imap(f,cells,chunksize=1)):
            res.append(r); print(i,flush=True)
    np.savez('tshared.npz',res=np.array(res).reshape(3,4,3,2,5,10,5))
