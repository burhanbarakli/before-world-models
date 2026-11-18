"""Time cost of the gate: t_rim and t_deep, test seeds, spread of cells; model 0 and analytic."""
import sys,time,pickle,itertools; sys.dont_write_bytecode=True
import irun as I, numpy as np, multiprocessing as mp, robot as Rb
def job(j):
    arm,T,h,tau,gap,opt=j
    if I.ROBOT is None: I.ROBOT=Rb.Panda()
    eta=I.Gr.rule(h,tau); tf=T+4.; out=np.zeros((5,10,len(I.FIELDS))); clean=np.zeros((5,len(I.FIELDS)))
    for ih in range(5):
        hole,ref,f=I.base(arm,T,h,tau,ih)
        r0=I.irun(I.ROBOT,I.gated(f,0),hole,eta,h,tau,None,tf)
        t_d=(ref.dt*I.Gg.rim_index(ref)+h+tau if r0["t_rim"] is None else r0["t_rim"])-gap
        clean[ih]=I.vec(I.irun(I.ROBOT,I.gated(f,opt),hole,eta,h,tau,None,tf))
        for i,s in enumerate(range(10,20)):
            w,v=I.Gr.draw(I.ROBOT,ref,ih,s,gap)
            out[ih,i]=I.vec(I.irun(I.ROBOT,I.gated(f,opt),hole,eta,h,tau,(t_d,w,v),tf))
    return j,out,clean
if __name__=="__main__":
    J=[(0,T,h,tau,g,o) for (T,g) in [(8.,.25),(8.,.4),(4.,.25),(4.,.4)] for (h,tau) in [(.02,0.),(.07,.025),(.09,.04)] for o in (0,2)]
    t=time.time()
    with mp.Pool(8) as P: res=P.map(job,J,chunksize=1)
    pickle.dump(res,open("time.pkl","wb")); print("done",time.time()-t)
