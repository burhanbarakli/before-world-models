"""Ungated undisturbed run for every arm,T,h,tau,hole: per-tick pose and |c|. No disturbance, project field."""
import sys,time; sys.dont_write_bytecode=True
import irun as I, numpy as np, multiprocessing as mp, pickle, itertools
import robot as Rb
def one(j):
    arm,T,h,tau=j
    if I.ROBOT is None: I.ROBOT=Rb.Panda()
    eta=I.Gr.rule(h,tau); out=[]
    for ih in range(5):
        hole,ref,f=I.base(arm,T,h,tau,ih)
        r=I.irun(I.ROBOT,I.gated(f,0),hole,eta,h,tau,None,T+4.,trace=True)
        out.append(dict(t_rim=r["t_rim"],tr=r["trace"].astype(np.float32),rim_i=I.Gg.rim_index(ref),dt=ref.dt))
    return j,out
if __name__=="__main__":
    J=list(itertools.product(I.Gl.ARMS,I.Gl.PERIOD,I.Gl.DELAY,I.Gl.LAG))
    t=time.time()
    with mp.Pool(8) as P: res=P.map(one,J,chunksize=1)
    pickle.dump(dict(res),open("traces.pkl","wb")); print("done",time.time()-t,len(res))
