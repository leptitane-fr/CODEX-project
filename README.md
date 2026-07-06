# TEI — Toy Model

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/status-exploratory-blue)

## What this is

A computational toy model in support of the **Theory of Informational Emergence
(TEI)**, an ontological framework (currently at version 5.0) proposing that
observed space, time, and matter are a "rendered" projection of a discrete,
non-spatial causal substrate. TEI explicitly does not currently claim to be a
predictive physics program: a previous version (3.x) derived the fine-structure
constant and CMB peak ratios through post-hoc numerical fitting later shown to be
false, and the project's governing rule since then is that **no numeric
agreement is accepted without independent provenance** (see
`math/causal_set_dimension.md` for an example of that discipline applied here).

This repository targets the one open question TEI itself identifies as
computationally tractable right now (TEI 5.0, Partie 3.2 / 7.5): the claim that
the number of nodes reachable within `N` causal steps from a point should grow
**polynomially** (as `N^3`), never like the generic exponential growth of an
arbitrary graph — and that this, not "why is space 3D", is the real form of the
question.

## What's implemented

`sim/graph_generators.py` provides three generators and a shared
growth-exponent measurement, so the regimes can be compared directly:

- `generate_random_dag` — a generic random causal DAG with no embedding and no
  notion of distance. Its reachable set saturates at nearly the full node count
  within a handful of hops: the "generic exponential" regime TEI contrasts
  itself against.
- `sprinkle_minkowski` + `reachable_within_ticks` — a Poisson sprinkling of
  points into `dim`-dimensional Minkowski coordinates. The causal future of a
  point grows as `tick^dim` by construction: this is standard causal set theory
  (the Myrheim-Meyer dimension estimator), not a new TEI result — see
  `math/causal_set_dimension.md` for the derivation, references, and an explicit
  statement of what this does *not* establish (the embedding dimension is
  imposed externally; TEI's actual open question — deriving exponent 3 from a
  purely local, non-embedded rule — is untouched by this instrument).
- `generate_tei_shadow_graph` — TEI's own candidate mechanism for that open
  question (the "Regle de l'Ombre Causale"): a purely local assembly rule,
  with no embedding at all, where each new node connects to a bounded number
  `k` of existing nodes that must form a local antichain (no existing directed
  path between any two of them), maintaining a strict transitive reduction.
  Whether this produces a stable polynomial exponent is answered empirically
  in `math/tei_shadow_rule_analysis.md` — the short version: it does break the
  generic saturating-exponential regime, but the measured exponent drifts with
  hop depth rather than stabilizing, so it does **not** confirm the `N^3`
  hypothesis as currently implemented.

## Reproducibility

1. Install dependencies:
   ```bash
   conda env create -f environment.yml
   conda activate tei
   ```

2. Measure the growth exponent for a Minkowski-embedded causal set:
   ```bash
   python sim/graph_generators.py --mode sprinkling --dim 3 --N 100000 --ticks 20 --seed 42 --out data/sprinkling_d3.npz
   ```

3. Compare against the generic (non-embedded) baseline:
   ```bash
   python sim/graph_generators.py --mode random-dag --N 100000 --out-degree 4 --ticks 15 --seed 42 --out data/random_dag.npz
   ```

4. Test the local, non-embedded Causal Shadow Rule:
   ```bash
   python sim/graph_generators.py --mode tei-shadow --k 3 --N 100000 --ticks 20 --seed 42 --out data/tei_shadow_k3.npz
   ```

5. Run unit tests:
   ```bash
   pytest -q
   ```

## Repository structure

```
sim/                          # Generators and measurement code
  graph_generators.py
tests/                        # Pytest unit tests
  test_graph_generators.py
data/                         # Generated .npz outputs (gitignored, run scripts to reproduce)
figures/                      # Generated plots (gitignored, run scripts to reproduce)
math/                         # Provenance notes and derivations
  causal_set_dimension.md
  tei_shadow_rule_analysis.md
environment.yml               # Conda environment
pyproject.toml                # Pytest configuration
CITATION.cff                  # Citation metadata
LICENSE                       # MIT License
```

## Citation

If you use this work, please cite:

```
@misc{goulet2025tei,
  author       = {Stéphane Goulet},
  title        = {Theory of Informational Emergence (TEI) — Toy Model},
  year         = {2025},
  url          = {https://github.com/leptitane-fr/tei-reproducibility},
  note         = {Preprint, under open review}
}
```

## License

This project is licensed under the MIT License.
