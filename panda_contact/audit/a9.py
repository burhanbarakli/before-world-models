import numpy as np
d=np.load("./panda_contact/results/exp_contact.npz")
D=d["data"]; keys=list(d["keys"]); K=lambda n: D[...,keys.index(n)]
ok,deep,ti=K("ok"),K("deep"),K("t_in")
tf=np.array([16.,12.])[None,:,None,None,None,None,None,None,None]
ti2=np.where(ok==1,ti,tf)
def boot(x, B=2000, seed=0):
    # x: (m,T,dl,g,e,c,pol,h,s) -> diff KAHIN-REFLEKS on c5 e>0 paper
    y=x[:3,:,:,:,1:,0]; Z=(y[...,2,:,:]-y[...,1,:,:]).mean(axis=(1,2,3,4))  # (m,h,s)
    pt=Z.mean(); rng=np.random.default_rng(seed)
    bs=[Z[np.ix_(rng.integers(0,3,3),rng.integers(0,5,5),rng.integers(0,20,20))].mean() for _ in range(B)]
    return pt, np.percentile(bs,[2.5,97.5])
print("arrival REFLEKS-KAHIN (code t_in):", -boot(ti)[0], " with force failures as tf:", -boot(ti2)[0], -boot(ti2)[1][::-1])
print("W_deep", boot(deep))
nop=ok.copy(); nop=nop[:,:,:,0:1]
print("W no-push half", boot(nop))
pu=ok[:,:,:,1:2]; print("W push half", boot(pu))
