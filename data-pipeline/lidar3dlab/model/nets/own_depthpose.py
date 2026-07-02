"""OUR own depth + relative-pose network, from scratch (no vendored model). Trainable on an 8 GB GPU.

Design: a shared-nothing pair of small convnets.
  - DepthNet: a UNet encoder/decoder that predicts a per-pixel metric depth (positive via softplus) AND a
    learned aleatoric confidence (log-variance) used to down-weight unreliable pixels in the loss and to filter
    the point cloud at inference (a genuine, useful feature, not decoration).
  - PoseNet: a small convnet over the channel-stacked frame pair that regresses a 6-DoF relative pose as an se(3)
    tangent vector; `se3_exp` maps it to a 4x4 matrix (our own Rodrigues/exp, differentiable).

This is the first honest, trainable own model; the beyond-SOTA recurrent-memory / loop-closure variants extend it
behind the same forward signature (see wip/lidar3d/beyond-sota-own-stack-plan.md).

Two interchangeable backbones behind ONE forward signature (`backbone=` in OwnDepthPose):
  - "scratch"  : the from-scratch UNet encoder + a small pose convnet (DepthNet + PoseNet below). Zero external
                 weights; the honest "desde cero" baseline.
  - "resnet18" : a torchvision ResNet-18 encoder pretrained on ImageNet, SHARED by the depth decoder and a Siamese
                 pose head. The backbone is a generic vision feature extractor (NOT a third-party reconstruction
                 product); the depth decoder, the aleatoric confidence head, the Siamese pose head, the se(3)
                 exponential and the whole training loop remain ours. This is the quality-oriented variant: a
                 pretrained encoder gives much sharper, more consistent depth and steadier pose than 2.2 M params
                 learned from scratch on a few thousand pairs.
Every experiment (backbone, data, ATE) is logged in docs/experiments and MODEL_HISTORY so nothing is lost.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn


def conv(ci: int, co: int, k: int = 3, s: int = 1) -> nn.Sequential:
    return nn.Sequential(nn.Conv2d(ci, co, k, s, k // 2), nn.GroupNorm(min(8, co), co), nn.GELU())


def _up(x: torch.Tensor, ref: torch.Tensor) -> torch.Tensor:
    return F.interpolate(x, size=ref.shape[-2:], mode="bilinear", align_corners=False)


class DepthNet(nn.Module):
    def __init__(self, base: int = 32, max_depth: float = 10.0):
        super().__init__()
        self.max_depth = max_depth
        self.e1 = nn.Sequential(conv(3, base), conv(base, base))
        self.e2 = nn.Sequential(conv(base, base * 2, s=2), conv(base * 2, base * 2))
        self.e3 = nn.Sequential(conv(base * 2, base * 4, s=2), conv(base * 4, base * 4))
        self.e4 = nn.Sequential(conv(base * 4, base * 8, s=2), conv(base * 8, base * 8))
        self.d3 = nn.Sequential(conv(base * 8 + base * 4, base * 4), conv(base * 4, base * 4))
        self.d2 = nn.Sequential(conv(base * 4 + base * 2, base * 2), conv(base * 2, base * 2))
        self.d1 = nn.Sequential(conv(base * 2 + base, base), conv(base, base))
        self.head = nn.Conv2d(base, 2, 1)  # [depth_raw, logvar]

    @staticmethod
    def _up(x: torch.Tensor, ref: torch.Tensor) -> torch.Tensor:
        return F.interpolate(x, size=ref.shape[-2:], mode="bilinear", align_corners=False)

    def forward(self, rgb: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x1 = self.e1(rgb)
        x2 = self.e2(x1)
        x3 = self.e3(x2)
        x4 = self.e4(x3)
        y3 = self.d3(torch.cat([self._up(x4, x3), x3], 1))
        y2 = self.d2(torch.cat([self._up(y3, x2), x2], 1))
        y1 = self.d1(torch.cat([self._up(y2, x1), x1], 1))
        h = self.head(y1)
        depth = self.max_depth * torch.sigmoid(h[:, :1])          # metric depth in (0, max_depth)
        logvar = h[:, 1:].clamp(-8, 8)                            # aleatoric log-variance
        return depth, logvar


class PoseNet(nn.Module):
    def __init__(self, base: int = 16):
        super().__init__()
        self.net = nn.Sequential(
            conv(6, base, s=2), conv(base, base * 2, s=2), conv(base * 2, base * 4, s=2),
            conv(base * 4, base * 8, s=2), conv(base * 8, base * 8, s=2), nn.AdaptiveAvgPool2d(1))
        self.head = nn.Linear(base * 8, 6)
        self.head.weight.data.mul_(0.01)
        self.head.bias.data.zero_()

    def forward(self, rgb0: torch.Tensor, rgb1: torch.Tensor) -> torch.Tensor:
        f = self.net(torch.cat([rgb0, rgb1], 1)).flatten(1)
        return self.head(f)  # se(3) tangent [B,6] = (omega[3], v[3])


def se3_exp(xi: torch.Tensor) -> torch.Tensor:
    """Our own se(3) exponential: tangent [B,6] (rotation axis-angle, translation) -> [B,4,4] c-to-c transform."""
    omega, v = xi[:, :3], xi[:, 3:]
    theta = omega.norm(dim=1, keepdim=True).clamp(min=1e-8)
    k = omega / theta
    K = torch.zeros(xi.shape[0], 3, 3, device=xi.device, dtype=xi.dtype)
    K[:, 0, 1] = -k[:, 2]
    K[:, 0, 2] = k[:, 1]
    K[:, 1, 0] = k[:, 2]
    K[:, 1, 2] = -k[:, 0]
    K[:, 2, 0] = -k[:, 1]
    K[:, 2, 1] = k[:, 0]
    th = theta[:, :, None]
    R = torch.eye(3, device=xi.device, dtype=xi.dtype)[None] + torch.sin(th) * K + (1 - torch.cos(th)) * (K @ K)
    T = torch.eye(4, device=xi.device, dtype=xi.dtype)[None].repeat(xi.shape[0], 1, 1)
    T[:, :3, :3] = R
    T[:, :3, 3] = v
    return T


class PretrainedEncoder(nn.Module):
    """ResNet-18 (ImageNet) multi-scale feature extractor. A GENERIC vision backbone, not a third-party
    reconstruction product: only the convolutional features are reused; the depth decoder, the aleatoric head,
    the Siamese pose head and the training loop are ours. Returns features at /2, /4, /8, /16, /32."""

    out_ch = (64, 64, 128, 256, 512)

    def __init__(self, pretrained: bool = True):
        super().__init__()
        from torchvision.models import ResNet18_Weights, resnet18
        w = ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        m = resnet18(weights=w)
        self.stem = nn.Sequential(m.conv1, m.bn1, m.relu)      # /2, 64
        self.maxpool = m.maxpool
        self.layer1, self.layer2, self.layer3, self.layer4 = m.layer1, m.layer2, m.layer3, m.layer4
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def forward(self, rgb: torch.Tensor) -> list[torch.Tensor]:
        x = (rgb - self.mean) / self.std                      # ImageNet normalisation
        x1 = self.stem(x)
        x2 = self.layer1(self.maxpool(x1))                    # /4, 64
        x3 = self.layer2(x2)                                  # /8, 128
        x4 = self.layer3(x3)                                  # /16, 256
        x5 = self.layer4(x4)                                  # /32, 512
        return [x1, x2, x3, x4, x5]


class DepthDecoder(nn.Module):
    """Our UNet decoder over the pretrained features: metric depth (sigmoid) + aleatoric log-variance, upsampled
    to the input resolution. Same aleatoric-confidence contract as the from-scratch DepthNet."""

    def __init__(self, enc_ch: tuple[int, ...] = PretrainedEncoder.out_ch, base: int = 32, max_depth: float = 10.0):
        super().__init__()
        self.max_depth = max_depth
        c1, c2, c3, c4, c5 = enc_ch
        self.d4 = nn.Sequential(conv(c5 + c4, base * 4), conv(base * 4, base * 4))
        self.d3 = nn.Sequential(conv(base * 4 + c3, base * 2), conv(base * 2, base * 2))
        self.d2 = nn.Sequential(conv(base * 2 + c2, base), conv(base, base))
        self.d1 = nn.Sequential(conv(base + c1, base), conv(base, base))
        self.head = nn.Conv2d(base, 2, 1)

    def forward(self, feats: list[torch.Tensor], out_hw: tuple[int, int]) -> tuple[torch.Tensor, torch.Tensor]:
        x1, x2, x3, x4, x5 = feats
        y4 = self.d4(torch.cat([_up(x5, x4), x4], 1))
        y3 = self.d3(torch.cat([_up(y4, x3), x3], 1))
        y2 = self.d2(torch.cat([_up(y3, x2), x2], 1))
        y1 = self.d1(torch.cat([_up(y2, x1), x1], 1))
        h = self.head(F.interpolate(y1, size=out_hw, mode="bilinear", align_corners=False))
        depth = self.max_depth * torch.sigmoid(h[:, :1])
        logvar = h[:, 1:].clamp(-8, 8)
        return depth, logvar


class SiamesePoseHead(nn.Module):
    """Regresses a 6-DoF se(3) tangent from the globally-pooled encoder features of the two frames (shared
    encoder = Siamese). Small MLP, zero-initialised last layer so it starts at identity motion."""

    def __init__(self, feat: int = 512):
        super().__init__()
        self.mlp = nn.Sequential(nn.Linear(feat * 2, 256), nn.GELU(), nn.Linear(256, 128), nn.GELU(),
                                 nn.Linear(128, 6))
        self.mlp[-1].weight.data.mul_(0.01)
        self.mlp[-1].bias.data.zero_()

    def forward(self, g0: torch.Tensor, g1: torch.Tensor) -> torch.Tensor:
        return self.mlp(torch.cat([g0, g1], 1))


class CorrPoseHead(nn.Module):
    """Regresses se(3) from a LOCAL CORRELATION cost volume between the two frames' feature maps. For every spatial
    location it correlates frame-0 features against a (2d+1)^2 window of frame-1 features, which encodes the apparent
    pixel motion, the signal relative pose actually depends on, and which global pooling (Siamese) discards. A small
    convnet + zero-init MLP maps the cost volume (plus frame-0 context) to the se(3) tangent. This is the RAFT/
    TartanVO-style pose front-end; it targets the pose-accuracy bottleneck that bounds the fused map."""

    def __init__(self, feat: int = 256, disp: int = 4):
        super().__init__()
        self.disp = disp
        cc = (2 * disp + 1) ** 2
        self.enc = nn.Sequential(conv(cc + feat, 128, s=2), conv(128, 128, s=2),
                                 conv(128, 128, s=2), nn.AdaptiveAvgPool2d(1))
        self.head = nn.Linear(128, 6)
        self.head.weight.data.mul_(0.01)
        self.head.bias.data.zero_()

    def _corr(self, f0: torch.Tensor, f1: torch.Tensor) -> torch.Tensor:
        b, c, h, w = f0.shape
        f0n = F.normalize(f0, dim=1)
        f1p = F.pad(F.normalize(f1, dim=1), (self.disp,) * 4)
        outs = []
        for dy in range(2 * self.disp + 1):
            for dx in range(2 * self.disp + 1):
                outs.append((f0n * f1p[:, :, dy:dy + h, dx:dx + w]).sum(1, keepdim=True))
        return torch.cat(outs, 1)                         # [B, (2d+1)^2, H, W]

    def forward(self, f0: torch.Tensor, f1: torch.Tensor) -> torch.Tensor:
        x = self.enc(torch.cat([self._corr(f0, f1), f0], 1)).flatten(1)
        return self.head(x)


class DinoV2Encoder(nn.Module):
    """A FROZEN DINOv2 ViT backbone (the same foundation-model family lingbot-map uses). Returns N intermediate
    patch-token feature maps [B, C, h, w] for a DPT-style depth decoder. Frozen means no gradients and no optimizer
    state, so even ViT-Base (86 M) / ViT-Large (300 M) train within an 8 GB budget: only the small decoder + pose
    head are trained. Weights are fetched once via torch.hub and cached."""

    def __init__(self, name: str = "dinov2_vitb14", layers: tuple = (2, 5, 8, 11)):
        super().__init__()
        self.vit = torch.hub.load("facebookresearch/dinov2", name, verbose=False)
        for p in self.vit.parameters():
            p.requires_grad_(False)
        self.vit.eval()
        self.embed_dim = int(self.vit.embed_dim)
        self.patch = int(self.vit.patch_size)
        self.layers = list(layers)
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def train(self, mode: bool = True):
        super().train(mode)
        self.vit.eval()                                    # the backbone stays frozen/eval regardless
        return self

    def forward(self, rgb: torch.Tensor) -> list[torch.Tensor]:
        with torch.no_grad():                              # no gradients through the frozen backbone
            x = (rgb - self.mean) / self.std               # ImageNet normalisation
            feats = self.vit.get_intermediate_layers(x, n=self.layers, reshape=True)
        return [f.float() for f in feats]


class DinoDepthDecoder(nn.Module):
    """DPT-style depth head over the frozen DINOv2 feature levels (this is the DepthAnything recipe: DINOv2 + a
    convolutional reassemble/fuse decoder). Projects each semantic level, fuses them, then progressively upsamples to
    the input resolution; emits metric depth + aleatoric log-variance."""

    def __init__(self, embed_dim: int = 768, n_levels: int = 4, base: int = 64, max_depth: float = 10.0):
        super().__init__()
        self.max_depth = max_depth
        self.proj = nn.ModuleList([conv(embed_dim, base) for _ in range(n_levels)])
        self.fuse = nn.Sequential(conv(base * n_levels, base * 2), conv(base * 2, base * 2))
        self.up = nn.ModuleList([                           # 16 -> 32 -> 64 -> 128 (then interpolate to input)
            nn.Sequential(conv(base * 2, base * 2), conv(base * 2, base)),
            nn.Sequential(conv(base, base), conv(base, base)),
            nn.Sequential(conv(base, base), conv(base, base // 2)),
        ])
        self.head = nn.Conv2d(base // 2, 2, 1)

    def forward(self, feats: list[torch.Tensor], out_hw: tuple) -> tuple:
        x = torch.cat([p(f) for p, f in zip(self.proj, feats)], 1)
        x = self.fuse(x)
        for blk in self.up:
            x = blk(F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False))
        x = F.interpolate(x, size=out_hw, mode="bilinear", align_corners=False)
        h = self.head(x)
        return self.max_depth * torch.sigmoid(h[:, :1]), h[:, 1:].clamp(-8, 8)


def weighted_procrustes(p0: torch.Tensor, p1: torch.Tensor, w: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    """Differentiable rigid alignment (weighted Kabsch/SVD): returns the 4x4 transform T mapping frame-0 points to
    frame-1, i.e. R,t minimizing sum_k w_k || R p0_k + t - p1_k ||^2. p0,p1: [B,N,3]; w: [B,N] (>=0). Backprop-safe
    (the reflection fix uses det, not a hard branch). This is the geometric core of the metric-depth-seeded pose.
    Runs in float32 with autocast OFF (SVD needs it, and matmuls under autocast would downcast to bf16)."""
    with torch.autocast(device_type=p0.device.type, enabled=False):
        p0, p1, w = p0.float(), p1.float(), w.float()
        w = w / (w.sum(1, keepdim=True) + eps)
        mu0 = (w.unsqueeze(-1) * p0).sum(1, keepdim=True)         # weighted centroids [B,1,3]
        mu1 = (w.unsqueeze(-1) * p1).sum(1, keepdim=True)
        x, y = p0 - mu0, p1 - mu1
        s = (w.unsqueeze(-1) * x).transpose(1, 2) @ y             # [B,3,3] weighted cross-covariance
        u, _, vh = torch.linalg.svd(s)
        v = vh.transpose(1, 2)
        d = torch.det(v @ u.transpose(1, 2))                     # +/-1: cancel any reflection
        diag = torch.diag_embed(torch.stack([torch.ones_like(d), torch.ones_like(d), d], -1))
        r = v @ diag @ u.transpose(1, 2)
        t = mu1.squeeze(1) - (r @ mu0.transpose(1, 2)).squeeze(-1)
    tf = torch.eye(4, device=p0.device, dtype=torch.float32).unsqueeze(0).repeat(p0.shape[0], 1, 1)
    tf[:, :3, :3] = r
    tf[:, :3, 3] = t
    return tf


def _sample_at(img: torch.Tensor, px: torch.Tensor) -> torch.Tensor:
    """Bilinear-sample a [B,1,H,W] map at [B,N,2] image-pixel coords -> [B,N]."""
    h, w = img.shape[-2:]
    g = torch.stack([2 * px[..., 0] / (w - 1) - 1, 2 * px[..., 1] / (h - 1) - 1], -1)
    return F.grid_sample(img, g[:, None], align_corners=True, mode="bilinear").squeeze(1).squeeze(1)


def _unproject_px(px: torch.Tensor, depth: torch.Tensor, k: torch.Tensor) -> torch.Tensor:
    """Pixel coords [B,N,2] + metric depth [B,N] + intrinsics [B,3,3] -> camera-frame 3D points [B,N,3]."""
    fx, fy = k[:, 0, 0:1], k[:, 1, 1:2]
    cx, cy = k[:, 0, 2:3], k[:, 1, 2:3]
    x = (px[..., 0] - cx) / fx * depth
    y = (px[..., 1] - cy) / fy * depth
    return torch.stack([x, y, depth], -1)


class GeoPoseHead(nn.Module):
    """Metric-depth-seeded GEOMETRIC relative pose (the differentiable-BA milestone, M-B). Instead of regressing the
    pose, it (1) forms soft feature correspondences frame0->frame1 (learned descriptors + a global soft-argmax),
    (2) lifts both endpoints to 3D with the predicted metric depth + intrinsics, and (3) solves a differentiable
    weighted-Procrustes for the rigid relative pose. The metric depth fixes the monocular scale so the geometry is
    well-posed. This is the estimator family accurate learned VO uses (DROID/DPVO/DINO-VO), not a regression MLP."""

    def __init__(self, feat: int, proj: int = 128):
        super().__init__()
        self.q = nn.Conv2d(feat, proj, 1)
        self.k = nn.Conv2d(feat, proj, 1)
        self.conf = nn.Sequential(nn.Conv2d(feat, 64, 1), nn.GELU(), nn.Conv2d(64, 1, 1))
        self.temp = nn.Parameter(torch.tensor(3.0))

    def forward(self, f0: torch.Tensor, f1: torch.Tensor, d0: torch.Tensor, d1: torch.Tensor,
                k: torch.Tensor) -> torch.Tensor:
        b, _, h, w = f0.shape
        hi, wi = d0.shape[-2:]
        q = F.normalize(self.q(f0), dim=1).flatten(2)                 # [B,proj,N]
        kk = F.normalize(self.k(f1), dim=1).flatten(2)
        corr = torch.einsum("bcn,bcm->bnm", q, kk) * self.temp.clamp(0.5, 20)
        attn = corr.softmax(-1)                                       # soft frame0->frame1 correspondence
        ys, xs = torch.meshgrid(torch.arange(h, device=f0.device), torch.arange(w, device=f0.device), indexing="ij")
        gx = (xs.flatten().float() + 0.5) * (wi / w)                  # grid -> image pixels
        gy = (ys.flatten().float() + 0.5) * (hi / h)
        grid = torch.stack([gx, gy], -1)[None].expand(b, -1, -1)      # [B,N,2] pixel coords of the frame grid
        p0px = grid
        p1px = attn @ grid                                            # soft-corresponded frame1 pixel per frame0 pt
        d0s = _sample_at(d0, p0px).clamp(min=1e-3)
        d1s = _sample_at(d1, p1px).clamp(min=1e-3)
        p0 = _unproject_px(p0px, d0s, k)
        p1 = _unproject_px(p1px, d1s, k)
        conf = self.conf(f0).flatten(2).squeeze(1).sigmoid() * attn.max(-1).values   # descriptor conf x match peak
        t01 = weighted_procrustes(p0, p1, conf + 1e-4)               # frame0 -> frame1
        return torch.linalg.inv(t01)                                 # our convention: rel maps frame1 -> frame0


class OwnDepthPose(nn.Module):
    """The full model: per-frame depth+conf and pairwise relative pose. Interchangeable backbones behind one forward
    signature: "scratch" (DepthNet + PoseNet, zero external weights), "resnet18" (ImageNet ResNet shared by
    DepthDecoder + SiamesePoseHead), or "dinov2_vitb14"/"dinov2_vits14"/"dinov2_vitl14" (a FROZEN DINOv2 foundation
    backbone + a DPT-style DinoDepthDecoder + Siamese pose). Everything but the frozen backbone features is ours."""

    def __init__(self, base: int = 32, max_depth: float = 10.0, backbone: str = "scratch",
                 pretrained: bool = True, pose_head: str = "siamese"):
        super().__init__()
        self.backbone = backbone
        self.pose_head = pose_head
        if backbone.startswith("dinov2"):
            self.enc = DinoV2Encoder(name=backbone)
            self.dec = DinoDepthDecoder(self.enc.embed_dim, n_levels=len(self.enc.layers),
                                        base=max(base, 64), max_depth=max_depth)
            self._plevel = -1                                          # grid-feature level for corr/geo heads
            grid_feat, pool_feat = self.enc.embed_dim, self.enc.embed_dim
        elif backbone == "resnet18":
            self.enc = PretrainedEncoder(pretrained=pretrained)
            self.dec = DepthDecoder(self.enc.out_ch, base, max_depth)
            self._plevel = 3                                          # layer3 (/16)
            grid_feat, pool_feat = self.enc.out_ch[3], self.enc.out_ch[-1]
        else:
            self.depth = DepthNet(base, max_depth)
            self.pose = PoseNet()
            return
        if pose_head == "geo":
            self.posehead = GeoPoseHead(feat=grid_feat)               # metric-depth-seeded differentiable geometry
        elif pose_head == "corr":
            self.posehead = CorrPoseHead(feat=grid_feat)
        else:
            self.posehead = SiamesePoseHead(pool_feat)

    def forward(self, rgb0: torch.Tensor, rgb1: torch.Tensor, k: torch.Tensor | None = None) -> dict:
        if self.backbone == "scratch":
            depth0, logvar0 = self.depth(rgb0)
            xi = self.pose(rgb0, rgb1)
            return {"depth0": depth0, "logvar0": logvar0, "xi": xi, "rel_pose": se3_exp(xi)}
        f0 = self.enc(rgb0)
        f1 = self.enc(rgb1)
        depth0, logvar0 = self.dec(f0, rgb0.shape[-2:])
        if self.pose_head == "geo":                                  # GEOMETRIC pose from metric depth (no se(3) reg)
            if k is None:
                raise ValueError("pose_head='geo' needs intrinsics k=[B,3,3]")
            depth1 = self.dec(f1, rgb1.shape[-2:])[0]
            rel = self.posehead(f0[self._plevel], f1[self._plevel], depth0, depth1, k)
            xi = torch.zeros(rgb0.shape[0], 6, device=rgb0.device, dtype=depth0.dtype)  # placeholder (pose is geometric)
            return {"depth0": depth0, "logvar0": logvar0, "xi": xi, "rel_pose": rel}
        if self.pose_head == "corr":
            xi = self.posehead(f0[self._plevel], f1[self._plevel])
        else:
            xi = self.posehead(f0[-1].mean((-2, -1)), f1[-1].mean((-2, -1)))
        return {"depth0": depth0, "logvar0": logvar0, "xi": xi, "rel_pose": se3_exp(xi)}
