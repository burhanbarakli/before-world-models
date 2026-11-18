import numpy as np
from common import *
D,U,K=load(); OK=succ(D,K); r=np.load("rim.npz")
zp,lp=r["zpost"],r["latpost"]; pre=r["pre"]
for nm,idx in [("paper",[0,1,2]),("analytic",[4])]:
  print("==",nm,"landing height above rim (mm) vs failure, runs with lateral >5 mm at landing vs <=5")
  z=(zp[idx]-RIM)*1e3; l=lp[idx]*1e3; ok=OK[idx]
  bins=[-40,-5,0,2,4,6,8,10,15,20,80]
  for lo,hi in zip(bins[:-1],bins[1:]):
    m=(z>=lo)&(z<hi)
    for tag,mm in [(">5",m&(l>5)),("<=5",m&(l<=5))]:
      if mm.sum()==0: continue
      f=[(~ok[:,:,:,:,:,o])[mm].mean() for o in range(5)]
      print(f"  z [{lo},{hi}) lat{tag}: n {mm.sum()}  fail none {f[0]:.3f} .01 {f[1]:.3f} .02 {f[2]:.3f} .04 {f[3]:.3f} .08 {f[4]:.3f}  share of KAPI0 fails {(mm&~ok[:,:,:,:,:,2]).sum()/(~ok[:,:,:,:,:,2]).sum():.3f}")
  # KAPI0 failures: margin needed vs h+tau
  s=np.array([[h+t for t in LAG] for h in DELAY])
  print(" KAPI0 fail rate by h+tau among z in [0,8) lat>5:")
  for h,t in sorted(np.ndindex(4,3),key=lambda ij:s[ij]):
    m=(z[:,:,h,t]>=0)&(z[:,:,h,t]<8)&(l[:,:,h,t]>5)
    print(f"   {s[h,t]:.3f} n {m.sum()} fail {(~ok[:,:,h,t,:,2])[m].mean():.3f}")
# how many reruns are needed
tot=0
for ia in [0,1,2,4]:
  for o,io in [(1,0),(2,1),(3,2)]:
    res=OK[ia,:,:,:,:,o]&~OK[ia,:,:,:,:,0]     # gate rescues
    pm=pre[ia,:,:,:,:,:,io]>0                  # gated path differs from ungated before t_d
    n=(res&pm[...,None]).sum(); tot+=n
    ks=(OK[ia,:,:,:,:,0]&pm[...,None]).sum()
    print("arm",ia,"opt",OPT[o],"rescued runs",res.sum(),"with pre-gating",n,"share",round(n/max(res.sum(),1),3),"| kurals ok with pre-gating",ks)
print("total reruns",tot)
# when does pre-gating occur in KAPI0, which T, gap
for ia,nm in [(0,"m0"),(4,"analytic")]:
  print(nm,"share with d>.02 before t_d by T,gap",np.round((pre[ia,...,1]>0).mean((1,2,4)),3).tolist(),"by T,h+tau index h",np.round((pre[ia,...,1]>0).mean((2,3,4)),3).tolist())
