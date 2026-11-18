import numpy as np
P="./panda_gate1/results/gate_rule.npz"
Z=np.load(P); D=Z['data']; keys=[str(k) for k in Z['keys']]
RIM,DEP=0.25,0.06
E=np.array([3,4,5,6.5,8,10,12,16,20]); H=[.015,.035,.07,.09]; L=[0,.025,.04]; TT=[8.,6.,4.]; G=[.4,.25]
def ok(D,c):
    lat=D[...,0];tilt=D[...,1];z=D[...,2]
    return ((RIM-z)>=0.9*DEP)&(lat<=c)&(tilt<=np.arctan(2*c/DEP))
def scoreM(sel,te,tie='first'):
    """sel,te float arrays T,h,t,g,e(10),n  (n = flattened runs or hole,seed mean already)"""
    # sel,te : T,h,t,g,e after averaging
    gs=sel[...,:9]; 
    m=gs.mean((0,1,2,3))
    if tie=='last': f=8-int(np.argmax(m[::-1]))
    else: f=int(np.argmax(m))
    tm=gs.mean(3)
    if tie=='last': tab=8-np.argmax(tm[...,::-1],axis=-1)
    else: tab=np.argmax(tm,axis=-1)
    I=np.indices(tab.shape)
    tte=te[...,:9].mean(3)
    TABLE=tte[I[0],I[1],I[2],tab].mean()
    return dict(RULE=te[...,9].mean(),FIX8=te[...,4].mean(),FIXS=te[...,f].mean(),TABLE=TABLE,ORACLE=te[...,:9].max(-1).mean(),ORT=tte.max(-1).mean(),f=f,tab=tab)
def outcome(s,q):
    G_=s['ORACLE']-s['FIX8']>=.03; B=q[0,0]>0 and q[0,1]>0; M=s['TABLE']-s['RULE'];U=q[1,2]
    if not G_: return 'inconclusive'
    if not B: return 'not confirmed'
    if M>=.03: return 'helps/not suffice'
    if U>=.03: return 'supported, small margin not excluded'
    return 'confirmed'
def boot(o,n=2000,seed=123,mode='protocol',tie='first',ret=False):
    """o bool T,h,t,g,e,hole,seed"""
    o=o.astype(np.float32)
    rng=np.random.default_rng(seed); NH=o.shape[5]
    out=[]
    for _ in range(n):
        if mode in('protocol','holesonly','seedsonly','nested'):
            hi=rng.integers(NH,size=NH) if mode!='seedsonly' else np.arange(NH)
        if mode=='protocol' or mode=='seedsonly':
            si=rng.integers(10,size=10); ti=10+rng.integers(10,size=10)
            a=o[:,:,:,:,:,hi]
            sel=a[...,si].mean((5,6)); te=a[...,ti].mean((5,6))
        elif mode=='holesonly':
            a=o[:,:,:,:,:,hi]; sel=a[...,:10].mean((5,6)); te=a[...,10:].mean((5,6))
        elif mode=='nested':
            # seeds resampled independently inside each drawn hole slot
            sel=0;te=0
            for h in hi:
                si=rng.integers(10,size=10); ti=10+rng.integers(10,size=10)
                sel=sel+o[:,:,:,:,:,h][...,si].mean(5); te=te+o[:,:,:,:,:,h][...,ti].mean(5)
            sel=sel/NH;te=te/NH
        elif mode=='hxT':
            # independent units: hole x T x seed (directions depend on T and hole)
            hi=rng.integers(NH,size=NH)
            sels=[];tes=[]
            for iT in range(o.shape[0]):
                s_=0;t_=0
                for h in hi:
                    si=rng.integers(10,size=10); ti=10+rng.integers(10,size=10)
                    s_=s_+o[iT,:,:,:,:,h][...,si].mean(4); t_=t_+o[iT,:,:,:,:,h][...,ti].mean(4)
                sels.append(s_/NH);tes.append(t_/NH)
            sel=np.stack(sels);te=np.stack(tes)
        s=scoreM(sel,te,tie)
        out.append((s['RULE']-s['FIX8'],s['RULE']-s['FIXS'],s['TABLE']-s['RULE']))
    out=np.array(out)
    q=np.quantile(out,[.025,.975],axis=0)
    return (q,out) if ret else q
