"""Re-run 8 jobs through the unmodified project work() and compare bits. Writes nothing to the project."""
import sys,time,os,hashlib
sys.dont_write_bytecode=True
R="."
sys.path.insert(0,R+"/panda_learned")
import gate_speed as gs
import gate_learned as Gl
import numpy as np, multiprocessing as mp
JOBS=[(0,8.,.09,.04,.25,2),(1,4.,.02,0.,.4,0),(2,8.,.07,.025,.25,1),(3,8.,.02,0.,.25,1),
      (3,4.,.04,.04,.4,3),(None,8.,.09,.025,.25,0),(None,8.,.02,.04,.4,2),(None,4.,.07,0.,.25,4)]
def timed(j):
    t=time.time(); r=gs.work(j); return j,r,time.time()-t
if __name__=="__main__":
    z=np.load(R+"/panda_learned/results/gate_speed.npz"); D,U=z["data"],z["und"]
    with mp.Pool(8) as pool:
        for j,(o,u),dt in pool.imap(timed,JOBS,chunksize=1):
            ix=(Gl.ARMS.index(j[0]),Gl.PERIOD.index(j[1]),Gl.DELAY.index(j[2]),Gl.LAG.index(j[3]),Gl.GAP.index(j[4]),j[5])
            print(j,"idx",ix,"bits equal data:",np.array_equal(o,D[ix]),"und:",np.array_equal(u,U[ix]),
                  "maxabs",float(np.abs(o-D[ix]).max()),"n_diff",int((o!=D[ix]).sum()),f"{dt:.0f}s",flush=True)
