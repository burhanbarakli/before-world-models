import numpy as np
from common import *
D,U,K=load(); OK=succ(D,K); r=np.load("rim.npz"); z=(r["zpost"]-RIM)*1e3; l=r["latpost"]*1e3; pre=r["pre"]
ok=OK[[0,1,2]]; zz=z[[0,1,2]]; ll=l[[0,1,2]]
zone=(zz<8)&(ll>5)    # lands laterally off, below or within 8 mm above rim
print("zone share all/sel/test",round(float(zone.mean()),4),round(float(zone[...,:10].mean()),4),round(float(zone[...,10:].mean()),4))
print("KAPI0 failures inside zone (paper):",(~ok[:,:,:,:,:,2]&zone).sum()/(~ok[:,:,:,:,:,2]).sum())
print("KURAL failures inside zone:",(~ok[:,:,:,:,:,0]&zone).sum()/(~ok[:,:,:,:,:,0]).sum())
te=ok[...,10:]; zt=zone[...,10:]
print("test, outside zone: S by opt",[round(float(te[:,:,:,:,:,o][~zt].mean()),4) for o in range(5)])
print("test, inside zone:  S by opt",[round(float(te[:,:,:,:,:,o][zt].mean()),4) for o in range(5)])
# Share of H from each (T,gap)
h=(ok[:,:,:,:,:,2].astype(float)-ok[:,:,:,:,:,0])[...,10:].mean((0,2,3,5,6))
print("H contributions by T,gap (each cell's gain/4):",np.round(h/4,4).tolist())
# KURAL failure in terms of landing: by h+tau outside zone
s=np.array([[a+b for b in LAG] for a in DELAY])
# L=.01 advantage per model from pre gating: how much of (.01 ok & .02 fail) has pre>0
for ia in range(3):
    gain=OK[ia,:,:,:,:,1]&~OK[ia,:,:,:,:,2]
    pm=pre[ia,...,0]>0
    print("model",ia,"L.01 ok & L.02 fail runs",gain.sum(),"with pre-gating at L=.01",(gain&pm[...,None]).sum(),"mean pre ticks there",round(float(pre[ia,...,0][...,None].repeat(20,-1)[gain].mean()),1))
gain=OK[4,:,:,:,:,1]&~OK[4,:,:,:,:,2]; print("analytic same",gain.sum(),(gain&(pre[4,...,0][...,None]>0)).sum())
# pre ticks by T=8 gap .25 per hole, per model at L=.01
print("mean pre ticks L=.01, T=8, by arm, by hole:",{ARMS[i]:np.round(pre[i,0,:,:,1,:,0].mean((0,1)),1).tolist() for i in range(5)})
