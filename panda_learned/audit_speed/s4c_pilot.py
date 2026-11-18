import sys,time; sys.dont_write_bytecode=True
import irun as I, numpy as np, multiprocessing as mp, pickle
from common import *
JOBS=[(a,8.,.07,.025,.25,o,"time") for a in (0,None) for o in (0,1,2)]
if __name__=="__main__":
    t=time.time(); D,U,K=load()
    with mp.Pool(6) as P: res=P.map(I.job,JOBS,chunksize=1)
    print("elapsed",time.time()-t)
    pickle.dump(res,open("pilot.pkl","wb"))
    for j,o,c,tz in res:
        ix=(I.Gl.ARMS.index(j[0]),I.Gl.PERIOD.index(j[1]),I.Gl.DELAY.index(j[2]),I.Gl.LAG.index(j[3]),I.Gl.GAP.index(j[4]),j[5])
        ok=(o[...,:5]==D[ix]).all()
        F=I.FIELDS
        print(j,"bits",ok,"z_trig",np.round(tz[:,1],4),"t_d",np.round(tz[:,0],3))
        f=lambda n:o[...,F.index(n)]
        print("  through-rim frac",np.mean(f("z_post")<.25),"z_pre mean",round(np.nanmean(f("z_pre")),4),"n_pre mean",round(np.nanmean(f("n_pre")),1),"n_post",round(np.nanmean(f("n_post")),1),"n_stop",round(np.nanmean(f("n_stop")),1))
        print("  t_rim mean",round(np.nanmean(f("t_rim")),3),"t_deep mean",round(np.nanmean(f("t_deep")),3),"clean t_rim",np.round(c[:,F.index('t_rim')],2),"clean n_pre",c[:,F.index('n_pre')])
