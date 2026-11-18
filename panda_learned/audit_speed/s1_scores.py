import numpy as np,sys
from common import *
D,U,K=load(); print("shape",D.shape,U.shape,K)
print("nan",np.isnan(D).sum(),np.isnan(U).sum())
for i,k in enumerate(K): print(k,D[...,i].min(),D[...,i].max())
print("und identical across options:",all((U[:,:,:,:,:,0]==U[:,:,:,:,:,o]).all() for o in range(1,5)))
for arm,idx in [("paper",[0,1,2]),("analytic",[4]),("weak",[3])]:
  ok=succ(D[idx],K)
  ks,g0,tab,orc=policy(ok[...,:10],ok[...,10:])
  print(f"{arm}: KURAL {ks:.4f} KAPI0 {g0:.4f} TABLOK {tab:.4f} ORACLE {orc:.4f}  H {g0-ks:.4f} P {tab-g0:.4f} Q {orc-g0:.4f}")
  print("  by option(test):",np.round(ok[...,10:].mean(axis=(0,1,2,3,4,6,7)),4))
  print("  by option(sel) :",np.round(ok[...,:10].mean(axis=(0,1,2,3,4,6,7)),4))
print("und KURAL",{a:round(float(succ(U[[i]],K)[:,:,:,:,:,0].mean()),4) for i,a in enumerate(ARMS)})
ok=succ(D[[0,1,2]],K)
pt=policy(ok[...,:10],ok[...,10:]); pt=np.array([pt[1]-pt[0],pt[2]-pt[1],pt[3]-pt[1]])
def boot(ok,n,seed):
    r=np.random.default_rng(seed); out=np.zeros((n,3))
    for b in range(n):
        m=r.integers(3,size=3); h=r.integers(5,size=5); s=r.integers(0,10,size=10); t=r.integers(10,20,size=10)
        x=ok[m][:,:,:,:,:,:,h]
        p=policy(x[...,s],x[...,t]); out[b]=[p[1]-p[0],p[2]-p[1],p[3]-p[1]]
    return out
for sd in [12345,777]:
    b=boot(ok,2000,sd); q=np.quantile(b,[.025,.975],axis=0)
    rc=q+pt-b.mean(0); piv=np.stack([2*pt-q[1],2*pt-q[0]])
    print("seed",sd,"boot mean",np.round(b.mean(0),4),"sd",np.round(b.std(0),4))
    for i,n in enumerate("HPQ"): print(f"  {n} pt {pt[i]:.4f} recentred [{rc[0,i]:.4f},{rc[1,i]:.4f}] raw pct [{q[0,i]:.4f},{q[1,i]:.4f}] pivot [{piv[0,i]:.4f},{piv[1,i]:.4f}]")
    np.save(f"boot{sd}.npy",b)
