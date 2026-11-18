"""Height-triggered reruns. Only runs whose gated path differs from the ungated one before t_d can change;
of those, re-run every gate-rescued run, plus a random sample of the others to test that they do not flip."""
import sys,time,pickle; sys.dont_write_bytecode=True
import irun as I, numpy as np, multiprocessing as mp, robot as Rb
from collections import defaultdict
from common import *
def task(t):
    (arm,T,h,tau,gap,ih,opt),seeds,t_z=t
    if I.ROBOT is None: I.ROBOT=Rb.Panda()
    eta=I.Gr.rule(h,tau); hole,ref,f=I.base(arm,T,h,tau,ih); out=[]
    for s in seeds:
        w,v=I.Gr.draw(I.ROBOT,ref,ih,s,gap)
        out.append(I.vec(I.irun(I.ROBOT,I.gated(f,opt),hole,eta,h,tau,(t_z,w,v),T+4.,mode="z")))
    return t[0],seeds,np.array(out)
if __name__=="__main__":
    D,U,K=load(); OK=succ(D,K); r=np.load("rim.npz"); pre=r["pre"]; tr=pickle.load(open("traces.pkl","rb"))
    rng=np.random.default_rng(5); g=defaultdict(list); kind={}
    for ia in [0,1,2,4]:
      for o in (1,2):
        io=o-1
        for ix in np.ndindex(2,4,3,2,5):
            if pre[(ia,)+ix+(io,)]==0: continue
            it,ih,il,ig,ho=ix
            for s in range(20):
                res=OK[ia,it,ih,il,ig,o,ho,s] and not OK[ia,it,ih,il,ig,0,ho,s]
                other=rng.random()<.03
                if res or other:
                    g[(ia,it,ih,il,ig,ho,o)].append(s); kind[(ia,it,ih,il,ig,ho,o,s)]=res
    J=[]
    for (ia,it,ih,il,ig,ho,o),ss in g.items():
        a=I.Gl.ARMS[ia]; T,h,tau,gp=PERIOD[it],DELAY[ih],LAG[il],GAP[ig]
        e=tr[(a,T,h,tau)][ho]; t=e["tr"]
        t_d=(e["dt"]*e["rim_i"]+h+tau if e["t_rim"] is None else e["t_rim"])-gp
        k=int(np.argmax(t[:,0]>=t_d-1e-9))
        J.append(((a,T,h,tau,gp,ho,o),ss,float(t[k,3])))
    print("tasks",len(J),"runs",sum(len(x[1]) for x in J),flush=True); t0=time.time()
    with mp.Pool(8) as P: res=P.map(task,J,chunksize=4)
    pickle.dump(dict(res=res,kind=kind),open("height.pkl","wb")); print("done",time.time()-t0)
