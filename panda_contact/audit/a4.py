import sys,os
sys.path.insert(0,"./panda_contact")
import contact as C
import numpy as np, exp_contact as X, gate_rule as Gr, robot as Rb, gate1g as Gg
rob=C.Panda()
for T in (8.0,4.0):
  for ih,hole in enumerate(Gr.HOLES):
    ref=Rb.reference_for(rob,hole,T)
    zp=C.push_height(ref,0.25); ri=Gg.rim_index(ref)
    print(T,ih,"rim idx",ri,"len",len(ref.p),"dt",ref.dt,"push z-rim mm",round((zp-Rb.RIM_Z)*1000,2))
vs=[]
for ih in range(5):
  for s in X.SEEDS:
    u,mu,w,v,ns=X.draw(ih,s,8.0); vs.append((np.linalg.norm(v),np.linalg.norm(w),v[2]))
vs=np.array(vs); print("push |v| m mean/max",vs[:,0].mean(),vs[:,0].max()," |w| rad mean",vs[:,1].mean()," v_z (body) mean",vs[:,2].mean())
