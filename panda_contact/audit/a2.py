import numpy as np
d=np.load("./panda_contact/results/exp_contact.npz")
D=d["data"]; keys=list(d["keys"]); K=lambda n: D[...,keys.index(n)]
ok=K("ok")
# recompute ok from fields
ok2=((K("end_z")<=0.25-0.9*0.06)&(K("f_max")<=50)).astype(float)
m=~np.isnan(ok); print("ok consistent:", np.all(ok[m]==ok2[m]), " deep consistent:", np.all(K("deep")[m]==(K("end_z")[m]<=0.25-0.054)))
# paper arm indices 0,1,2; c=5 -> c idx0
def cellS(ok, c):
    # per (model, hole, seed) -> mean over T,delay,gap,e>0 for each policy, and TABAN e=0
    x=ok[:3,:,:,:,:,c]  # (m,T,dl,g,e,pol,h,s)
    # mean over T,delay,e, with gaps weighted equally: grid balanced, compute mean per gap then average
    Spos=x[:,:,:,:,1:].mean(axis=(1,2,4))      # (m,g,pol,h,s)
    Spos=Spos.mean(axis=1)                       # equal gap weight -> (m,pol,h,s)
    S0=x[:,:,:,:,0,0].mean(axis=(1,2,3))         # TABAN e=0 (m,h,s)
    return Spos,S0
def stat(Spos,S0,mi,hi,si):
    sp=Spos[np.ix_(mi,[0,1,2],hi,si)].mean(axis=(0,2,3)); s0=S0[np.ix_(mi,hi,si)].mean()
    return np.array([s0, s0-sp[0], sp[1]-sp[0], sp[2]-sp[1]]), sp
for c in (0,1):
    Spos,S0=cellS(ok,c)
    pt,sp=stat(Spos,S0,[0,1,2],range(5),range(20))
    print(f"c idx {c}: S", np.round(sp,4), "G K R W", np.round(pt,4))
    for rs in (0,1,7):
        rng=np.random.default_rng(rs)
        bs=np.array([stat(Spos,S0,rng.integers(0,3,3),rng.integers(0,5,5),rng.integers(0,20,20))[0] for _ in range(2000)])
        lo,hi=np.percentile(bs,[2.5,97.5],axis=0)
        print("  seed",rs,"lo",np.round(lo,4),"hi",np.round(hi,4))
    # alternative: nested bootstrap (seeds within hole independently)
    rng=np.random.default_rng(3); bs=[]
    for _ in range(2000):
        mi=rng.integers(0,3,3); hi_=rng.integers(0,5,5)
        vals=[]; v0=[]
        acc=np.zeros(3); a0=0
        for h in hi_:
            si=rng.integers(0,20,20)
            acc+=Spos[np.ix_(mi,[0,1,2],[h],si)].mean(axis=(0,2,3)); a0+=S0[np.ix_(mi,[h],si)].mean()
        acc/=5; a0/=5
        bs.append([a0,a0-acc[0],acc[1]-acc[0],acc[2]-acc[1]])
    lo,hi=np.percentile(np.array(bs),[2.5,97.5],axis=0); print("  nested lo",np.round(lo,4),"hi",np.round(hi,4))
    # fixed models (only holes,seeds)
    rng=np.random.default_rng(4)
    bs=np.array([stat(Spos,S0,[0,1,2],rng.integers(0,5,5),rng.integers(0,20,20))[0] for _ in range(2000)])
    lo,hi=np.percentile(bs,[2.5,97.5],axis=0); print("  no-model-resample lo",np.round(lo,4),"hi",np.round(hi,4))
