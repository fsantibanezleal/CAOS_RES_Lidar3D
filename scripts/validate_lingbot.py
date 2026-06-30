"""Smoke-test: run lingbot-map streaming inference on a real sequence on this GPU.

Validates the 8 GB-safe config (SDPA, CPU-offload, small KV window, bf16) actually
produces camera poses + depth + a world point cloud, and exports a PLY + a depth PNG
so the result can be eyeballed. This is the real-core de-risk before building the app.

Run:
  .venv/Scripts/python.exe scripts/validate_lingbot.py \
      --image_folder E:/_Datos/3D_Spatial_Reconstruction/lingbot-map-examples/oxford \
      --model_path  E:/_Models/3D_Spatial_Reconstruction/lingbot-map/lingbot-map.pt \
      --first_k 32 --out out/validate
"""
import argparse, glob, os, time
import numpy as np

# Cap caching-allocator fragmentation on a small GPU (must precede torch import).
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image_folder", required=True)
    ap.add_argument("--model_path", required=True)
    ap.add_argument("--first_k", type=int, default=32)
    ap.add_argument("--image_size", type=int, default=518)
    ap.add_argument("--patch_size", type=int, default=14)
    ap.add_argument("--kv_window", type=int, default=16)
    ap.add_argument("--num_scale_frames", type=int, default=8)
    ap.add_argument("--camera_iters", type=int, default=1)
    ap.add_argument("--conf_quantile", type=float, default=0.5, help="keep points above this conf quantile")
    ap.add_argument("--out", default="out/validate")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_cuda = dev.type == "cuda"
    dtype = torch.bfloat16 if (use_cuda and torch.cuda.get_device_capability()[0] >= 8) else torch.float32
    print(f"device={dev} dtype={dtype} gpu={torch.cuda.get_device_name(0) if use_cuda else 'cpu'}")

    from lingbot_map.models.gct_stream import GCTStream
    from lingbot_map.utils.load_fn import load_and_preprocess_images
    from lingbot_map.utils.pose_enc import pose_encoding_to_extri_intri
    from lingbot_map.utils.geometry import closed_form_inverse_se3_general

    # ---- images ----
    paths = sorted(sum([glob.glob(os.path.join(args.image_folder, f"*{e}"))
                        for e in (".png", ".jpg", ".JPG", ".jpeg")], []))
    if args.first_k:
        paths = paths[:args.first_k]
    assert paths, f"no images in {args.image_folder}"
    print(f"loading {len(paths)} frames ...")
    images = load_and_preprocess_images(paths, mode="crop",
                                        image_size=args.image_size, patch_size=args.patch_size)
    print(f"images tensor: {tuple(images.shape)} dtype={images.dtype}")

    # ---- model (8 GB-safe) ----
    print("building GCTStream ...")
    model = GCTStream(
        img_size=args.image_size, patch_size=args.patch_size, enable_3d_rope=True,
        max_frame_num=1024, kv_cache_sliding_window=args.kv_window,
        kv_cache_scale_frames=args.num_scale_frames, kv_cache_cross_frame_special=True,
        kv_cache_include_scale_frames=True, use_sdpa=True, camera_num_iterations=args.camera_iters,
    )
    print(f"loading checkpoint {args.model_path} ...")
    ckpt = torch.load(args.model_path, map_location="cpu", weights_only=False)
    sd = ckpt.get("model", ckpt) if isinstance(ckpt, dict) else ckpt
    missing, unexpected = model.load_state_dict(sd, strict=False)
    print(f"  loaded (missing={len(missing)} unexpected={len(unexpected)})")
    model = model.to(dev).eval()
    if dtype != torch.float32 and getattr(model, "aggregator", None) is not None:
        model.aggregator = model.aggregator.to(dtype=dtype)  # heads stay fp32

    images = images.to(dev)
    if use_cuda:
        torch.cuda.reset_peak_memory_stats(); torch.cuda.empty_cache()

    # ---- inference ----
    print("running inference_streaming ...")
    t0 = time.time()
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=dtype, enabled=use_cuda):
        pred = model.inference_streaming(
            images, num_scale_frames=args.num_scale_frames, keyframe_interval=1,
            output_device=torch.device("cpu"),
        )
    dt = time.time() - t0
    n = len(paths)
    print(f"inference done in {dt:.1f}s  ({n/dt:.2f} FPS over {n} frames)")
    if use_cuda:
        print(f"GPU peak alloc={torch.cuda.max_memory_allocated()/1e9:.2f} GB "
              f"reserved={torch.cuda.max_memory_reserved()/1e9:.2f} GB")

    print("prediction keys + shapes:")
    for k, v in pred.items():
        if isinstance(v, torch.Tensor):
            print(f"  {k:18s} {tuple(v.shape)} {v.dtype}")
        else:
            print(f"  {k:18s} {type(v)}")

    # ---- poses ----
    extr, intr = pose_encoding_to_extri_intri(pred["pose_enc"], images.shape[-2:])
    e4 = torch.zeros((*extr.shape[:-2], 4, 4), dtype=extr.dtype)
    e4[..., :3, :4] = extr.cpu(); e4[..., 3, 3] = 1.0
    c2w = closed_form_inverse_se3_general(e4)[..., :3, :4].numpy()
    cam_centers = c2w.reshape(-1, 3, 4)[:, :, 3]
    traj_len = float(np.linalg.norm(np.diff(cam_centers, axis=0), axis=1).sum())
    print(f"camera trajectory: {cam_centers.shape[0]} poses, path length ~{traj_len:.3f} (metric units)")
    np.save(os.path.join(args.out, "cam_centers.npy"), cam_centers)

    # ---- point cloud: unproject depth with K + c2w (model emits depth, not world_points) ----
    def to_np(x):
        return x.detach().cpu().float().numpy() if isinstance(x, torch.Tensor) else np.asarray(x)
    depth = to_np(pred["depth"])                      # (1,S,H,W,1)
    depth = depth.reshape(-1, depth.shape[-3], depth.shape[-2])  # -> (S,H,W)
    K = to_np(intr).reshape(-1, 3, 3)                 # (S,3,3)
    c2w_np = c2w.reshape(-1, 3, 4)                    # (S,3,4)
    conf = to_np(pred.get("depth_conf"))
    imgs = to_np(pred.get("images", images.cpu()))
    S, H, W = depth.shape
    vv, uu = np.meshgrid(np.arange(H), np.arange(W), indexing="ij")   # (H,W)
    wp = np.empty((S, H, W, 3), np.float32)
    for i in range(S):
        fx, fy, cx, cy = K[i, 0, 0], K[i, 1, 1], K[i, 0, 2], K[i, 1, 2]
        d = depth[i]
        x = (uu - cx) / fx * d; y = (vv - cy) / fy * d; z = d
        cam = np.stack([x, y, z], -1).reshape(-1, 3)                  # (H*W,3) camera coords
        world = cam @ c2w_np[i, :3, :3].T + c2w_np[i, :3, 3]          # -> world
        wp[i] = world.reshape(H, W, 3)
    pts = wp.reshape(-1, 3)
    # colors: images may be [S,3,H,W] in 0..1
    if imgs.ndim == 5: imgs = imgs.reshape(-1, *imgs.shape[-3:])
    if imgs.shape[-3] == 3:        # [S,3,H,W] -> [S,H,W,3]
        imgs = np.transpose(imgs, (0, 2, 3, 1))
    cols = (imgs.reshape(-1, 3)[:, :3] * 255).clip(0, 255).astype(np.uint8)
    if conf is not None:
        c = conf.reshape(-1)
        thr = np.quantile(c, args.conf_quantile)
        keep = c >= thr
        pts, cols = pts[keep], cols[keep]
        print(f"point cloud: {pts.shape[0]:,} points kept (conf>={thr:.3f}, {100*keep.mean():.0f}%) of {S*H*W:,}")
    # subsample for a light PLY
    if pts.shape[0] > 400000:
        idx = np.random.default_rng(0).choice(pts.shape[0], 400000, replace=False)
        pts, cols = pts[idx], cols[idx]
    ply = os.path.join(args.out, "cloud.ply")
    with open(ply, "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {pts.shape[0]}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
        for p, c in zip(pts, cols):
            f.write(f"{p[0]:.4f} {p[1]:.4f} {p[2]:.4f} {int(c[0])} {int(c[1])} {int(c[2])}\n")
    print(f"wrote {ply} ({pts.shape[0]:,} pts)")

    # ---- depth PNG (first + middle frame) ----
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        d = to_np(pred["depth"]); d = d.reshape(-1, *d.shape[-2:]) if d.ndim >= 4 else d
        for tag, i in (("first", 0), ("mid", len(d)//2)):
            plt.figure(figsize=(6, 4)); plt.imshow(d[i], cmap="turbo"); plt.colorbar(); plt.title(f"depth {tag}")
            plt.tight_layout(); plt.savefig(os.path.join(args.out, f"depth_{tag}.png"), dpi=110); plt.close()
        print("wrote depth_first.png / depth_mid.png")
    except Exception as ex:
        print(f"depth viz skipped: {ex}")

    print("VALIDATION_OK")


if __name__ == "__main__":
    main()
