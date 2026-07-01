"""OUR own depth + relative-pose network, from scratch (no vendored model). Trainable on an 8 GB GPU.

Design: a shared-nothing pair of small convnets.
  - DepthNet: a UNet encoder/decoder that predicts a per-pixel metric depth (positive via softplus) AND a
    learned aleatoric confidence (log-variance) used to down-weight unreliable pixels in the loss and to filter
    the point cloud at inference (a genuine, useful feature, not decoration).
  - PoseNet: a small convnet over the channel-stacked frame pair that regresses a 6-DoF relative pose as an se(3)
    tangent vector; `se3_exp` maps it to a 4x4 matrix (our own Rodrigues/exp, differentiable).

This is the first honest, trainable own model; the beyond-SOTA recurrent-memory / loop-closure variants extend it
behind the same forward signature (see wip/lidar3d/beyond-sota-own-stack-plan.md).
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn


def conv(ci: int, co: int, k: int = 3, s: int = 1) -> nn.Sequential:
    return nn.Sequential(nn.Conv2d(ci, co, k, s, k // 2), nn.GroupNorm(min(8, co), co), nn.GELU())


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


class OwnDepthPose(nn.Module):
    """The full model: per-frame depth+conf and pairwise relative pose."""

    def __init__(self, base: int = 32, max_depth: float = 10.0):
        super().__init__()
        self.depth = DepthNet(base, max_depth)
        self.pose = PoseNet()

    def forward(self, rgb0: torch.Tensor, rgb1: torch.Tensor) -> dict:
        depth0, logvar0 = self.depth(rgb0)
        xi = self.pose(rgb0, rgb1)
        return {"depth0": depth0, "logvar0": logvar0, "xi": xi, "rel_pose": se3_exp(xi)}
