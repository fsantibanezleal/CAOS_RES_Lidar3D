# Guide — bring your own data

The product is **applicable to NEW data**, not just the baked cases — that is what makes it a tool. The door is
**CONTRACT 1** (`data-pipeline/lidar3dlab/io/contract.py`).

1. Put your input in the documented standard format (see [`data/README.md`](../../data/README.md) — EXAMPLE: a
   params CSV with `case_id,beta,gamma,N,I0[,days]`). Drop the file under `data/raw/` (git-ignored).
2. Point `preprocess` at it (or pass it on the CLI) and run `scripts/precompute.{sh,ps1}`. CONTRACT 1 validates
   each row: **rejected** with a reason if it violates the schema/ranges (NaN, out-of-range, `I0>N`, …),
   **flagged** if plausible-but-suspicious (e.g. `R0>20`), **accepted** otherwise. Nothing is silently coerced.
3. The pipeline produces a compact artifact + manifest you can replay in the SPA, exactly like the built-in cases.
4. **Live (optional):** if the [gate](../architecture/03_the-gate.md) classifies your case `live`, the frontend's
   Pyodide lane calls `lidar3dlab.live.run_trace_json({...your params...})` and renders the result in-browser — no
   server, no precompute.

If your data legitimately doesn't fit, extend CONTRACT 1 (and its tests) **deliberately** — never loosen it just
to make bad data pass.
