"""EXAMPLE cases spanning CATEGORIES (the domain problem-type taxonomy). Replace per product with your real,
varied coverage matrix. Each case: id, category, params, expected band (what a domain expert should see),
real|synthetic flag. Includes a negative/degenerate CONTROL the engine must handle without crashing."""
from __future__ import annotations

from dataclasses import dataclass

from ..io.schema import SIRParams


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    params: SIRParams
    expected_band: str
    real_or_synthetic: str


CASES: list[Case] = [
    Case("EX01_subcritical", "sub-critical (R0<1)",
         SIRParams("EX01_subcritical", beta=0.18, gamma=0.25, N=100_000, I0=50),
         "no outbreak: peak ~ I0, attack rate ~ 0", "synthetic"),
    Case("EX02_epidemic", "epidemic (R0>1)",
         SIRParams("EX02_epidemic", beta=0.55, gamma=0.20, N=100_000, I0=50),
         "clear single peak; attack rate ~ 0.7-0.9", "synthetic"),
    Case("EX03_fast_burn", "fast-burn (high R0)",
         SIRParams("EX03_fast_burn", beta=1.20, gamma=0.20, N=100_000, I0=100),
         "early sharp peak; attack rate -> ~1", "synthetic"),
    Case("EX04_slow_spread", "slow-spread (R0~1.2)",
         SIRParams("EX04_slow_spread", beta=0.30, gamma=0.25, N=100_000, I0=50),
         "broad low peak late in the horizon", "synthetic"),
    Case("CTRL_degenerate", "control: degenerate",
         SIRParams("CTRL_degenerate", beta=0.40, gamma=0.20, N=100_000, I0=0),
         "I0=0 -> no dynamics (must run, peak_I=0, attack rate=0)", "synthetic"),
]
