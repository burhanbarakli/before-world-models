import numpy as np
d=np.load("./panda_contact/results/exp_contact.npz")
for k in d.files: print(k, d[k].shape if d[k].ndim else d[k], d[k] if d[k].size<20 else '')
D=d["data"]; keys=list(d["keys"])
print("nan count per policy/e/c:")
for c in range(2):
  for e in range(4):
    print(c,e,[int(np.isnan(D[:,:,:,:,e,c,p,:,:,0]).sum()) for p in range(3)])
