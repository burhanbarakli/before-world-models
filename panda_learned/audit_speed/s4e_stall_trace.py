"""Weak arm, hole 2, L=.01: is the stall a true fixed point of alpha m + eta c?"""
import sys; sys.dont_write_bytecode=True
import irun as I, numpy as np, robot as Rb, field_se3 as F
I.ROBOT=Rb.Panda()
for arm,T,h,tau,ih,lo in [(3,8.,.04,.0,2,1),(3,8.,.04,.0,2,2),(3,4.,.02,.0,2,1),(0,8.,.04,.0,2,1),(3,8.,.02,.0,0,0)]:
    hole,ref,f=I.base(arm,T,h,tau,ih); eta=I.Gr.rule(h,tau); g=I.gated(f,lo)
    r=I.irun(I.ROBOT,g,hole,eta,h,tau,None,T+4.,trace=True); t=r["trace"]
    print(f"arm {arm} T {T} h {h} hole {ih} opt {lo} eta {eta}: end_z {r['end_z']:.4f} t_rim {r['t_rim']} t_deep {r['t_deep']} n_stop {r['n_stop']}")
    for k in np.linspace(0,len(t)-1,9).astype(int): print("   t %.2f z %.4f d %.4f a %.3f"%(t[k,0],t[k,3],t[k,4],t[k,5]))
    # field balance at the end of the run
    R,p=I.ROBOT.pose(); c,m,_,_=f.field(R,p); a=g.a
    cn,mn=F.norm(*c),F.norm(*m)
    dot=(2*c[0]@m[0]+100*c[1]@m[1])/(cn*mn+1e-12)
    res=F.norm(a*m[0]+eta*c[0],a*m[1]+eta*c[1])
    print(f"   end: |c| {cn:.4f} |m| {mn:.4f} cos(c,m) {dot:.3f} a {a:.3f} |a m+eta c| {res:.4f}  true D {F.distance(R,p,*[ref.R[ref.nearest(R,p)[0]],ref.p[ref.nearest(R,p)[0]]]):.4f} true lateral mm {1e3*np.hypot(p[0]-hole[0],p[1]-hole[1]):.2f}")
