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
- The CLI in `sim/graph_generators.py` supports two modes, `random-dag` and
  `sprinkling` — see its module docstring and `--help` for parameters.
- `data/` and `figures/` are gitignored except for `.gitkeep`; generated
  artifacts should be reproducible from the scripts, not committed as
  fixtures.

## Current open question (do not "solve" it with a shortcut)

The actual TEI question this toy model targets — why local, non-embedded causal
coupling would produce polynomial connectivity growth with exponent 3 instead
of the generic exponential growth of an arbitrary graph — is **not** answered
by the current `sprinkle_minkowski` generator, which imposes the embedding
dimension externally. If asked to "solve" or "derive" this, don't produce a
generator that secretly bakes in dimension 3 (e.g. via a hardcoded embedding)
and present it as a derivation — that is exactly the failure mode (TEI 3.x)
this project's discipline exists to prevent. A genuine attempt would need a
generation rule with no imposed embedding, whose emergent connectivity growth
is then measured, not assumed.

## Keeping this file current

If the toy model grows (new generators, an actual attempt at the non-embedded
exponent-3 question, a gravity-deflection calculation per TEI 7.7-7.8), update
this file's layout section and governing-discipline section to match — don't
let it drift into describing scaffolding that no longer reflects the code.
