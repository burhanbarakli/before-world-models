import sys,itertools,multiprocessing as mp
sys.dont_write_bytecode=True
sys.path.insert(0,"./panda_gate1")
import numpy as np, gate_rule as GR
ndt=lambda h: int(round(h/0.01))*0.01
GR.rule=lambda h,tau: min(20.0,0.6/(ndt(h)+tau))
def f(j):
    return GR.work(j)
if __name__=="__main__":
    cells=[(.015,.025),(.015,.04),(.035,0.0),(.035,.025),(.035,.04)]
    jobs=[(T,h,t,g,9) for T in GR.PERIOD for h,t in cells for g in GR.GAP]
    print([ (h,t,GR.rule(h,t)) for h,t in cells],flush=True)
    with mp.Pool(4) as pool:
        res=[]
        for i,r in enumerate(pool.imap(f,jobs,chunksize=1)):
            res.append(r); print(i,flush=True); np.savez('heff.npz',jobs=np.array(jobs),res=np.array(res))
