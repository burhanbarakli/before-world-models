import sys; sys.dont_write_bytecode=True
import numpy as np, pickle
from common import *
D,U,K=load(); OK=succ(D,K)
z=np.load(ROOT+"/panda_gate1/results/gate_rule.npz"); old=z["data"]; print("gate_rule",old.shape,[str(k) for k in z["keys"]])
print("analytic no-gate == gate_rule rule arm, T=8,4, h=70,90:",np.array_equal(D[4,:,2:,:,:,0],old[[0,2]][:,2:,:,:,9]))
oldok=succ(old[[0,2]][:,:,:,:,:9],K); fail=~oldok.any(4)
a=OK[4]; print("runs failing at every eta",round(fail.mean(),4),"rescued any gate",round((a[...,1:,:,:].any(4)&fail).sum()/fail.sum(),4),"KAPI0",round((a[:,:,:,:,2]&fail).sum()/fail.sum(),4))
print("  those failures: lost-type? see s6b. by T,gap",np.round(fail.mean((1,2,4,5)),3).tolist())
tr=pickle.load(open("traces.pkl","rb"))
# t_d spread across arms
d=[]
for T in PERIOD:
  for h in DELAY:
    for t in LAG:
      for ho in range(5):
        tr5=tr[(None,T,h,t)][ho]["t_rim"]
        d.append([ (tr[(a,T,h,t)][ho]["t_rim"] or np.nan)-tr5 for a in [0,1,2]])
d=np.array(d); print("t_rim(model)-t_rim(analytic): mean",np.round(np.nanmean(d),3),"min",np.nanmin(d),"max",np.nanmax(d))
# reference z monotone/band covers only straight descent
sys.path.insert(0,ROOT+"/panda_gate1")
import field_se3 as F, robot as Rb, gate_rule as Gr, gate1g as Gg
for T in PERIOD:
    ref=Rb.reference_for(None,Gr.HOLES[0],T); i=int(np.argmax(ref.p[:,2]<.37+1e-9))
    print("T",T,"z min before via",ref.p[:i,2].min(),"first band idx t",i*ref.dt,"t rim ref",Gg.rim_index(ref)*ref.dt,"descent speed at rim mm/s",-1e3*ref.v[Gg.rim_index(ref),2],"at via",-1e3*ref.v[i,2],"xy drift in band mm",1e3*np.abs(ref.p[i:,:2]-ref.p[-1,:2]).max(), "vmax",ref.vmax)
    r=Gg.rim_index(ref)
    for gap in GAP: print("   ref height at rim-gap mm",1e3*(ref.p[r-int(round(gap/ref.dt)),2]-.25))
# disturbance size in mm
rng=[]
for it,T in enumerate(PERIOD):
  for ih in range(5):
    for s in range(20):
      r_=np.random.default_rng([ih,30,s,int(T)]); w,v=Rb.disturbance(r_,.2); rng.append(list(v)+list(w))
rng=np.array(rng); print("first-draw disturbance: |v| mm mean",1e3*np.linalg.norm(rng[:,:3],axis=1).mean(),"max",1e3*np.linalg.norm(rng[:,:3],axis=1).max(),"|w| rad mean",np.linalg.norm(rng[:,3:],axis=1).mean())
# dedupe: unique outcomes in the npz between arms
print("distinct T,hole,seed disturbances",2*5*20,"; test half:",2*5*10)
# sel vs test imbalance: z-down component
dz=(rng[:,2]); print("mean downward jump (v_z, body z=down) sel",1e3*dz[np.arange(200)%20<10].mean(),"test",1e3*dz[np.arange(200)%20>=10].mean())
