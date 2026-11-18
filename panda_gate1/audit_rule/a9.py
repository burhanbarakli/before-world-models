import sys; sys.path.insert(0,sys.argv[1])
from lib import *
np.set_printoptions(linewidth=170,precision=3,suppress=True)
Z2=np.load('heff.npz'); J=Z2['jobs']; R=Z2['res']; print(J.shape,R.shape)
D2=D.copy()
for j,r in zip(J,R):
    idx=(TT.index(j[0]),H.index(j[1]),L.index(j[2]),G.index(j[3]),9); D2[idx]=r
o=ok(D2,.005); s=scoreM(o[...,:10].astype(float).mean((5,6)),o[...,10:].astype(float).mean((5,6)))
print('RULE with effective h: S rule %.4f (was .8497) all-seed %.4f; r-8 %.4f r-S %.4f M %.4f'%(s['RULE'],o[...,9].mean(),s['RULE']-s['FIX8'],s['RULE']-s['FIXS'],s['TABLE']-s['RULE']))
q=boot(o,2000,seed=7); print(np.round(q,4).tolist(),outcome(s,q))
o0=ok(D,.005).astype(float)
for j in range(2):
    for l in range(3):
        print(H[j],L[l],'old %.3f new %.3f'%(o0[:,j,l,:,9,:,10:].mean(),o.astype(float)[:,j,l,:,9,:,10:].mean()))
# shared clock
T2=np.load('tshared.npz')['res']; o2=ok(T2,.005).astype(float)
s0=scoreM(o0[...,:10].mean((5,6)),o0[...,10:].mean((5,6)))
print('shared-clock rule test S %.4f vs stored %.4f; M %.4f; by gap new'%(o2.mean(),s0['RULE'],s0['TABLE']-o2.mean()),o2.mean((0,1,2,4,5)),'old',o0[:,:,:,:,9,:,10:].mean((0,1,2,4,5)))
ch=(ok(T2,.005)!=ok(D[:,:,:,:,9,:,10:],.005)); print('runs changed',ch.mean())
