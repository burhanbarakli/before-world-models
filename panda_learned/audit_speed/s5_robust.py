import numpy as np
from common import *
D,U,K=load(); OK=succ(D,K)
ok=OK[[0,1,2]]
def row(x,s,t):
    k,g,tab,o=policy(x[...,s],x[...,t]); return f"KURAL {k:.3f} KAPI0 {g:.3f} TAB {tab:.3f} ORC {o:.3f} | H {g-k:+.3f} P {tab-g:+.3f} Q {o-g:+.3f}"
S=np.arange(10);T=np.arange(10,20)
print("base         ",row(ok,S,T)); print("swapped halves",row(ok,T,S))
for m in range(3): print(f"model {m}      ",row(ok[[m]],S,T)," swap:",row(ok[[m]],T,S))
for m in range(3):
    keep=[i for i in range(3) if i!=m]; print(f"drop model {m} ",row(ok[keep],S,T))
for h in range(5):
    keep=[i for i in range(5) if i!=h]; print(f"drop hole {h}  ",row(ok[:,:,:,:,:,:,keep],S,T)," swap:",row(ok[:,:,:,:,:,:,keep],T,S))
r=np.random.default_rng(99); N=5000; R=np.zeros((N,3))
for i in range(N):
    p=r.permutation(20); s,t=p[:10],p[10:]
    a=policy(ok[...,s],ok[...,t]); R[i]=[a[1]-a[0],a[2]-a[1],a[3]-a[1]]
q=np.quantile(R,[0,.025,.5,.975,1],axis=0)
print("random 10/10 splits n=",N)
for i,n in enumerate("HPQ"): print(f" {n}: min {q[0,i]:.4f} p2.5 {q[1,i]:.4f} med {q[2,i]:.4f} p97.5 {q[3,i]:.4f} max {q[4,i]:.4f}")
oc=np.where(R[:,0]<.03,0,np.where(R[:,2]<.03,1,np.where(R[:,1]>=.03,2,3)))
print(" outcome share: H fail,gate suffices,P>=.03,no decision",np.round(np.bincount(oc,minlength=4)/N,4))
# per-model and per-hole share of Q>=.03 across splits
for m in range(3):
    Rm=np.zeros(1000)
    for i in range(1000):
        p=r.permutation(20); a=policy(ok[[m]][...,p[:10]],ok[[m]][...,p[10:]]); Rm[i]=a[3]-a[1]
    print(f" model {m} Q splits: med {np.median(Rm):.4f} max {Rm.max():.4f} share>=.03 {np.mean(Rm>=.03):.3f}")
# all 20 seeds used as test with fixed policies
print("all seeds: by option",np.round(ok.mean((0,1,2,3,4,6,7)),4),"oracle",round(float(ok.any(5).mean()),4))
# table choices
sel=ok[...,:10].astype(float).mean((4,6,7)).argmax(-1)
print("TABLOK choices (option index) counts:",np.bincount(sel.ravel(),minlength=5), "of",sel.size)
print("per model",[np.bincount(sel[m].ravel(),minlength=5).tolist() for m in range(3)])
# oracle anatomy on test
te=ok[...,10:]; a=te.any(5)
print("test: oracle",a.mean(),"L=.01",te[:,:,:,:,:,1].mean(),"runs oracle-success but L=.01 fails:",(a&~te[:,:,:,:,:,1]).mean(), "count",(a&~te[:,:,:,:,:,1]).sum(),"of",a.size)
print("nestedness (all seeds) P(success at larger option | success at smaller L)-style: fail L=.01 & succ other:",(ok.any(5)&~ok[:,:,:,:,:,1]).mean())
for i,j in [(1,2),(2,3),(3,4),(2,0),(1,0)]:
    print(f" opt {OPT[j]} ok & opt {OPT[i]} fail (all seeds): {(ok[:,:,:,:,:,j]&~ok[:,:,:,:,:,i]).mean():.5f}  reverse {(ok[:,:,:,:,:,i]&~ok[:,:,:,:,:,j]).mean():.5f}")
# oracle vs independence benchmark, per cell(model,T,h,tau,gap)
te=te.astype(float); p=te.mean((6,7)); ind=(1-np.prod(1-p,axis=5)).mean(); com=p.max(5).mean()
print("oracle actual",te.max(5).mean(),"if options independent given cell",round(float(ind),4),"if fully nested",round(float(com),4), "(paper, test)")
tea=OK[[4]][...,10:].astype(float); p=tea.mean((6,7)); print("analytic: actual",tea.max(5).mean(),"indep",round(float((1-np.prod(1-p,axis=5)).mean()),4),"nested",round(float(p.max(5).mean()),4))
# flips between models for same run: disagreement
print("gated (KAPI0) per-run agreement across 3 models, all seeds:",(ok[:,:,:,:,:,2].sum(0)%3==0).mean(), " no-gate:",(ok[:,:,:,:,:,0].sum(0)%3==0).mean())
# slices of H, S by (T,gap), and by L
for i,t in enumerate(PERIOD):
  for j,g in enumerate(GAP):
    print(f"T={t} gap={g}: test S by option",np.round(te[:,i,:,:,j].mean((0,1,2,4,5)),3)," all seeds",np.round(ok[:,i,:,:,j].mean((0,1,2,4,5)),3),"  analytic",np.round(OK[4,i,:,:,j].mean((0,1,3,4)),3)," weak",np.round(OK[3,i,:,:,j].mean((0,1,3,4)),3))
sumd=np.array([[h+t for t in LAG] for h in DELAY])
print("by h+tau (paper, test): ")
for h,t in sorted(np.ndindex(4,3),key=lambda ij:sumd[ij]):
    print(f" {sumd[h,t]:.3f} eta {min(20,.6/sumd[h,t]):5.2f}: ",np.round(te[:,:,h,t].mean((0,1,2,4,5)),3),"  analytic",np.round(OK[4,:,h,t][...,10:].mean((0,1,3,4)),3))
