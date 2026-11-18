# exact replay of hole 3 seed 13 (and hole 1 seed 2) for the rule index in EVERY cell, plus grid eta 12 sample
import sys,itertools
sys.dont_write_bytecode=True
sys.path.insert(0,"./panda_gate1")
import numpy as np, gate_rule as GR, gate1 as G, gate1g as Gg, robot as Rb
D=np.load("./panda_gate1/results/gate_rule.npz")['data']
part,n=int(sys.argv[1]),int(sys.argv[2])
rb=Rb.Panda(); bad=0;tot=0
items=list(itertools.product(range(3),range(4),range(3),range(2),[9,6]))
for it,(iT,ih,il,ig,ie) in enumerate(items):
    if it%n!=part: continue
    T,h,tau,gap=GR.PERIOD[iT],GR.DELAY[ih],GR.LAG[il],GR.GAP[ig]
    eta=GR.rule(h,tau) if ie==9 else GR.ETA[ie]
    for ho,s in ((3,13),(1,2)):
        hole=GR.HOLES[ho]; ref=Rb.reference_for(rb,hole,T)
        t_rim=Rb.run(rb,ref,hole,eta,h,tau,None,tf=T+4.0)["t_rim"]
        t_d=(ref.dt*Gg.rim_index(ref)+h+tau if t_rim is None else t_rim)-gap
        w,v=GR.draw(rb,ref,ho,s,gap)
        r=Rb.run(rb,ref,hole,eta,h,tau,(t_d,w,v),tf=T+4.0)
        x=np.array([r[k] for k in G.KEYS]); st=D[iT,ih,il,ig,ie,ho,s]
        tot+=1
        if not np.array_equal(x,st):
            bad+=1; print('MISMATCH',T,h,tau,gap,ie,ho,s,np.abs(x-st).max(),flush=True)
print('replayed',tot,'mismatches',bad,flush=True)
