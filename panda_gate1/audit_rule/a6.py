import sys; sys.path.insert(0,sys.argv[1])
from lib import *
for (j,l,e,n) in [(1,1,5,'h35 t25 ~eta10'),(1,2,4,'h35 t40 ~eta8')]:
    a=ok(D[:,j,l,:,9],.005);b=ok(D[:,j,l,:,e],.005); print(n,'success flips',(a!=b).sum(),'of',a.size, 'max lat diff',np.abs(D[:,j,l,:,9,:,:,0]-D[:,j,l,:,e,:,:,0]).max())
o=ok(D,.005).astype(float)
s=scoreM(o[...,:10].mean((5,6)),o[...,10:].mean((5,6)))
print('test-half SR by eta',np.round(o[...,10:].mean((0,1,2,3,5,6)),3))
print('all-seed SR by eta',np.round(o.mean((0,1,2,3,5,6)),3))
# conditional on feasible
f=o.max(4,keepdims=True)>0
print('feasible frac',f.mean())
# gap x T
print('rule/8/table by T x gap')
