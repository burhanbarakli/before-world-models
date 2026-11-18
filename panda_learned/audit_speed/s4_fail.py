import numpy as np
from common import *
D,U,K=load(); li,ei=K.index("lat"),K.index("end_z")
ok=succ(D,K)
for nm,idx in [("paper",[0,1,2]),("analytic",[4]),("weak",[3])]:
  x=ok[idx]; d=D[idx]
  print("=====",nm)
  a=x.any(5); n=x.sum(5)
  print("frac runs success under k options k=0..5 all seeds:",np.round(np.bincount(n.ravel(),minlength=6)/n.size,4))
  print("test: ",np.round(np.bincount(n[...,10:].ravel(),minlength=6)/n[...,10:].size,4))
  print("sel: ",np.round(np.bincount(n[...,:10].ravel(),minlength=6)/n[...,:10].size,4))
  for o in range(5):
    f=~x[:,:,:,:,:,o]
    deep=(RIM-d[:,:,:,:,:,o,:,:,ei])>=.9*DEPTH
    lat=d[:,:,:,:,:,o,:,:,li]
    print(f" opt {OPT[o]}: fail {f.mean():.4f}; shallow {(~deep).mean():.4f}, lat>5mm {(lat>.005).mean():.4f}; shallow&fail-only-shallow {(~deep&(lat<=.005)).mean():.4f}")
  # all-fail runs by condition, whole set
  allf=~a
  print(" all-option failures: T",np.round(allf.mean((0,2,3,4,5,6)),4),"gap",np.round(allf.mean((0,1,2,3,5,6)),4))
  print(" by T,gap:",np.round(allf.mean((0,2,3,5,6)),4).tolist())
  print(" by h",np.round(allf.mean((0,1,3,4,5,6)),4),"tau",np.round(allf.mean((0,1,2,4,5,6)),4))
  print(" by hole",np.round(allf.mean((0,1,2,3,4,6)),4))
  print(" by seed",np.round(allf.mean((0,1,2,3,4,5)),3))
  print(" by model",np.round(allf.mean((1,2,3,4,5,6)),4))
  # concentration: distinct (T,gap,hole,seed)
  c=allf.mean((0,2,3)) # T,gap,hole,seed
  print(" distinct disturbance instances (T,gap,hole,seed)=",c.size," with any fail",(c>0).sum()," with all cells failing",(c>=1).sum(), ">0.5:",(c>.5).sum())
  print(" share of all-fail mass from instances>0.5:",c[c>.5].sum()/c.sum())
  big=np.argwhere(c>.5)
  print(" instances>0.5 (T,gap,hole,seed,rate):",[(PERIOD[i],GAP[j],h,s,round(float(c[i,j,h,s]),2)) for i,j,h,s in big][:40])
