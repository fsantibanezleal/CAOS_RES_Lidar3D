"""lidar3dlab — the offline+live engine for the CAOS product-repo template (ADR-0057).

Rename this package to `<slug>lab` per product and replace the EXAMPLE engine (model/ + the stage bodies) with the
deep-research-chosen SOTA engine. Everything else (the two data contracts, the staged pipeline, the lane gate, the
manifest/trace, the cases-by-category registry) is the FROZEN base — instantiate it, do not redesign it.
"""

__version__ = "0.10.001"  # display X.XX.XXX; PEP 440 form in pyproject.toml (0.1.0)
