# Provenance note: causal-set volume-dimension scaling

`sim/graph_generators.py` measures, for a Poisson sprinkling of points into
`dim`-dimensional Minkowski coordinates, how the number of points in a point's
causal future grows with proper time. This note records where that scaling law
comes from, so the result is never mistaken for something derived by this
project (see TEI 5.0, Partie 1: no numeric agreement is accepted without
independent provenance).

## The scaling law

In flat `dim`-dimensional Minkowski spacetime (1 time + `dim - 1` space
dimensions), the solid future light cone up to proper time `tau` from a point is

    C(tau) = { (t, x) : 0 <= t <= tau, |x| <= t }

Its volume is the stack of spatial balls of radius `t`, whose volume in
`dim - 1` spatial dimensions is proportional to `t^(dim - 1)`:

    Vol(C(tau)) = integral_0^tau  k * t^(dim - 1) dt  =  k / dim * tau^dim

For a Poisson sprinkling of density `rho`, the expected number of points inside
`C(tau)` is `rho * Vol(C(tau))`, i.e. proportional to `tau^dim`. This is the
standard **Myrheim-Meyer dimension estimator** used throughout causal set
theory to read off the embedding dimension of a sprinkled causal set from
interval cardinalities.

References (established literature, not this project's work):

- J. Myrheim, "Statistical geometry", CERN preprint TH-2538 (1978).
- D. Meyer, *The Dimension of Causal Sets*, PhD thesis, MIT (1988).
- L. Bombelli, J. Lee, D. Meyer, R. Sorkin, "Space-Time as a Causal Set",
  Phys. Rev. Lett. 59, 521 (1987).

## What this does and does not establish for TEI

- It **does** give a working instrument: `reachable_within_ticks` reproduces
  this `tau^dim` growth numerically (see `tests/test_graph_generators.py`),
  confirmed against `dim = 2, 3, 4`.
- It does **not** address TEI's actual open question (Partie 7.5): here the
  embedding dimension `dim` is imposed externally on the sprinkling before any
  point is placed. TEI asks why a *local, non-embedded* coupling rule would
  produce polynomial connectivity growth with exponent 3 at all, rather than
  the generic exponential growth of an arbitrary causal DAG (reproduced by
  `generate_random_dag`). That question — deriving the exponent instead of
  assuming an embedding that guarantees it — remains open.
