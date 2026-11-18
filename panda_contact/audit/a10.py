import numpy as np
d=np.load("./panda_contact/results/exp_contact.npz")
D=d["data"]; keys=list(d["keys"])
for idx in [(3,0,0,0,3,1,1,0,3),(3,0,0,0,3,1,1,0,6),(3,0,2,1,3,0,2,0,5)]:
    print(idx, {k:round(float(D[idx][i]),4) for i,k in enumerate(keys)})
