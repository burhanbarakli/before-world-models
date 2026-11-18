import numpy as np
d=np.load("./panda_contact/results/exp_contact.npz")
D=d["data"]; keys=list(d["keys"]); K=lambda n: D[...,keys.index(n)]
ez,jam,deep,lat,ok,fm=K("end_z"),K("jam"),K("deep"),K("lat"),K("ok"),K("f_max")
P=slice(0,3)
for e in (1,2,3):
  m=deep[P,:,:,:,e,1,1]==0
  z=ez[P,:,:,:,e,1,1][m]; j=jam[P,:,:,:,e,1,1][m]
  above=z>0.25-0.001
  print(f"c2 e{e} REFLEKS notdeep {m.mean():.3f}: never entered {above.mean():.2f}, entered&stalled(jam) {((~above)&(j==1)).mean():.2f}, entered&still moving {((~above)&(j==0)).mean():.2f}")
m=deep[P,:,:,:,1:,0,1]==0; z=ez[P,:,:,:,1:,0,1][m]; j=jam[P,:,:,:,1:,0,1][m]; above=z>0.249
print(f"c5 REFLEKS notdeep n={m.sum()}: never entered {above.mean():.2f}, entered&jam {((~above)&(j==1)).mean():.2f}, moving {((~above)&(j==0)).mean():.2f}")
# KAHIN over F example indices: arm3 T8 dl2 gap1
x=fm[3,0,2,1,3,0,2]; print("KAHIN over examples (h,s,fmax):",[(h,s,round(float(x[h,s]),1)) for h in range(5) for s in range(20) if x[h,s]>50][:5])
# W per (T,delay) cell incl gap
for ti in range(2):
  for dl in range(3):
    y=ok[P,ti,dl,:,1:,0]; print("T",[8,4][ti],"dl",dl,"W",round(float(y[...,2,:,:].mean()-y[...,1,:,:].mean()),3),"S_R",round(float(y[...,1,:,:].mean()),3))
