# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.

## What this repository is

A computational **toy model** in support of the "Theory of Informational
Emergence" (TEI), an ontological framework by Stéphane Goulet (currently at
version 5.0) proposing that observed space, time, and matter emerge from a
discrete, non-spatial causal substrate. See `README.md` for the project's
current scope and `math/causal_set_dimension.md` for the provenance of the one
quantitative result this repo currently reproduces.

## The project's governing discipline — read before adding any result

An earlier version of TEI (3.x) derived the fine-structure constant and CMB
peak ratios via post-hoc numerical fitting dressed up as calculation; both were
independently shown to be false. Since then the project enforces a strict rule
that **must be followed in this codebase too**: never treat a number that
"comes out right" as validated unless its provenance is independent and stated
explicitly. Concretely:

- Any new script that reports a numeric result (an exponent, a coefficient, a
  ratio) must document where that result's correctness criterion comes from —
  is it reproducing a *known, citable* mathematical/physical relation (like
  `math/causal_set_dimension.md` does for the Myrheim-Meyer estimator), or is it
  an actual open TEI claim being tested? Never blur the two.
- Don't present a simulation that happens to match a hoped-for number as
  confirmation of a TEI hypothesis without saying explicitly what would have
  falsified it and why it didn't.
- When extending `sim/`, keep the same honesty about what a given generator
  does and doesn't establish (see the module docstring in
  `sim/graph_generators.py` for the pattern: what's standard theory vs. what
  remains genuinely open).

## Layout

```
sim/graph_generators.py     # causal graph generators + growth-exponent measurement
tests/test_graph_generators.py
math/causal_set_dimension.md   # provenance note for the tau^dim scaling law used
math/tei_shadow_rule_analysis.md  # raw results for the non-embedded Causal Shadow Rule generator
math/event_driven_shadow_analysis.md  # design history for the async, observer-relative generator (incl. two dead ends)
data/, figures/              # generated outputs (gitignored — regenerate via sim/)
environment.yml               # conda env "tei"
pyproject.toml                 # pytest config (pythonpath = ".")
.github/workflows/ci.yml       # runs pytest on push/PR
```

## Working in this repo

- Environment: `conda env create -f environment.yml && conda activate tei` (or
  just `pip install numpy scipy networkx matplotlib pytest` — no compiled
  dependencies).
- Tests: `pytest -q` from the repo root (relies on `pyproject.toml`'s
  `pythonpath = ["."]` so `from sim.graph_generators import ...` resolves;
  don't remove that without also fixing imports).
- The CLI in `sim/graph_generators.py` supports four modes, `random-dag`,
  `sprinkling`, `tei-shadow`, and `event-shadow` — see its module docstring
  and `--help` for parameters. `random-dag` and `tei-shadow` also take
  `--depth-metric {shortest,longest}` (default `shortest`) to choose between
  `reachable_within_hops` and `reachable_within_depth` — see
  `math/tei_shadow_rule_analysis.md` Part B for why the longest-path reading
  exists and what it does and doesn't change. `event-shadow` is the
  asynchronous, observer-relative generator (`--observer-ticks`,
  `--warmup-events`, `--walk-hops`, `--background-ratio`) — read
  `math/event_driven_shadow_analysis.md` before touching it: it documents two
  design attempts that failed outright (a fixed-node Observer starves under
  both global-heap and local-random-walk selection), and why `walk_hops` /
  `background_ratio` need to be reasonably large or the measured curve is
  indistinguishable from a trivial straight line.
- `data/` and `figures/` are gitignored except for `.gitkeep`; generated
  artifacts should be reproducible from the scripts, not committed as
  fixtures.

## Current open question (do not "solve" it with a shortcut)

The actual TEI question this toy model targets — why local, non-embedded causal
coupling would produce polynomial connectivity growth with exponent 3 instead
of the generic exponential growth of an arbitrary graph — is **not** answered
by `sprinkle_minkowski`, which imposes the embedding dimension externally. A
genuine attempt needs a generation rule with no imposed embedding, whose
emergent connectivity growth is then measured, not assumed.

One such attempt now exists: `generate_tei_shadow_graph` implements TEI's
"Regle de l'Ombre Causale" (bounded valence + strict transitive reduction, no
embedding). Measured results are in `math/tei_shadow_rule_analysis.md` — read
that file before citing or re-deriving this generator's exponent. Summary:
it breaks the generic saturating-exponential regime under both notions of
causal depth tried (shortest-path hops and longest-path depth), but the
measured exponent **does not settle onto a stable value under either metric**
(it drifts upward with hop count, or rises then falls with longest-path
depth), so it does not confirm N³. Treat this as an open, unresolved attempt,
not a result to build on. If asked to "solve" or "derive" this question,
don't produce a generator that secretly bakes in dimension 3 (e.g. via a
hardcoded embedding, or by tuning parameters until an exponent estimate lands
near 3) and present it as a derivation — that is exactly the failure mode
(TEI 3.x) this project's discipline exists to prevent. This includes tuning
which *metric* (hop count vs. longest path, or a future third option) is
reported based on which one happens to land closer to 3 for a given `k` —
report what the measurement shows, not the reading that flatters the
hypothesis.

A second attempt, `generate_event_driven_shadow_graph`, removes two remaining
god's-eye-view assumptions from the first generator (a global tick loop, and
parent sampling from the entire front). Its architecture is validated and
tested, and a 50-seed statistical study has now been run —
`math/event_driven_shadow_analysis.md` documents both the design process
(including two attempts that failed outright: a fixed-node Observer, rather
than a self-continuing worldline, could not accumulate ticks under either a
global heap or a local random walk) and the study results. The verdict is
**negative and stronger than for `tei-shadow`**: the Observer's causal-cone
exponent is ~1.0-1.5 (never near 3), depends on `k`, drifts toward 1 for
k=3/4, and is not even independent of the arbitrary `background_ratio`
simulation parameter — meaning "the exponent of the rule" is not a
well-defined quantity here. Do not try to rescue this by searching
`(k, background_ratio, walk_hops)` space for a triple that lands near 3; the
parameter-sensitivity table in that file is exactly the evidence that such a
find would be meaningless (and doing so is the TEI-3.x failure mode).

A follow-up (same file) changes the *observable* rather than the generator:
`interval_width` / `max_antichain_size` measure the transverse width (max
antichain) of an Alexandrov interval, whose exponent estimates the spatial
dimension `d-1` without the worldline chain in the floor. This genuinely
fixes the `background_ratio` pathology (the width exponent *is* invariant
under it), but the exponent still depends on `k` and still drifts, so it
still does not give a stable emergent dimension. Note the disqualified
near-hit recorded there (k=3 early window gives d-1 ~ 2.0, i.e. d ~ 3, but it
drifts and is k-specific) — it is documented and defused precisely so no one
re-reports it as a result. The cheap longest-path-depth-level proxy for width
was tried and rejected (underestimates the exact max antichain 3-7x); use the
exact `max_antichain_size`.

## Keeping this file current

If the toy model grows further (new generators, refinements to the shadow
rule, a gravity-deflection calculation per TEI 7.7-7.8), update this file's
layout section and governing-discipline section to match — don't let it
drift into describing scaffolding that no longer reflects the code.
