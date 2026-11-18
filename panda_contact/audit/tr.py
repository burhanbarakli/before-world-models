import sys, time
sys.path.insert(0,"./panda_contact")
import contact as C, exp_contact as X
import numpy as np
rob=C.Panda()
REC=[]
orig=C.Shift.update
def upd(self,t,z,fz,dt):
    s=orig(self,t,z,fz,dt)
    R,pos=rob.pose()
    REC.append((t,pos[0],pos[1],pos[2],self.s[0],self.s[1],fz,self.state))
    return s
C.Shift.update=upd
def ep(arm,ti,dl,g,ei,ci,pol,h,si,show=True):
    REC.clear()
    T=X.PERIOD[ti]; hh,tau=X.DELAYS[dl]
    t0=time.time()
    r=X.episode(rob,X.ARMS[arm],T,hh,tau,X.GAPS[g],X.ERRORS[ei],C.CLEARANCES[ci],X.POLICIES[pol],h,X.SEEDS[si])
    u=X.draw(h,X.SEEDS[si],T)[0]; e=X.ERRORS[ei]*u; hole=np.array(X.Gr.HOLES[h]); true=hole+e[:2]
    A=np.array([x[:7] for x in REC]); st=[x[7] for x in REC]
    if show:
        print(f"--- arm{arm} T{T} dl{dl} g{g} e{X.ERRORS[ei]} c{C.CLEARANCES[ci]} {X.POLICIES[pol]} h{h} s{X.SEEDS[si]}  ({time.time()-t0:.1f}s)")
        print("   result:",{k:(round(v,4) if isinstance(v,float) else v) for k,v in r.items()})
        for k in range(0,len(A),50):
            tip=A[k,1:3]; s=A[k,4:6]
            print(f"   t{A[k,0]:5.2f} z-rim {1000*(A[k,3]-.25):7.2f}mm  tip-true {1000*np.linalg.norm(tip-true):5.2f}  shat-e {1000*np.linalg.norm(s-e[:2]):5.2f}  tip-(hole+shat) {1000*np.linalg.norm(tip-hole-s):5.2f}  fz {A[k,6]:6.2f} {st[k]}")
    return r,A,st,true,hole,e
