import sys,time,json
sys.dont_write_bytecode=True
sys.path.insert(0,"./panda_gate1")
import numpy as np, gate_rule as GR
order=sys.argv[1]; out=sys.argv[2]
D=np.load("./panda_gate1/results/gate_rule.npz")['data']
J=[(4.0,.015,0.0,.25,9),(4.0,.015,0.0,.25,8),(6.0,.07,.025,.4,9),(8.0,.09,.04,.25,9),(8.0,.035,.025,.4,3),(6.0,.035,.04,.25,4)]
if order=='rev': J=J[::-1]
res=[]
for j in J:
    t0=time.time(); r=GR.work(j)
    idx=(GR.PERIOD.index(j[0]),GR.DELAY.index(j[1]),GR.LAG.index(j[2]),GR.GAP.index(j[3]),j[4])
    s=D[idx]; d=np.abs(r-s)
    print(j,'exact',np.array_equal(r,s),'max|d|',d.max(),'nmismatch',(r!=s).sum(),'t',round(time.time()-t0,1),flush=True)
