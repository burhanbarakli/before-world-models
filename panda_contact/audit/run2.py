from tr import *
# KAHIN over-F example: trace force around push
REC.clear(); TR=[]
T=8.0; hh,tau=X.DELAYS[2]
r=X.episode(rob,None,T,hh,tau,0.25,0.01,0.005,"KAHIN",0,105,trace=TR)
print("KAHIN over example:",{k:(round(v,3) if isinstance(v,float) else v) for k,v in r.items()})
TR=np.array(TR); A=np.array([x[:7] for x in REC])
u=X.draw(0,105,T)[0]; true=np.array(X.Gr.HOLES[0])+0.01*u[:2]
i=np.argmax(np.linalg.norm(TR[:,2:5],axis=1)); print(" peak |f| at t",TR[i,0],"z-rim mm",1000*(TR[i,1]-.25)," f",TR[i,2:5])
for k in range(int((r['t_push']-0.1)*100), int((r['t_push']+0.6)*100),5):
    print(f"   t{TR[k,0]:.2f} z-rim {1000*(TR[k,1]-.25):6.2f} lat-to-true {1000*np.linalg.norm(A[k,1:3]-true):5.2f}  f {np.round(TR[k,2:5],1)}")
# Friction sign: REFLEKS c5 e10 search sliding, compare lateral force with lateral velocity
REC.clear(); TR=[]
r=X.episode(rob,None,8.0,0.02,0.0,None,0.01,0.002,"REFLEKS",0,103,trace=TR)
TR=np.array(TR); A=np.array([x[:7] for x in REC])
st=np.array([x[7]=="search" for x in REC])
v=np.gradient(A[:,1:3],0.01,axis=0); fl=TR[:,2:4]
m=st&(np.linalg.norm(v,axis=1)>1e-3)
cos=np.sum(v[m]*fl[m],1)/np.linalg.norm(v[m],axis=1)/np.maximum(np.linalg.norm(fl[m],axis=1),1e-9)
print("search steps",m.sum()," cos(lateral force, lateral velocity) median",np.median(cos)," frac<0",np.mean(cos<0), " |f_lat| median",np.median(np.linalg.norm(fl[m],axis=1))," fz median",np.median(TR[m,4]))
print(" |v_lat| median mm/s",1000*np.median(np.linalg.norm(v[m],axis=1)))
