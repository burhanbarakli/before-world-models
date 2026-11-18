import sys,itertools
sys.dont_write_bytecode=True
sys.path.insert(0,"./panda_gate1")
import numpy as np, gate_rule as GR, robot as Rb
part,n,out=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
rb=Rb.Panda(); rows=[]
items=list(itertools.product(range(3),range(4),range(3),range(5),range(10)))
for it,(iT,ih,il,ho,ie) in enumerate(items):
    if it%n!=part: continue
    T,h,tau=GR.PERIOD[iT],GR.DELAY[ih],GR.LAG[il]
    eta=GR.rule(h,tau) if ie==9 else GR.ETA[ie]
    ref=Rb.reference_for(rb,GR.HOLES[ho],T)
    r=Rb.run(rb,ref,GR.HOLES[ho],eta,h,tau,None,tf=T+4.0)
    rows.append((iT,ih,il,ho,ie,np.nan if r['t_rim'] is None else r['t_rim'],r['lat'],r['tilt'],r['end_z'],ref.dt*GR.Gg.rim_index(ref)))
    if len(rows)%100==0: np.save(out,np.array(rows)); print(it,flush=True)
np.save(out,np.array(rows))
