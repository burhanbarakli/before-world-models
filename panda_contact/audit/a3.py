import numpy as np
np.set_printoptions(precision=3, suppress=True, linewidth=150)
d=np.load("./panda_contact/results/exp_contact.npz")
D=d["data"]; keys=list(d["keys"]); K=lambda n: D[...,keys.index(n)]
pu=K("pushed")
print("pushed rate gap=None:", np.nanmean(pu[:,:,:,0]), " gap=0.25:", np.nanmean(pu[:,:,:,1]))
print("pushed by T (gap .25):", [np.nanmean(pu[:,i,:,1]) for i in range(2)], "by policy", [np.nanmean(pu[:,:,:,1,:,:,p]) for p in range(3)])
tp=K("t_push"); print("t_push range gap.25:", np.nanmin(tp[:,:,:,1]), np.nanmax(tp[:,:,:,1]))
for i,T in enumerate([8,4]): print(" T",T,"t_push mean",np.nanmean(tp[:,i,:,1]), "by delay",[np.nanmean(tp[:,i,j,1]) for j in range(3)])
# failures over Fmax, paper arm c=5
over=(K("f_max")>50).astype(float); over[np.isnan(K("f_max"))]=np.nan
deep=K("deep"); ok=K("ok")
x=over[:3,:,:,:,:,0]
print("over Fmax c5 paper by T x delay x gap (all e, pol avg nanmean):")
for i in range(2):
  for j in range(3):
    print(" T",[8,4][i],"dl",j,[round(float(np.nanmean(x[:,i,j,g])),3) for g in range(2)])
print("over by e:",[np.nanmean(x[:,:,:,:,e]) for e in range(4)])
print("over by policy:",[np.nanmean(x[:,:,:,:,:,p]) for p in range(3)])
# are over-Fmax runs deep?
o=over[:3,:,:,:,1:,0]; dp=deep[:3,:,:,:,1:,0]
for p in range(3): 
  m=o[...,p,:,:]==1; print("pol",p,"over runs:",m.sum()," deep among them:",np.nanmean(dp[...,p,:,:][m]))
# overlap of over-failures across policies (paired)
oT,oR,oK=o[...,0,:,:],o[...,1,:,:],o[...,2,:,:]
print("P(R over | K over)",np.mean(oR[oK==1]),"P(K over|R over)",np.mean(oK[oR==1]), "P(T over|K over)", np.mean(oT[oK==1]))
# e=0 over rates
print("e=0 over TABAN",np.nanmean(over[:3,:,:,:,0,0,0]),"REFLEKS",np.nanmean(over[:3,:,:,:,0,0,1]))
# fmax distribution
fm=K("f_max")[:3,:,:,:,1:,0]
print("fmax quantiles KAHIN:",np.nanpercentile(fm[...,2,:,:],[50,90,95,99,100]))
