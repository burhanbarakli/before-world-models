import sys; sys.path.insert(0,sys.argv[1])
from lib import *
np.set_printoptions(linewidth=170,precision=3,suppress=True)
o=ok(D,.005)
sr=o.astype(float)
# halves
print('half means rule,8,6.5: sel',sr[...,:10][:,:,:,:,[9,4,3]].mean((0,1,2,3,5,6)),'test',sr[...,10:][:,:,:,:,[9,4,3]].mean((0,1,2,3,5,6)))
# per cell test-half table: T,h,tau gap: rule, fix8, fix6.5, table eta and SR for all eta
s=scoreM(sr[...,:10].mean((5,6)),sr[...,10:].mean((5,6))); tab=s['tab']
print('cell T h tau | rule fix8 fix6.5 table(eta) sel-best oracle | all half SR by eta (gap-averaged), last=rule')
te=sr[...,10:].mean((5,6)).mean(3); se=sr[...,:10].mean((5,6)).mean(3); al=sr.mean((3,5,6))
gaps=[]
for i,j,l in np.ndindex(3,4,3):
    print(TT[i],int(H[j]*1e3),int(L[l]*1e3),'| r %.2f f8 %.2f f65 %.2f tab %.2f(%g) orc %.2f M %+.3f'%(te[i,j,l,9],te[i,j,l,4],te[i,j,l,3],te[i,j,l,tab[i,j,l]],E[tab[i,j,l]],te[i,j,l,:9].max(),te[i,j,l,tab[i,j,l]]-te[i,j,l,9]),'| all',al[i,j,l])
# M contribution by cell
M=np.array([[[te[i,j,l,tab[i,j,l]]-te[i,j,l,9] for l in range(3)] for j in range(4)] for i in range(3)])
print('M by T x h x tau (x100/36 is contribution)\n',M)
print('sum',M.sum(),'mean',M.mean())
print('top M cells',sorted([(round(M[i,j,l],3),TT[i],H[j],L[l]) for i,j,l in np.ndindex(3,4,3)],reverse=True)[:6])
print('bottom',sorted([(round(M[i,j,l],3),TT[i],H[j],L[l]) for i,j,l in np.ndindex(3,4,3)])[:6])
# by hole
print('by hole: rule fix8 fixS table')
for hh in range(5):
    t2=sr[:,:,:,:,:,hh,10:].mean(5)
    I=np.indices(tab.shape)
    print(hh,t2[...,9].mean(),t2[...,4].mean(),t2[...,3].mean(),t2[...,:9].mean(3)[I[0],I[1],I[2],tab].mean())
# leave one out, point estimates: reselect
def rep(mask_fn,label):
    pass
print('LOHO: remove hole -> point diffs')
for hh in range(5):
    k=[x for x in range(5) if x!=hh]; a=o[:,:,:,:,:,k]
    s=scoreM(a[...,:10].astype(float).mean((5,6)),a[...,10:].astype(float).mean((5,6)))
    q=boot(a,500,seed=1)
    print(hh,'r-8 %.3f r-S %.3f M %.3f etaS %g'%(s['RULE']-s['FIX8'],s['RULE']-s['FIXS'],s['TABLE']-s['RULE'],E[s['f']]),'q',np.round(q,3).tolist(),outcome(s,q))
print('LOTO: remove T')
for iT in range(3):
    k=[x for x in range(3) if x!=iT]; a=o[k]
    s=scoreM(a[...,:10].astype(float).mean((5,6)),a[...,10:].astype(float).mean((5,6)))
    q=boot(a,500,seed=1); print(TT[iT],'r-8 %.3f r-S %.3f M %.3f etaS %g'%(s['RULE']-s['FIX8'],s['RULE']-s['FIXS'],s['TABLE']-s['RULE'],E[s['f']]),'q',np.round(q,3).tolist(),outcome(s,q))
print('only T: ')
for iT in range(3):
    a=o[[iT]]
    s=scoreM(a[...,:10].astype(float).mean((5,6)),a[...,10:].astype(float).mean((5,6)))
    q=boot(a,500,seed=1); print(TT[iT],'r-8 %.3f r-S %.3f M %.3f etaS %g'%(s['RULE']-s['FIX8'],s['RULE']-s['FIXS'],s['TABLE']-s['RULE'],E[s['f']]),'q',np.round(q,3).tolist(),outcome(s,q))
print('only gap:')
for g in range(2):
    a=o[:,:,:,[g]]
    s=scoreM(a[...,:10].astype(float).mean((5,6)),a[...,10:].astype(float).mean((5,6)))
    q=boot(a,500,seed=1); print(G[g],'r-8 %.3f r-S %.3f M %.3f etaS %g'%(s['RULE']-s['FIX8'],s['RULE']-s['FIXS'],s['TABLE']-s['RULE'],E[s['f']]),'q',np.round(q,3).tolist(),outcome(s,q))
print('drop h level:')
for j in range(4):
    k=[x for x in range(4) if x!=j]; a=o[:,k]
    s=scoreM(a[...,:10].astype(float).mean((5,6)),a[...,10:].astype(float).mean((5,6)))
    q=boot(a,500,seed=1); print(H[j],'r-8 %.3f r-S %.3f M %.3f etaS %g'%(s['RULE']-s['FIX8'],s['RULE']-s['FIXS'],s['TABLE']-s['RULE'],E[s['f']]),'q',np.round(q,3).tolist(),outcome(s,q))
print('drop tau level:')
for j in range(3):
    k=[x for x in range(3) if x!=j]; a=o[:,:,k]
    s=scoreM(a[...,:10].astype(float).mean((5,6)),a[...,10:].astype(float).mean((5,6)))
    q=boot(a,500,seed=1); print(L[j],'r-8 %.3f r-S %.3f M %.3f etaS %g'%(s['RULE']-s['FIX8'],s['RULE']-s['FIXS'],s['TABLE']-s['RULE'],E[s['f']]),'q',np.round(q,3).tolist(),outcome(s,q))
# drop (15,0) cells
# ties
sa=sr[...,:10].mean((5,6)); ta=sr[...,10:].mean((5,6))
s2=scoreM(sa,ta,'last'); print('tie last M',s2['TABLE']-s2['RULE'],'fixS',E[s2['f']], 'ORT-FIX8',s2['ORT']-s2['FIX8'])
print('n ties in table',sum(((sa[...,:9].mean(3)[i,j,l]==sa[...,:9].mean(3)[i,j,l].max()).sum()>1) for i,j,l in np.ndindex(3,4,3)))
qt=boot(o,2000,seed=5,tie='last'); print('tie last boot',np.round(qt,4).tolist())
# swap
s3=scoreM(ta,sa); print('swap: r-8 %.3f r-S %.3f M %.3f etaS %g orc-8 %.3f'%(s3['RULE']-s3['FIX8'],s3['RULE']-s3['FIXS'],s3['TABLE']-s3['RULE'],E[s3['f']],s3['ORACLE']-s3['FIX8']))
oo=np.concatenate([o[...,10:],o[...,:10]],axis=-1); qs=boot(oo,2000,seed=5); print('swap boot',np.round(qs,4).tolist(),outcome(s3,qs))
# c sweep
print('c sweep: c r f8 fS tab orc  r-8 r-S M  q outcome')
for c in [.001,.002,.003,.004,.0045,.005,.0055,.006,.007,.008,.009,.01,.015]:
    a=ok(D,c); s=scoreM(a[...,:10].astype(float).mean((5,6)),a[...,10:].astype(float).mean((5,6))); q=boot(a,1000,seed=3)
    print(c,'%.3f %.3f %.3f %.3f %.3f | %.3f %.3f %.3f etaS %g'%(s['RULE'],s['FIX8'],s['FIXS'],s['TABLE'],s['ORACLE'],s['RULE']-s['FIX8'],s['RULE']-s['FIXS'],s['TABLE']-s['RULE'],E[s['f']]),np.round(q,3).tolist(),outcome(s,q))
