import numpy as np
np.set_printoptions(precision=3, suppress=True, linewidth=150)
d=np.load("./panda_contact/results/exp_contact.npz")
D=d["data"]; keys=list(d["keys"]); K=lambda n: D[...,keys.index(n)]
ok,deep,fm,jam,tc,se,ti,ez=K("ok"),K("deep"),K("f_max"),K("jam"),K("t_contact"),K("s_err"),K("t_in"),K("end_z")
over=(fm>50).astype(float)
P=slice(0,3)
def W(x,c=0,ax=None): 
    y=x[P,:,:,:,1:,c]; return y[...,2,:,:].mean()-y[...,1,:,:].mean()
print("W ok",W(ok)," W deep",W(deep)," W notover", -(W(over)))
# W by gap, T, delay, e
x=ok[P,:,:,:,:,0]
for g in range(2): print("gap",g,"W",x[:,:,:,g,1:,2].mean()-x[:,:,:,g,1:,1].mean())
for e in range(1,4): print("e",e,"W",x[:,:,:,:,e,2].mean()-x[:,:,:,:,e,1].mean(), " Wdeep", deep[P,:,:,:,e,0,2].mean()-deep[P,:,:,:,e,0,1].mean())
# paired transitions in pushed runs c5 e>0
kk=ok[P,:,:,1,1:,0,2]; rr=ok[P,:,:,1,1:,0,1]
print("pushed: K ok R fail",np.mean((kk==1)&(rr==0))," K fail R ok",np.mean((kk==0)&(rr==1)))
ro=over[P,:,:,1,1:,0,1]; rd=deep[P,:,:,1,1:,0,1]
m=(kk==1)&(rr==0); print("  among K ok&R fail: R over",ro[m].mean()," R notdeep",1-rd[m].mean())
kd=deep[P,:,:,:,1:,0,2]; ko=over[P,:,:,:,1:,0,2]; rd=deep[P,:,:,:,1:,0,1]
print("P(R deep | K over)",rd[ko==1].mean())
# KAHIN(e>0) vs TABAN(e=0) paired identical?
t0=ok[P,:,:,:,0,0,0]
for e in range(1,4): print("KAHIN e",e,"== TABAN e0 frac", np.mean(ok[P,:,:,:,e,0,2]==t0), "fmax corr", np.corrcoef(fm[P,:,:,:,e,0,2].ravel(),fm[P,:,:,:,0,0,0].ravel())[0,1])
# REFLEKS e=0 vs TABAN e=0
print("REFLEKS e0 == TABAN e0", np.mean(ok[P,:,:,:,0,0,1]==t0), " t_contact REFLEKS e0 >=0 frac",np.mean(tc[P,:,:,:,0,0,1]>=0))
print("\n=== c = 2 mm, paper, e>0 ===")
for p,n in enumerate(["TABAN","REFLEKS","KAHIN"]):
    s=lambda a: a[P,:,:,:,1:,1,p]
    print(n,"S",s(ok).mean(),"notdeep",1-s(deep).mean(),"jam",s(jam).mean(),"over",s(over).mean(),"contact frac",(s(tc)>=0).mean(),"t_in",s(ti).mean())
for e in range(1,4):
  for g in range(2):
    r=lambda a: a[P,:,:,g,e,1,1]; k=lambda a: a[P,:,:,g,e,1,2]
    print(f" e{e} gap{g}: R ok {r(ok).mean():.3f} notdeep {1-r(deep).mean():.3f} jam {r(jam).mean():.3f} over {r(over).mean():.3f} | K ok {k(ok).mean():.3f} over {k(over).mean():.3f}")
for i,T in enumerate([8,4]):
  for e in range(1,4): 
    r=ok[P,i,:,:,e,1,1]; print(f" T{T} e{e} R ok {r.mean():.3f}", " by delay", [round(float(ok[P,i,j,:,e,1,1].mean()),3) for j in range(3)])
# REFLEKS c2 failures that are not deep: end_z above rim? s_err, t_contact
m=(deep[P,:,:,:,1:,1,1]==0)
print("R c2 notdeep: n",m.sum()," end_z-rim mm quantiles", np.percentile((ez[P,:,:,:,1:,1,1][m]-0.25)*1000,[5,50,95]), " jam frac",jam[P,:,:,:,1:,1,1][m].mean())
print("   t_contact - quantiles",np.percentile(tc[P,:,:,:,1:,1,1][m],[5,50,95])," s_err mm",np.percentile(se[P,:,:,:,1:,1,1][m]*1000,[5,50,95]))
# by e for not deep R c2
for e in range(1,4):
    m=(deep[P,:,:,:,e,1,1]==0); 
    print(f"  e{e}: notdeep {m.mean():.3f}; end_z-rim median {np.median((ez[P,:,:,:,e,1,1][m]-0.25)*1000) if m.any() else np.nan:.2f} mm; s_err median {np.median(se[P,:,:,:,e,1,1][m])*1000 if m.any() else np.nan:.1f} mm; tcontact med {np.median(tc[P,:,:,:,e,1,1][m]) if m.any() else np.nan:.2f}")
# successful REFLEKS c2: s_err at end
m=(ok[P,:,:,:,1:,1,1]==1); print("R c2 success s_err mm median", np.median(se[P,:,:,:,1:,1,1][m])*1000)
# c5 REFLEKS not deep
m=(deep[P,:,:,:,1:,0,1]==0); print("R c5 notdeep n",m.sum(),"by e",[int((deep[P,:,:,:,e,0,1]==0).sum()) for e in range(1,4)], "by T",[int((deep[P,i,:,:,1:,0,1]==0).sum()) for i in range(2)],"by gap",[int((deep[P,:,:,g,1:,0,1]==0).sum()) for g in range(2)])
