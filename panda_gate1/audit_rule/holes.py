import sys
sys.dont_write_bytecode=True
sys.path.insert(0,"./panda_gate1")
import numpy as np, gate_rule as GR, robot as Rb
LOW=np.array([-2.9671,-1.8326,-2.9671,-3.1416,-2.9671,-0.0873,-2.9671]);HIGH=np.array([2.9671,1.8326,2.9671,0.0,2.9671,3.8223,2.9671])
rb=Rb.Panda()
for hole in GR.HOLES:
  for T in (8.,):
    ref=Rb.reference_for(rb,hole,T);Rb.ref_q0(rb,ref);mg=[];s=[]
    for j in range(0,len(ref.p),50):
        rb.ik(ref.R[j],ref.p[j]);q=rb.q();mg.append(np.minimum(q-LOW,HIGH-q).min());s.append(np.linalg.svd(rb.jacobian(),compute_uv=False).min())
    print(hole,T,'margin %.3f smin %.3f'%(min(mg),min(s)))
