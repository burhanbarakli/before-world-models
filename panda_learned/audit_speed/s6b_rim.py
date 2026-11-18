"""Joins the ungated traces with the disturbances: which runs are teleported through the rim; pre-t_d gating; cross-tab with stored bits."""
import sys,pickle; sys.dont_write_bytecode=True
import irun as I, numpy as np
import robot as Rb
from common import *
D,U,K=load(); OK=succ(D,K); tr=pickle.load(open("traces.pkl","rb"))
I.ROBOT=Rb.Panda()
Arms=I.Gl.ARMS
# disturbances per T,hole,seed,gap
W={}
for it,T in enumerate(PERIOD):
  for ih in range(5):
    ref=Rb.reference_for(I.ROBOT,I.Gr.HOLES[ih],T)
    for ig,g in enumerate(GAP):
      for s in range(20): W[it,ih,ig,s]=I.Gr.draw(I.ROBOT,ref,ih,s,g)
same=sum(np.array_equal(W[it,ih,0,s][1],W[it,ih,1,s][1]) for it in range(2) for ih in range(5) for s in range(20))
print("same disturbance across gaps:",same,"of 200")
n=(5,2,4,3,2,5,20)
through=np.zeros(n,bool); zpost=np.zeros(n); latpost=np.zeros(n); zpre=np.zeros(n[:5]+(5,))
pre=np.zeros(n[:5]+(5,4)) # ticks with d>L in band before t_d
dmaxpre=np.zeros(n[:5]+(5,)); dmaxall=np.zeros(n[:5]+(5,))
for ia,a in enumerate(Arms):
 for it,T in enumerate(PERIOD):
  for ih_,h in enumerate(DELAY):
   for il,tau in enumerate(LAG):
    x=tr[(a,T,h,tau)]
    for ho in range(5):
     e=x[ho]; t=e["tr"]; tt,px,py,pz,d=t[:,0],t[:,1],t[:,2],t[:,3],t[:,4]
     band=(pz-RIM>=0)&(pz-RIM<=.12)
     for ig,g in enumerate(GAP):
      t_d=(e["dt"]*e["rim_i"]+h+tau if e["t_rim"] is None else e["t_rim"])-g
      k=int(np.argmax(tt>=t_d-1e-9)); zpre[ia,it,ih_,il,ig,ho]=pz[k]
      m=band&(np.arange(len(tt))<k)
      dmaxpre[ia,it,ih_,il,ig,ho]=d[m].max() if m.any() else 0
      dmaxall[ia,it,ih_,il,ig,ho]=d[band].max() if band.any() else 0
      for io,L in enumerate(LO:=[.01,.02,.04,.08]): pre[ia,it,ih_,il,ig,ho,io]=(d[m]>L).sum()
      # R approx R_down at the descent; use R_down plus true small tilt is not stored, so use reference orientation at end
      R=Rb.R_DOWN
      for s in range(20):
        w,v=W[it,ho,ig,s]
        dv=R@v
        zp=pz[k]+dv[2]; zpost[ia,it,ih_,il,ig,ho,s]=zp
        latpost[ia,it,ih_,il,ig,ho,s]=np.hypot(px[k]+dv[0]-I.Gr.HOLES[ho][0],py[k]+dv[1]-I.Gr.HOLES[ho][1])
        through[ia,it,ih_,il,ig,ho,s]=zp<RIM
np.savez("rim.npz",through=through,zpost=zpost,latpost=latpost,zpre=zpre,pre=pre,dmaxpre=dmaxpre,dmaxall=dmaxall)
print("z_pre-rim mm by T,gap, mean (paper):",np.round(1e3*(zpre[:3]-RIM).mean((0,2,3,5)),1).tolist(),"min",np.round(1e3*(zpre[:3]-RIM).min((0,2,3,5)),1).tolist())
for nm,idx in [("paper",[0,1,2]),("analytic",[4]),("weak",[3])]:
  print("==",nm)
  th=through[idx]; lp=latpost[idx]; ok=OK[idx]
  lost=th&(lp>.005)
  print(" P(through rim):",round(float(th.mean()),4)," through & lat>5mm at landing:",round(float(lost.mean()),4),"by T,gap",np.round(lost.mean((0,2,3,5,6)),4).tolist())
  print(" test half lost",round(float(lost[...,10:].mean()),4),"sel half",round(float(lost[...,:10].mean()),4))
  for o in range(5):
    f=~ok[:,:,:,:,:,o]; 
    print(f" opt {OPT[o]}: fail {f.mean():.4f}; failures that are 'lost' {(f&lost).sum()/f.sum():.3f}; lost that fail {(f&lost).sum()/lost.sum():.3f}; non-lost fail rate {(f&~lost).sum()/(~lost).sum():.4f}; test: S {1-f[...,10:].mean():.4f}, S given not lost {1-(f&~lost)[...,10:].sum()/(~lost)[...,10:].sum():.4f}")
  pr=pre[idx]; print(" ticks d>L in band before t_d, share of (model,cell,gap,hole) with any, by L:",np.round((pr>0).mean((0,1,2,3,4,5)),3),"mean ticks",np.round(pr.mean((0,1,2,3,4,5)),1))
  print("   by T for L=.01:",np.round((pr[...,0]>0).mean((0,2,3,4,5)),3),"; L=.02:",np.round((pr[...,1]>0).mean((0,2,3,4,5)),3),"; L=.04:",np.round((pr[...,2]>0).mean((0,2,3,4,5)),3))
  print("   max d before t_d",round(float(dmaxpre[idx].max()),4),"p99",round(float(np.quantile(dmaxpre[idx],.99)),4),"max d in band overall",round(float(dmaxall[idx].max()),4))
