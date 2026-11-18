import numpy as np
P="./panda_gate1/results/gate_rule.npz"
Z=np.load(P); print(Z.files, Z['data'].shape, Z['data'].dtype, Z['keys'])
D=Z['data']; keys=[str(k) for k in Z['keys']]
print("nan",np.isnan(D).sum(),"inf",np.isinf(D).sum())
RIM,DEP=0.25,0.06
def ok(D,c):
    lat=D[...,keys.index('lat')];tilt=D[...,keys.index('tilt')];z=D[...,keys.index('end_z')]
    return (z<=RIM-0.9*DEP)&(lat<=c)&(tilt<=np.arctan2(2*c,DEP))
E=[3,4,5,6.5,8,10,12,16,20]
def S(o):
    sel=o[...,:10].astype(float);te=o[...,10:].astype(float)
    # manual loops
    r={}
    nT,nh,nt,ng,ne,_,_=o.shape
    r['RULE']=te[:,:,:,:,9].mean(); r['FIX8']=te[:,:,:,:,4].mean()
    m=[sel[:,:,:,:,i].mean() for i in range(9)]; f=int(np.argmax(m)); r['FIXS']=te[:,:,:,:,f].mean(); r['fixeta']=E[f]; r['selmeans']=np.round(m,3)
    tot=0;cnt=0;tab=np.zeros((nT,nh,nt),int)
    for i in range(nT):
      for j in range(nh):
        for l in range(nt):
          ms=[sel[i,j,l,:,e].mean() for e in range(9)]
          b=int(np.argmax(ms));tab[i,j,l]=b
          tot+=te[i,j,l,:,b].mean();cnt+=1
    r['TABLE']=tot/cnt
    orc=0;n=0
    for i,j,l,g in np.ndindex(nT,nh,nt,ng):
        orc+=max(te[i,j,l,g,e].mean() for e in range(9));n+=1
    r['ORACLE']=orc/n
    return r,tab
for c in (.005,.002,.01):
    r,tab=S(ok(D,c))
    print(c,{k:(round(float(v),4) if np.isscalar(v) else v) for k,v in r.items()})
    print(' RULE-FIX8 %.4f RULE-FIXS %.4f M %.4f ORACLE-FIX8 %.4f'%(r['RULE']-r['FIX8'],r['RULE']-r['FIXS'],r['TABLE']-r['RULE'],r['ORACLE']-r['FIX8']))
    if c==.005: print(np.array(E)[tab])
# exact equality rule vs grid
print("rule etas")
h=[.015,.035,.07,.09];t=[0,.025,.04]
for j in range(4):
  print([min(20,.6/(h[j]+t[l])) for l in range(3)])
for (j,l,e,name) in [(0,0,8,'h15t0 eta20'),(1,1,5,'h35t25 eta10'),(1,2,4,'h35t40 eta8')]:
    a=D[:,j,l,:,9];b=D[:,j,l,:,e]
    print(name,'exact',np.array_equal(a,b),'maxabsdiff',np.abs(a-b).max(),'frac exact',(a==b).mean())
    for c in (.005,):
        print('  ok-differ',(ok(a[None,None,None],c)!=ok(b[None,None,None],c)).sum() if False else '')
