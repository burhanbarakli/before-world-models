import pickle,sys; sys.dont_write_bytecode=True
import numpy as np
from common import *
F=["lat","tilt","end_z","end_p","end_r","t_rim","t_jump","z_pre","z_post","lat_post","d_post","t_deep","lat_rim","n_pre","n_post","n_stop"]
res=pickle.load(open("time.pkl","rb")); by={(j[1],j[2],j[3],j[4],j[5]):(o,c) for j,o,c in res}
f=lambda o,n:o[...,F.index(n)]
print("T gap h+tau | t_rim delay ms, mean median max (disturbed) | t_deep delay mean max | clean delay ms | stop ticks | t_deep-T max none/gated | pre ticks")
alld=[]
for (T,h,tau,g,o) in by:
    if o!=2: continue
    a,ca=by[(T,h,tau,g,0)]; b,cb=by[(T,h,tau,g,2)]
    dr=1e3*(f(b,"t_rim")-f(a,"t_rim")); dd=1e3*(f(b,"t_deep")-f(a,"t_deep")); cl=1e3*(f(cb,"t_deep")-f(ca,"t_deep"))
    alld.append(dd.ravel())
    print(T,g,round(h+tau,3),"|",round(np.nanmean(dr)),round(np.nanmedian(dr)),round(np.nanmax(dr)),"|",round(np.nanmean(dd)),round(np.nanmax(dd)),"| clean",round(np.nanmean(cl)),round(np.nanmax(cl)),"| stop",round(np.nanmean(f(b,"n_stop")),1),"| late",round(np.nanmax(f(a,"t_deep"))-T,2),round(np.nanmax(f(b,"t_deep"))-T,2),"| pre",round(np.nanmean(f(b,"n_pre")),1),"z_pre-ungated mm",round(1e3*np.nanmean(f(b,"z_pre")-f(a,"z_pre")),2))
d=np.concatenate(alld); print("all t_deep delay ms: mean",np.nanmean(d),"p95",np.nanquantile(d,.95),"max",np.nanmax(d),"nan",np.isnan(d).sum())
