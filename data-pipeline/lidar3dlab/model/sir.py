"""EXAMPLE analytic core: a deterministic SIR epidemic via forward Euler. Pure-Python + numpy => Pyodide-safe, so
the SAME code path serves the offline pipeline AND the live browser lane. Replace with your product's
research-chosen engine (kept in model/ only if it is pure-Python and light enough for the live lane)."""
from __future__ import annotations

import numpy as np

from ..io.schema import SIRParams, SIRResult


def simulate(p: SIRParams, dt: float = 0.25) -> SIRResult:
    steps = max(1, int(round(p.days / dt)))
    S = float(p.N - p.I0)
    I = float(p.I0)
    R = 0.0
    beta_over_N = (p.beta / p.N) if p.N > 0 else 0.0
    ts = [0.0]
    Ss = [S]
    Is = [I]
    Rs = [R]
    for k in range(1, steps + 1):
        new_inf = beta_over_N * S * I * dt
        new_rec = p.gamma * I * dt
        S = max(0.0, S - new_inf)
        I = max(0.0, I + new_inf - new_rec)
        R = R + new_rec
        ts.append(k * dt)
        Ss.append(S)
        Is.append(I)
        Rs.append(R)
    peak_idx = int(np.argmax(Is))
    return SIRResult(
        case_id=p.case_id,
        t=ts, S=Ss, I=Is, R=Rs,
        peak_I=float(Is[peak_idx]),
        t_peak=float(ts[peak_idx]),
        attack_rate=float(Rs[-1] / p.N) if p.N > 0 else 0.0,
    )
