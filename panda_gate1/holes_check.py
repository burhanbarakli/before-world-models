"""Kinematic margins of candidate hole layouts along the reference, no episodes run."""
import numpy as np
import robot as Rb
LOW = np.array([-2.9671,-1.8326,-2.9671,-3.1416,-2.9671,-0.0873,-2.9671]); HIGH = np.array([2.9671,1.8326,2.9671,0.0,2.9671,3.8223,2.9671])
rb = Rb.Panda()
for h in [(0.38,-0.16),(0.42,-0.08),(0.46,0.0),(0.42,0.08),(0.38,0.16),(0.40,0.0),(0.36,0.0)]:
    ref = Rb.reference_for(rb, h, 8.0); Rb.ref_q0(rb, ref); mg=[]; s=[]
    for j in range(0,len(ref.p),50):
        rb.ik(ref.R[j],ref.p[j]); q=rb.q(); mg.append(np.minimum(q-LOW,HIGH-q).min()); s.append(np.linalg.svd(rb.jacobian(),compute_uv=False).min())
    print(h,'margin %.3f smin %.3f end smin %.3f'%(min(mg),min(s),s[-1]))
