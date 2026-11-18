import numpy as np
d=np.load("./panda_contact/results/exp_contact.npz")
D=d["data"]; keys=list(d["keys"]); K=lambda n: D[...,keys.index(n)]
# c=2 e=10 REFLEKS analytic arm(3) , T idx, delay0, gap0: list failing and succeeding seeds
for ti in (0,1):
  x=K("ok")[3,ti,0,0,3,1,1]; print("T",ti,"fail (hole,seed):",[(h,s) for h in range(5) for s in range(20) if x[h,s]==0][:12])
  print("   end_z-rim mm of fails", [round(float((K('end_z')[3,ti,0,0,3,1,1,h,s]-.25)*1000),1) for h in range(5) for s in range(20) if x[h,s]==0][:12])
