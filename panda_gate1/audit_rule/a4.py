import sys,itertools
sys.dont_write_bytecode=True
sys.path.insert(0,"./panda_gate1")
import numpy as np, gate_rule as GR, robot as Rb, gate1g as Gg, gate1 as G1, field_se3 as F
rb=Rb.Panda()
# 1. all draws: redraw count, comparison with earlier streams, gap coupling
W={}
red=0;tot=0
for T,gap,(ih,hole),s in itertools.product(GR.PERIOD,GR.GAP,enumerate(GR.HOLES),range(20)):
    ref=Rb.reference_for(rb,hole,T)
    w,v=GR.draw(rb,ref,ih,s,gap); W[(T,gap,ih,s)]=np.r_[w,v]
    rng=np.random.default_rng([ih,30,s,int(T)]); w0,v0=Rb.disturbance(rng,Gg.SCALE)
    tot+=1; red+= not np.allclose(np.r_[w0,v0],W[(T,gap,ih,s)])
print('draws',tot,'with at least one redraw',red)
same=[np.array_equal(W[(T,.4,i,s)],W[(T,.25,i,s)]) for T in GR.PERIOD for i in range(5) for s in range(20)]
print('same direction across gaps',np.mean(same))
# metric norm
print('norm',set(np.round([F.norm(x[:3],x[3:]) for x in W.values()],9).tolist()))
# overlap with old streams
old=[]
for T in (8,4):
  for i in range(5):
    for s in range(20):
      r=np.random.default_rng([i,20,s,T]); w,v=Rb.disturbance(r,.2); old.append(np.r_[w,v])
    for k in (0,1):
      for s in range(10):
        r=np.random.default_rng([i,k,s,T]); w,v=Rb.disturbance(r,.2 if k else .5); old.append(np.r_[w,v])
new=np.array(list(W.values())); old=np.array(old)
dot=np.abs(new@old.T/np.linalg.norm(new,axis=1,keepdims=True)/np.linalg.norm(old,axis=1)[None]); print('max |cos| new vs old directions',dot.max())
# 2. draw invariance after arbitrary sim state: run an episode with different eta/h then draw
ref=Rb.reference_for(rb,GR.HOLES[2],6.0)
base=GR.draw(rb,ref,2,7,.25)
for eta,h,tau in [(3,.09,.04),(20,.015,0),(GR.rule(.07,.025),.07,.025)]:
    Rb.run(rb,ref,GR.HOLES[2],eta,h,tau,None,tf=2.0)
    b=GR.draw(rb,ref,2,7,.25); print('draw invariant',np.array_equal(b[0],base[0]) and np.array_equal(b[1],base[1]))
# 3. runtime IK error at disturbance, jump below rim, effective position: instrumented on 3 cells for rule and eta 8
orig_ik=Rb.Panda.ik
log=[]
def ik2(self,R_t,p_t,iters=200):
    e=orig_ik(self,R_t,p_t,iters); log.append((e,float(self.pose()[1][2]))); return e
for (T,h,tau,gap) in [(8.0,.09,.04,.25),(6.0,.035,.025,.25),(4.0,.07,.04,.25)]:
  for ie in (9,4):
    eta=GR.rule(h,tau) if ie==9 else GR.ETA[ie]
    errs=[];below=[]
    for ih,hole in enumerate(GR.HOLES):
        ref=Rb.reference_for(rb,hole,T)
        t_rim=Rb.run(rb,ref,hole,eta,h,tau,None,tf=T+4)['t_rim']
        t_d=t_rim-gap
        for s in range(0,20,4):
            w,v=GR.draw(rb,ref,ih,s,gap)
            Rb.Panda.ik=ik2; log.clear()
            r=Rb.run(rb,ref,hole,eta,h,tau,(t_d,w,v),tf=T+4)
            Rb.Panda.ik=orig_ik
            # first ik call(s): ref_q0 then disturbance
            e=log[-1]; errs.append(max(e[0])); below.append(e[1]<Rb.RIM_Z)
    print(T,h,tau,gap,ie,'max IK err m/rad %.2e'%max(errs),'frac jump below rim',np.mean(below))
