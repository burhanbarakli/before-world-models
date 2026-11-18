import sys
sys.path.insert(0,"./panda_contact")
import contact as C, exp_contact as X
import numpy as np
d=np.load("./panda_contact/results/exp_contact.npz")
D=d["data"]; keys=list(d["keys"]); K=lambda n: D[...,keys.index(n)]
ok,deep,tc,jam,ez,se=K("ok"),K("deep"),K("t_contact"),K("jam"),K("end_z"),K("s_err")
v_s=C.V_S
def t_pass(phi,e,c):
    b=2*c/(2*np.pi); best=None
    # first k where spiral radius at angle phi+2pi k within c of e  (r in [e-c, e+c])
    for k in range(10):
        th=phi+2*np.pi*k; r=b*th
        if abs(r-e)<=c*0.999 or r>e:  # first pass at or beyond
            L=b/2*(th*np.sqrt(1+th**2)+np.arcsinh(th)); return L/v_s, r
    return np.inf,None
for c_i,c in enumerate([0.005,0.002]):
  for e_i in (2,3):
    e=d["errors"][e_i]
    rows=[]
    for ti,T in enumerate([8.0,4.0]):
      tf=T+8
      for h in range(5):
        for si,s in enumerate(X.SEEDS):
          u=X.draw(h,s,T)[0]; phi=np.arctan2(u[1],u[0])%(2*np.pi)
          tp,r=t_pass(phi,e,c)
          for a in range(3):
            for dl in range(3):
              for g in range(2):
                t0=tc[a,ti,dl,g,e_i,c_i,1,h,si]
                rows.append((tf-t0-tp, deep[a,ti,dl,g,e_i,c_i,1,h,si], ok[a,ti,dl,g,e_i,c_i,1,h,si], t0))
    R=np.array(rows)
    print(f"c={c*1000:.0f} e={e*1000:.0f}: REFLEKS deep {R[:,1].mean():.3f}; slack quantiles", np.round(np.percentile(R[:,0],[5,25,50,75,95]),2))
    for lo,hi in [(-99,-2),(-2,0),(0,2),(2,4),(4,99)]:
        m=(R[:,0]>=lo)&(R[:,0]<hi)
        if m.sum(): print(f"   slack [{lo},{hi}) s: n={m.sum():5d} deep {R[m,1].mean():.3f} ok {R[m,2].mean():.3f}")
