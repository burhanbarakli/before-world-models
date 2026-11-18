import sys; sys.path.insert(0,sys.argv[1])
from lib import *
o=ok(D,.005)
sel=o[...,:10].astype(float).mean((5,6)); te=o[...,10:].astype(float).mean((5,6))
s=scoreM(sel,te); print({k:round(float(v),4) for k,v in s.items() if k not in('tab',)})
pt=np.array([s['RULE']-s['FIX8'],s['RULE']-s['FIXS'],s['TABLE']-s['RULE']]); print('point',pt)
for mode in ['protocol','nested','hxT','holesonly','seedsonly']:
    q,out=boot(o,2000,seed=7,mode=mode,ret=True)
    print(mode,'q',np.round(q,4).tolist(),'mean',np.round(out.mean(0),4),'outcome',outcome(s,q))
    if mode=='protocol':
        np.save(sys.argv[1]+'/bootprot.npy',out)
        print('  basic-pivot U for M: %.4f  L: rule-fix8 %.4f rule-fixs %.4f'%(2*pt[2]-q[0,2],2*pt[0]-q[1,0],2*pt[1]-q[1,1]))
        print('  bias M (boot mean - point) %.4f; shifted U %.4f'%(out[:,2].mean()-pt[2], q[1,2]+pt[2]-out[:,2].mean()))
        print('  P(M>=.03) in boot',(out[:,2]>=.03).mean(), 'P(rule-fixs<=0)',(out[:,1]<=0).mean(),'P(rule-fix8<=0)',(out[:,0]<=0).mean())
for sd in (0,1,2):
    print('seed',sd,np.round(boot(o,2000,seed=sd),4).tolist())
