import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
# load ascii ply
pts=[]; cols=[]
with open("out/validate/cloud.ply") as f:
    hdr=True
    for ln in f:
        if hdr:
            if ln.startswith("end_header"): hdr=False
            continue
        a=ln.split()
        if len(a)>=6:
            pts.append([float(a[0]),float(a[1]),float(a[2])]); cols.append([int(a[3]),int(a[4]),int(a[5])])
pts=np.array(pts); cols=np.array(cols)/255.0
cam=np.load("out/validate/cam_centers.npy")
print("cloud",pts.shape,"cam",cam.shape,"bbox min",pts.min(0).round(2),"max",pts.max(0).round(2))
# subsample for render
idx=np.random.default_rng(0).choice(len(pts),min(40000,len(pts)),replace=False)
P=pts[idx]; C=cols[idx]
fig=plt.figure(figsize=(15,5))
for k,(el,az) in enumerate([(20,-60),(75,-90),(10,0)]):
    ax=fig.add_subplot(1,3,k+1,projection="3d")
    ax.scatter(P[:,0],P[:,1],P[:,2],c=C,s=0.4,marker=".",linewidths=0)
    ax.plot(cam[:,0],cam[:,1],cam[:,2],"-",color="red",lw=2)
    ax.scatter(cam[:,0],cam[:,1],cam[:,2],c="red",s=8)
    ax.view_init(elev=el,azim=az); ax.set_title(f"view {k+1} (cam path red)")
    ax.set_box_aspect([1,1,1])
plt.tight_layout(); plt.savefig("out/validate/cloud_render.png",dpi=110); print("wrote out/validate/cloud_render.png")
