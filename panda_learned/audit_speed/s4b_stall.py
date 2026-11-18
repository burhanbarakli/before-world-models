import numpy as np
from common import *
D,U,K=load(); ei=K.index("end_z"); pi=K.index("end_p")
ez=D[...,ei]; deep=(RIM-ez)>=.9*DEPTH
print("und end_z>0.196 by arm:",[(~((RIM-U[i,:,:,:,:,0,:,ei])>=.054)).sum() for i in range(5)], "of",U[0,:,:,:,:,0,:,0].size)
print("und shallow weak cells:",[(PERIOD[a],DELAY[b],LAG[c],GAP[d],h,round(float(U[3,a,b,c,d,0,h,ei]),3)) for a,b,c,d,h in np.argwhere(~((RIM-U[3,:,:,:,:,0,:,ei])>=.054))])
for arm in range(5):
  for o in range(5):
    s=~deep[arm,:,:,:,:,o]
    if s.any():
      print(ARMS[arm],"opt",OPT[o],"shallow frac",round(float(s.mean()),4),"by T",np.round(s.mean((1,2,3,4,5)),4),"by(h,tau=0..):",np.round(s.mean((0,3,4,5)),3).tolist(),"by hole",np.round(s.mean((0,1,2,3,5)),3))
      e=ez[arm,:,:,:,:,o][s]; print("   end_z of shallow runs: min %.3f med %.3f max %.3f; frac>rim %.3f"%(e.min(),np.median(e),e.max(),(e>RIM).mean()))
# which (cell,hole) produce the stall in weak L=.01
s=~deep[3]
for o in [0,1]:
  x=s[:,:,:,:,o].mean(-1)
  idx=np.argwhere(x>0)
  print("opt",OPT[o],"cells",len(idx),[(PERIOD[a],DELAY[b],LAG[c],GAP[d],int(h),round(float(x[a,b,c,d,h]),2),round(float(ez[3,a,b,c,d,o,h].mean()),3)) for a,b,c,d,h in idx][:30])
# no-gate vs gate end distance, a proxy of residual time cost, paper arm successes
for o in range(1,5):
  a=D[[0,1,2],:,:,:,:,o,:,:,pi]; b=D[[0,1,2],:,:,:,:,0,:,:,pi]
  print("end_p mm median none",round(float(np.median(b))*1e3,3),"opt",OPT[o],round(float(np.median(a))*1e3,3),"max",round(float(a.max())*1e3,2))
