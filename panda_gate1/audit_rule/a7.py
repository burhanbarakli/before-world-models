import sys; sys.path.insert(0,sys.argv[1])
from lib import *
o=ok(D,.005).astype(np.float32)
rng=np.random.default_rng(9); r=[]
for _ in range(2000):
    h=rng.integers(5,size=5); t=10+rng.integers(10,size=10)
    te=o[:,:,:,:,:,h][...,t].mean((5,6))
    r.append(te[...,:9].mean(3).max(-1).mean()-te[...,9].mean())
r=np.array(r); print('ORT-RULE on test half, resampled, no selection: mean %.4f q2.5 %.4f q97.5 %.4f max %.4f P>=.03 %.4f'%(r.mean(),*np.quantile(r,[.025,.975]),r.max(),(r>=.03).mean()))
# feasibility-conditional M: restrict to runs where any eta succeeds, within cell
f=(o.max(4,keepdims=True)>0)
print('M/feasible approx',0.01472/f.mean(), 'U/feasible',.0233/f.mean())
# table of rule failure vs best by gap x T
sel=o[...,:10].mean((5,6)); te=o[...,10:].mean((5,6)); s=scoreM(sel,te); tab=s['tab']; I=np.indices(tab.shape)
for iT in range(3):
    for g in range(2):
        tb=te[iT,:,:,g,:9][I[1][0],I[2][0],tab[iT]].mean()
        print(TT[iT],G[g],'rule %.3f 8 %.3f tab %.3f'%(te[iT,:,:,g,9].mean(),te[iT,:,:,g,4].mean(),tb))
