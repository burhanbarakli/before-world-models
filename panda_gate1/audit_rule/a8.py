import sys; sys.path.insert(0,sys.argv[1])
from lib import *
np.set_printoptions(linewidth=170,precision=3,suppress=True)
R=np.concatenate([np.load('trim0.npy'),np.load('trim1.npy')])
print(R.shape,'None t_rim',np.isnan(R[:,5]).sum())
t=np.full((3,4,3,5,10),np.nan); lat=t.copy(); tilt=t.copy(); z=t.copy(); rf=t.copy()
for r in R:
    i=tuple(int(x) for x in r[:5]); t[i]=r[5]; lat[i]=r[6]; tilt[i]=r[7]; z[i]=r[8]; rf[i]=r[9]
print('t_rim mean by eta (all)',np.nanmean(t,(0,1,2,3)))
print('by T x eta mean\n',np.nanmean(t,(1,2,3)))
sp=np.nanmax(t,4)-np.nanmin(t,4); print('spread across etas per (T,h,tau,hole): mean %.3f max %.3f'%(np.nanmean(sp),np.nanmax(sp)))
ss=np.nanmax(t[...,:9][...,[3,4,5,6]],4)-np.nanmin(t[...,:9][...,[3,4,5,6]],4); print('spread eta 6.5-12: mean %.3f max %.3f'%(np.nanmean(ss),np.nanmax(ss)))
d=t[...,9]-t[...,4]; print('t_rim(rule)-t_rim(8): mean %.4f min %.3f max %.3f'%(np.nanmean(d),np.nanmin(d),np.nanmax(d)))
d=t[...,9]-t[...,3]; print('t_rim(rule)-t_rim(6.5): mean %.4f min %.3f max %.3f'%(np.nanmean(d),np.nanmin(d),np.nanmax(d)))
print('t_rim - ref rim time by (h,tau) rule, T=8\n',(t-rf)[0,...,9].mean(2))
print('t_rim mean by h x tau x eta for T=8 (hole avg) high-delay cell h90 t40:',t[0,3,2].mean(0))
print('h15 t0:',t[0,0,0].mean(0))
# undisturbed baseline success
for c in (.005,):
    okk=(RIM-z>=.9*DEP)&(lat<=c)&(tilt<=np.arctan(2*c/DEP))
    print('undisturbed success by eta',okk.mean((0,1,2,3)))
    print('undisturbed failures by h,tau at eta 16/20 (T avg)\n',okk[...,7].mean((0,3)),'\n',okk[...,8].mean((0,3)))
    print('undisturbed rule success',okk[...,9].mean(),' min',okk[...,9].mean((0,3)))
    print('undist lat max by eta',lat.max((0,1,2,3)), 'rule',lat[...,9].max())
# relation: SR vs t_rim-shift: does later t_rim correlate with SR across eta, within stable etas?
