"""Scores with the height trigger. Stored bits except for re-run runs; flips in the unre-run set are estimated from the sample."""
import pickle,sys; sys.dont_write_bytecode=True
import numpy as np
from common import *
D,U,K=load(); OK=succ(D,K); h=pickle.load(open("height.pkl","rb")); kind=h["kind"]
F=["lat","tilt","end_z","end_p","end_r","t_rim","t_jump","z_pre","z_post","lat_post","d_post","t_deep","lat_rim","n_pre","n_post","n_stop"]
ARMI={0:0,1:1,2:2,None:4}
Z=OK.copy(); stats={}
for key,ss,o in h["res"]:
    a,T,hh,tau,gp,ho,opt=key
    ia=ARMI[a]; it,ih,il,ig=PERIOD.index(T),DELAY.index(hh),LAG.index(tau),GAP.index(gp)
    new=(RIM-o[:,2]>=.9*DEPTH)&(o[:,0]<=.005)&(o[:,1]<=np.arctan(.01/DEPTH))
    for s,n in zip(ss,new):
        old=OK[ia,it,ih,il,ig,opt,ho,s]; k=kind[(ia,it,ih,il,ig,ho,opt,s)]
        stats.setdefault((ia,opt,T,'rescued' if k else 'other',bool(old)),[]).append(bool(n))
        Z[ia,it,ih,il,ig,opt,ho,s]=n
for k in sorted(stats,key=str):
    v=stats[k]; print(k,"n",len(v),"still ok",round(float(np.mean(v)),3))
ok=Z[[0,1,2]]; ok0=OK[[0,1,2]]
# L=.04 and .08 stored: L=.04 has a little pre-gating, clip it to be no better than the height-trigger L=.02 is not assumed; left as stored
for tag,x in [("clock trigger (stored)",ok0),("height trigger",ok)]:
    k,g,t,o=policy(x[...,:10],x[...,10:])
    print(f"{tag}: KURAL {k:.4f} KAPI0 {g:.4f} TAB {t:.4f} ORC {o:.4f} H {g-k:.4f} P {t-g:.4f} Q {o-g:.4f}  S by opt",np.round(x[...,10:].mean((0,1,2,3,4,6,7)),4))
    k,g,t,o=policy(x[...,10:],x[...,:10]); print(f"   swapped: H {g-k:.4f} P {t-g:.4f} Q {o-g:.4f}")
for i,T in enumerate(PERIOD):
  for j,g in enumerate(GAP):
    print(f" T={T} gap={g} test by opt clock",np.round(ok0[:,i,:,:,j][...,10:].mean((0,1,2,4,5)),3),"height",np.round(ok[:,i,:,:,j][...,10:].mean((0,1,2,4,5)),3))
xa,xb=OK[[4]],Z[[4]]
for tag,x in [("analytic clock",xa),("analytic height",xb)]:
    k,g,t,o=policy(x[...,:10],x[...,10:]); print(f"{tag}: KURAL {k:.4f} KAPI0 {g:.4f} TAB {t:.4f} ORC {o:.4f} H {g-k:.4f} P {t-g:.4f} Q {o-g:.4f}")
r=np.random.default_rng(3); b=np.zeros((2000,3))
for n in range(2000):
    m=r.integers(3,size=3); ho=r.integers(5,size=5); s=r.integers(0,10,size=10); t=r.integers(10,20,size=10)
    x=ok[m][:,:,:,:,:,:,ho]; p=policy(x[...,s],x[...,t]); b[n]=[p[1]-p[0],p[2]-p[1],p[3]-p[1]]
k,g,t,o=policy(ok[...,:10],ok[...,10:]); pt=np.array([g-k,t-g,o-g]); q=np.quantile(b,[.025,.975],axis=0)+pt-b.mean(0)
print("height trigger recentred:",{n:np.round(q[:,i],4).tolist() for i,n in enumerate("HPQ")})
np.save("ok_height.npy",Z)
