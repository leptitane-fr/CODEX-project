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

`sim/graph_generators.py` provides four generators and a shared
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
  in `math/tei_shadow_rule_analysis.md`, under two different notions of causal
  depth (`reachable_within_hops`, shortest-path; `reachable_within_depth`,
  longest-path) — the short version under both: it does break the generic
  saturating-exponential regime, but the measured exponent does not settle
  onto a stable value (it drifts upward with hop count, or rises then falls
  with longest-path depth), so it does **not** confirm the `N^3` hypothesis
  as currently implemented.
- `generate_event_driven_shadow_graph` — a second, more ontologically careful
  realization of the same rule: no global tick (an asynchronous per-node
  delay queue instead of a `for` loop), no saturation wall (unbounded charge,
  only its *delay* grows, linearly), and no global sampling (candidates are
  found via a bounded local random walk, never a draw from the whole
  population). Growth is measured from a designated Observer's own point of
  view — modeled, per TEI 6ter.3-D, as a self-continuing worldline rather
  than a fixed node, since a fixed node was empirically shown not to work
  (see `math/event_driven_shadow_analysis.md` for that design history,
  including two dead ends). A 50-seed study (also in that file) gives a clear
  **negative** verdict: the Observer's cumulative causal-cone exponent is
  ~1.0-1.5 (never near 3), depends on `k`, drifts toward 1 for k=3/4, and is
  not even independent of the arbitrary `background_ratio` parameter — so it
  does not confirm `N^3`. A follow-up swaps that observable for the transverse
  **interval width** (`interval_width` / `max_antichain_size`: the max
  antichain of an Alexandrov interval, whose exponent estimates the *spatial*
  dimension `d-1` without the worldline chain contaminating it). That fixes
  the `background_ratio` pathology — the width exponent is invariant under it —
  but the exponent still depends on `k` and still drifts. A diagnostic pass
  then pins the cause: the Observer's transverse width **collapses as it ages**
  (it decouples from the background flux), so the asymptotic emergent spatial
  dimension is effectively 0 — a bare 1D worldline — and the rich early-time
  width is a transient of birth, not a dimension. A gravity-like fix was then
  tested (`--charge-biased-routing`: walk steps drawn toward dense/slow nodes
  with probability ∝ 1+charge, the same law as the delay — no new knob) and
  **failed the pre-registered stationarity criterion**: flux condenses onto
  background hubs (max charge jumps 26 → ~1100) and the perpetually-newborn
  worldline, which abandons its charge at every self-continuation step, starves
  even faster (width → 1 immediately). See
  `math/event_driven_shadow_analysis.md` for the full study, the
  identity/charge-mismatch diagnosis, and the follow-up studies on the
  closed-motif Observer (below).
- `generate_braided_motif_graph` — the v0.7 answer to that diagnosis: the
  Observer as a *closed motif* (matter, TEI 6ter.3-D) — a worldtube of
  W-node antichain generations braided by 2 internal parents per node, with a
  measured metabolism (background captures under the same antichain rule) and
  entropy by generational rotation. Structural prediction: k=2 cannot make
  matter (zero capture slots). Result of the pre-registered halo A/B study:
  **closure cures the evaporation** — the motif holds a stationary,
  nontrivial transverse width (~1.6·W) indefinitely under both routings, the
  first persistent structure in this project — but the refractive **halo is
  zero-to-negative at every mass tested** (W ∈ {2,4,8}), so matter persists
  yet still does not gravitationally retain space around its body. A
  conservation-law fix followed (capture now *consumes* its prey — pending
  event invalidated and rescheduled with charge-grown delay, per TEI 7.7's
  "conserved until interpretation"): the charged slow **accretion belt** then
  forms exactly as designed (anchor charge up to ~470 under refraction, i.e.
  Canal 1, local time dilation near mass) — but the halo verdict is still
  negative, and a targeted verification shows why: the motif is a **pure
  absorber** (membrane nodes are the only nodes exempt from the event heap),
  and the interval width measures emitted-then-reabsorbed flux — Canal 2,
  "espace sécrété", which requires radiation the motif does not yet have.
  Structural radiation was then added (retired generations re-enter the event
  heap; entropy = emission, per TEI 6bis.2) — the wake is real, but the halo
  verdict stayed negative (an incumbent-hub charge monopoly, plus a suspected
  throughput bound on any single body's self-halo). Same file for all
  studies and diagnoses.
- `generate_two_motif_graph` + `first_contact_lag` — the two-body
  ("Earth-Mars", TEI 6bis.4) probe: two closed motifs born as localized
  clusters at a controlled relational separation, cross-couplings counted by
  direction and timed. Result: **the first reproducible positive refractive
  differential of the project** — separated bodies find each other in 5/10
  refractive runs vs 0/10 blind, with timed infall (wake coupling, then body
  contact ~45-110 generations later, then merger) — but no stationary
  inter-body channel forms (outcomes are bimodal: silence or fusion), so
  "space between bodies" still does not exist in the model. Observational
  metrology then proved the metric recedes ~1.08 hops/generation and outruns
  the radiated signal 2:1 (a measured causal event horizon), and that infall
  is a three-phase "zipper" (capture-edge knitting), not constant
  acceleration. An "angular momentum" attempt (a tangential-kick initial
  condition, `kick_ticks`/`kick_mode` on `generate_two_motif_graph`, laws
  untouched) then failed by ejection: the burn starves the body and the
  proper-motion decomposition shows **no tangential drift is injected and none
  persists**.
- `generate_three_motif_graph` + `triangle_angle` — the inertia question in
  the frame where it is actually well-posed. With only two bodies there is a
  single distance (a 1D line), so a transverse axis cannot exist: the two-body
  "no tangential drift" reading was measuring a coordinate that isn't there. A
  transverse coordinate first exists with **three** bodies — A and B fix a
  baseline, and C's angle off it (graph law of cosines on the three pairwise
  hop distances, measured in the past metric) is a scale-invariant 2D position
  from which common recession cancels. C's `test_mode` runs the A⊕B fusion
  braid and a prepared tangential kick against a pre-registered `forced`
  instrument control. Verdict (5 seeds × 900 generations): the forced control
  moves the angle **ballistically** (drift exponent 1.21 — the observable is
  sensitive), while every physical mode is **diffusive** (~0.56–0.59). So
  **no tangential inertia**, now a positive null in the correct frame — the
  substrate has no angular momentum because **it has no inertia** (it conserves
  what a body is and where it is, but not how it moves). A **topological spin**
  was then tried as the inertia carrier (`test_mode="chiral"`,
  `chirality=±1`: a strict-handedness braid whose intake heading circulates one
  fixed direction — topologically robust, no free knob). It *improves*
  metabolism (capture 86–91% vs 67%) but stays **diffusive for both
  handednesses** (0.49 and 0.64), with no mirror-antisymmetric drift: the
  substrate can carry a conserved topological charge but does not convert it
  into a conserved rate of motion — a spin is part of *what a body is*, not
  *how it moves*. A strict-Markov reframing (movement as a "QR code": a
  present structure whose reading displaces and reproduces it, Φ(σ)=T(σ))
  then produced `test_mode="front"` — the **self-collimating accretion
  front**: all capture walks start from the membrane's external in-edges (its
  present prey pool). The encoding *works* — the feedback self-perpetuates
  for 800+ generations — but its fixed point is **capture-lock, 5/5 seeds**:
  C attaches to the nearest reference body and rides it at hop distance 1-3
  forever, eating 94-97% of its captures from the host's membrane. In a
  perishable flux the only renewable intake locus is another worldtube, so a
  self-perpetuating displacement state points at *matter*, not *space*: the
  QR code of movement compiles into gravitational capture — incidentally the
  project's **first stable two-body bound state** (neither silence nor
  merger), though at contact range only. The program's last option
  (`test_mode="strict"`: captures must be causally independent of the whole
  membrane — the body as a whole interprets) failed its metabolic gate and
  measured why: a body's neighbourhood contains **0% strictly-independent
  nodes out to radius 6, at any age** — local space is entirely the body's
  own causal entanglements, so there is no causally-fresh space to move
  into; the one escape observed is, again, locking onto another body's
  worldtube. See `math/event_driven_shadow_analysis.md` for the full arc.
- `generate_soup_graph` — the **primordial soup** (material genesis): N=20
  bodies, all under the accretion-front rule, sown at random, blind
  selection (pre-registered death cutoff; fossils stay edible). Result: a
  two-phase architecture controlled by flux supply. **Abundance → a gas**
  (60/60 survive, transient contacts, and the few-body capture-lock does
  not reproduce — 0/60: the parasitic binary was a low-density artifact).
  **Scarcity → condensation**: cross-body diet jumps to ~90%, and bodies
  condense into a compact **reciprocal trophic web** (intra-cluster feeding
  ~96%, no dominant host) that defeats scarcity by collectively recycling
  its own radiated matter. Zero deaths in either phase: survival and
  aggregation are the same act. A 5-seed crystallography pass shows **the
  shape is a law, the size is stochastic**: the cluster is always a dense
  homogeneous mutual-grazing clique — a *liquid droplet* (not a
  star/chain/ring, no crystalline core), with a saturated core and an
  unsaturated free-valence surface, but its size varies (4–9 across seeds)
  and the universe makes several coexisting droplets. See
  `math/event_driven_shadow_analysis.md`, last section.
- `grazing_bond_volatility` — an **emergent thermometer** for the soup
  (temperature = topological volatility of the grazing bonds, which TEI does
  not encode). A single observable resolves **three states of matter**,
  ordered monotonically by flux supply: **gas** (abundance — bond turnover
  0.96, no permanent bonds), **liquid** (scarcity — 0.81, denser and more
  viscous), and, at low flux *plus a long horizon*, a **solid** — 2/11 seeds
  crystallize a near-permanent directed-bond network (turnover collapses to
  ~0.1, frozen-bond fraction jumps to 0.6–0.9), a sharp stochastic nucleation
  with the rest left supercooled. Flux alone does not freeze it; flux-low +
  time does. See `math/event_driven_shadow_analysis.md`, last section.

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

4. Test the local, non-embedded Causal Shadow Rule (shortest-path hops by default):
   ```bash
   python sim/graph_generators.py --mode tei-shadow --k 3 --N 100000 --ticks 20 --seed 42 --out data/tei_shadow_k3.npz
   ```
   Or re-read the same rule using longest-path depth instead:
   ```bash
   python sim/graph_generators.py --mode tei-shadow --k 3 --N 100000 --ticks 300 --depth-metric longest --seed 42 --out data/tei_shadow_k3_longest.npz
   ```

5. Test the event-driven, observer-relative version of the rule:
   ```bash
   python sim/graph_generators.py --mode event-shadow --k 3 --observer-ticks 300 --warmup-events 3000 --walk-hops 8 --background-ratio 50 --seed 42 --out data/event_shadow_k3.npz
   ```

6. Run unit tests:
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
  event_driven_shadow_analysis.md
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
