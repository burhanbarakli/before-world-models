import sys; sys.path.insert(0,sys.argv[1])
from lib import *
import itertools
from math import comb
o=ok(D,.005).astype(float)
# in-sample / oracle bound on M
s=scoreM(o[...,:10].mean((5,6)),o[...,10:].mean((5,6)))
print('test: ORT-RULE %.4f ORACLE-RULE %.4f'%(s['ORT']-s['RULE'],s['ORACLE']-s['RULE']))
s=scoreM(o[...,10:].mean((5,6)),o[...,:10].mean((5,6)))
print('sel half as test: ORT-RULE %.4f ORACLE-RULE %.4f'%(s['ORT']-s['RULE'],s['ORACLE']-s['RULE']))
a=o.mean((5,6)); print('all 20 seeds, in-sample best per (T,h,tau) minus rule: %.4f; best per cell w/gap %.4f'%(a[...,:9].mean(3).max(-1).mean()-a[...,9].mean(), a[...,:9].max(-1).mean()-a[...,9].mean()))
# random splits (seed labels within each hole independent)
rng=np.random.default_rng(11); Ms=[];r8=[];rS=[]
for _ in range(1000):
    sl=np.zeros((5,20),bool)
    for h in range(5): sl[h,rng.permutation(20)[:10]]=True
    sel=np.zeros(o.shape[:5]);te=sel.copy()
    for h in range(5):
        sel+=o[:,:,:,:,:,h][...,sl[h]].mean(5)/5; te+=o[:,:,:,:,:,h][...,~sl[h]].mean(5)/5
    s=scoreM(sel,te); Ms.append(s['TABLE']-s['RULE']); r8.append(s['RULE']-s['FIX8']); rS.append(s['RULE']-s['FIXS'])
for n,x in [('M',Ms),('r-8',r8),('r-S',rS)]:
    x=np.array(x); print('random split',n,'mean %.4f sd %.4f min %.4f q2.5 %.4f q97.5 %.4f max %.4f'%(x.mean(),x.std(),x.min(),*np.quantile(x,[.025,.975]),x.max()))
print('frac split M>=.03',np.mean(np.array(Ms)>=.03),'frac r-S<=0',np.mean(np.array(rS)<=0),'frac r-8<=0',np.mean(np.array(r8)<=0))
# per-hole t interval with fixed selection
s=scoreM(o[...,:10].mean((5,6)),o[...,10:].mean((5,6))); tab=s['tab'];I=np.indices(tab.shape)
rows=[]
for h in range(5):
    t=o[:,:,:,:,:,h,10:].mean(5); tb=t[...,:9].mean(3)[I[0],I[1],I[2],tab].mean()
    rows.append((t[...,9].mean()-t[...,4].mean(),t[...,9].mean()-t[...,s['f']].mean(),tb-t[...,9].mean()))
rows=np.array(rows); print('per-hole diffs r-8,r-S,M\n',rows)
m=rows.mean(0);se=rows.std(0,ddof=1)/np.sqrt(5);print('t4 CI lo',m-2.776*se,'hi',m+2.776*se)
# half difference: seed-level
for nm,idx in [('rule',9),('eta8',4),('eta6.5',3)]:
    x=o[:,:,:,:,idx].mean((0,1,2,3))  # hole,seed
    print(nm,'hole x half means',x[:,:10].mean(1).round(3),x[:,10:].mean(1).round(3))
    y=x.mean(0); print('  seed means',y.round(2))
# seed-level perm test of half gap for rule
x=o[:,:,:,:,9].mean((1,2,3))  # T,hole,seed -> independent directions
x=x.reshape(-1,20)
obs=x[:,10:].mean()-x[:,:10].mean(); rng=np.random.default_rng(1)
d=[]
for _ in range(5000):
    p=np.array([rng.permutation(20) for _ in range(len(x))]); xx=np.take_along_axis(x,p,1); d.append(xx[:,10:].mean()-xx[:,:10].mean())
print('half gap rule',obs,'perm p',(np.abs(d)>=abs(obs)).mean())
# failures: how many runs are failed under every eta incl rule (eta-independent)?
print('fraction of (T,h,tau,gap,hole,seed) failing for all 10 etas', (o.max(4)==0).mean(), 'by gap',(o.max(4)==0).mean((0,1,2,4,5)))
print('fraction by T,gap',(o.max(4)==0).mean((1,2,4,5)).round(3))
print('never below rim?', 'lat==0 frac', (D[...,0]==0).mean(), 'rule', (D[:,:,:,:,9,:,:,0]==0).mean(), 'eta20',(D[:,:,:,:,8,:,:,0]==0).mean())
# failure breakdown for RULE vs eta 8
lat,tilt,z=D[...,0],D[...,1],D[...,2]; c=.005
deep=(RIM-z)>=.9*DEP; la=lat<=c; ti=tilt<=np.arctan(2*c/DEP)
for e,n in [(9,'rule'),(4,'8'),(3,'6.5')]:
    print(n,'deep %.3f lat %.3f tilt %.3f all %.3f'%(deep[:,:,:,:,e].mean(),la[:,:,:,:,e].mean(),ti[:,:,:,:,e].mean(),(deep&la&ti)[:,:,:,:,e].mean()))
print('tilt limit rad',np.arctan(2*c/DEP), 'tilt fail not lat',(~ti&la).mean())
# paired identity check: outcomes for hopeless seeds same
