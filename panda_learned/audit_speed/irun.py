"""Instrumented copy of robot.run. mode 'time' = project behaviour (must match stored bits);
mode 'z' = fire the disturbance when the tool first descends to z_trig, the height the UNGATED undisturbed
run has at t_d, i.e. same place on the path, not same clock time."""
import sys,os
sys.dont_write_bytecode=True
R_="."
sys.path.insert(0,R_+"/panda_learned")
import gate_speed as gs
import gate_learned as Gl
import numpy as np
from collections import deque
import pybullet as p
import robot as Rb, field_se3 as F, gate_rule as Gr, gate1g as Gg, gate1 as G

class Rec:
    def __init__(s,g,lo):
        s.g,s.lo=g,lo; s.dt,s.vmax,s.p,s.R=g.dt,g.vmax,g.p,g.R; s.goal_R,s.goal_p=g.goal_R,g.goal_p; s.a=1.;s.d=0.
    def field(s,R,pos):
        out=s.g.field(R,pos); c=out[0]; s.d=float(F.norm(c[0],c[1])); s.a=1.
        if s.lo is not None and 0<=pos[2]-Rb.RIM_Z<=gs.BAND: s.a=float(np.clip((2*s.lo-s.d)/s.lo,0,1))
        return out

def irun(robot,ref,hole,eta,h,tau,dist=None,tf=15.,mode="time",trace=False):
    robot.reset(Rb.ref_q0(robot,ref))
    dt=1/Rb.CTRL_HZ
    buf=deque([np.zeros(7)]*int(round(h/dt)))
    qd_f=np.zeros(7); a=dt/tau if tau>0 else 1.0
    goal=np.array([hole[0],hole[1],Rb.RIM_Z-Rb.DEPTH])
    max_lat,max_tilt=0.,0.; t_rim=None; applied=dist is None
    info=dict(t_jump=None,z_pre=None,z_post=None,lat_post=None,d_post=None,t_deep=None,lat_rim=None,
              n_pre=0,n_post=0,n_stop=0,arr_lat_pre=None)
    tr=[]; prefly=False
    for k in range(int(tf*Rb.CTRL_HZ)):
        t=k*dt
        if not applied:
            R,pos=robot.pose()
            fire=(t>=dist[0]) if mode=="time" else (pos[2]<=dist[0])
            if fire:
                Rn=R@F.so3_exp(dist[1]); pn=pos+R@dist[2]
                info["z_pre"]=float(pos[2]); info["t_jump"]=t
                robot.ik(Rn,pn); applied=True
                prefly=True
        R,pos=robot.pose()
        if prefly:
            info["z_post"]=float(pos[2]); info["lat_post"]=float(np.hypot(pos[0]-hole[0],pos[1]-hole[1])); prefly=False
        c,m,D,i=ref.field(R,pos)
        if info["t_jump"]==t: info["d_post"]=ref.d
        if ref.a<1:
            if applied and dist is not None: info["n_post"]+=1
            else: info["n_pre"]+=1
            if ref.a==0: info["n_stop"]+=1
        if trace: tr.append((t,pos[0],pos[1],pos[2],ref.d,ref.a))
        w,v=F.clip(m[0]+eta*c[0],m[1]+eta*c[1],ref.vmax)
        buf.append(robot.twist_to_qd(R,w,v))
        qd=buf.popleft()
        qd_f=qd_f+a*(qd-qd_f)
        robot.command(qd_f)
        for _ in range(Rb.SUB): p.stepSimulation(physicsClientId=robot.c)
        R,pos=robot.pose()
        if pos[2]<Rb.RIM_Z:
            if t_rim is None:
                t_rim=t+dt; info["lat_rim"]=float(np.hypot(pos[0]-hole[0],pos[1]-hole[1]))
            max_lat=max(max_lat,float(np.hypot(pos[0]-hole[0],pos[1]-hole[1])))
            tilt=float(np.arccos(np.clip(-R[2,2],-1,1))); max_tilt=max(max_tilt,tilt)
        if info["t_deep"] is None and Rb.RIM_Z-pos[2]>=.9*Rb.DEPTH: info["t_deep"]=t+dt
    R,pos=robot.pose()
    r=dict(lat=max_lat,tilt=max_tilt,end_z=float(pos[2]),t_rim=t_rim,
           end_p=float(np.linalg.norm(pos-goal)),end_r=float(np.sqrt(2)*np.linalg.norm(F.so3_log(R.T@ref.goal_R))))
    r.update(info)
    if trace: r["trace"]=np.array(tr)
    return r

ROBOT=None
def base(arm,T,h,tau,ih):
    """ungated undisturbed: returns field, ref, t_d-less bits"""
    hole=Gr.HOLES[ih]; ref=Rb.reference_for(ROBOT,hole,T); f=Gl.field(arm,ref,ih,T)
    return hole,ref,f
def gated(f,opt):
    return Rec(f if opt==0 else gs.Gated(f,gs.LO[opt-1]),None if opt==0 else gs.LO[opt-1])
def tick_z(trace_z,t_d):
    dt=1/Rb.CTRL_HZ
    for k in range(len(trace_z)):
        if k*dt>=t_d: return float(trace_z[k])
    raise ValueError
FIELDS=["lat","tilt","end_z","end_p","end_r","t_rim","t_jump","z_pre","z_post","lat_post","d_post","t_deep","lat_rim","n_pre","n_post","n_stop"]
def vec(r): return [np.nan if r[k] is None else r[k] for k in FIELDS]
def job(j):
    """j: arm,T,h,tau,gap,opt,mode. returns (5,20,len(FIELDS)) + clean gated (5,len(FIELDS)) + (t_d,z_trig)(5,2)"""
    global ROBOT
    if ROBOT is None: ROBOT=Rb.Panda()
    arm,T,h,tau,gap,opt,mode=j
    eta=Gr.rule(h,tau); tf=T+4.
    out=np.zeros((5,20,len(FIELDS))); clean=np.zeros((5,len(FIELDS))); tz=np.zeros((5,2))
    for ih in range(5):
        hole,ref,f=base(arm,T,h,tau,ih)
        r0=irun(ROBOT,gated(f,0),hole,eta,h,tau,None,tf,trace=True)
        t_d=(ref.dt*Gg.rim_index(ref)+h+tau if r0["t_rim"] is None else r0["t_rim"])-gap
        z_trig=tick_z(r0["trace"][:,3],t_d); tz[ih]=t_d,z_trig
        clean[ih]=vec(irun(ROBOT,gated(f,opt),hole,eta,h,tau,None,tf))
        for s in range(20):
            w,v=Gr.draw(ROBOT,ref,ih,s,gap)
            d=(t_d if mode=="time" else z_trig,w,v)
            out[ih,s]=vec(irun(ROBOT,gated(f,opt),hole,eta,h,tau,d,tf,mode=mode))
    return j,out,clean,tz
