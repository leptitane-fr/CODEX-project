# Analysis: the TEI Causal Shadow Rule and the N³ growth question

This note reports raw, unedited results from `generate_tei_shadow_graph`
(`sim/graph_generators.py`), which implements TEI 5.0's own candidate
mechanism for the open question in Partie 3.2/7.5: can a purely local
assembly rule, with **no imposed embedding or metric**, produce polynomial
connectivity growth (ideally `N^3`) instead of the generic exponential growth
of an arbitrary causal DAG?

Per the project's own discipline (TEI 5.0, Partie 1): these numbers are
reported as measured, including the parts that do not support the hoped-for
outcome. No parameter was tuned to make an exponent land near 3.

## What was measured

- **Generator**: `generate_tei_shadow_graph(n_nodes, k, valence=k)` — each new
  node connects to up to `k` existing "front" nodes, constrained to a local
  antichain (no two chosen parents may already be connected by a directed
  path — the strict transitive-reduction / "no shortcut past a relay" rule).
  Each node can be chosen as a parent at most `valence = k` times before
  leaving the front.
- **Growth measurement**: `reachable_within_hops(graph, origin=0, max_hops)`,
  the same cumulative-count-per-hop measure already used for
  `generate_random_dag`. A purely combinatorial graph has no continuous
  metric, so hop count is the only available notion of "tick" here — unlike
  `sprinkle_minkowski`, where ticks are continuous proper-time buckets (see
  `math/causal_set_dimension.md`). This difference in what "a tick" means
  between the two generators matters for reading the results below.
- **Protocol**: for `k = 2, 3, 4`, 5 seeds each, `N = 300,000` nodes,
  `max_hops = 50`. For each run, a single power-law exponent was fit by
  log-log regression over the full hop range ("slope_all"), and separately
  over the first 25 hops ("first_half") and last 25 hops ("second_half"), to
  check whether the exponent is stable or drifting with depth.

## Raw results

| k | slope (hops 1-50) | slope (hops 1-25) | slope (hops 26-50) | mean reachable count at hop 50 (of N=300,000) |
|---|---|---|---|---|
| 2 | 2.241 ± 0.045 | 1.725 ± 0.065 | 4.127 ± 0.081 | 6,947 |
| 3 | 2.613 ± 0.074 | 2.107 ± 0.095 | 3.506 ± 0.229 | 20,645 |
| 4 | 2.718 ± 0.051 | 2.358 ± 0.092 | 2.808 ± 0.210 | 41,111 |

(mean ± standard deviation across 5 seeds; a second, independent run at
`N = 80,000`, `max_hops = 40` for `k = 4` gave slope_all = 2.651 ± 0.055,
first-half = 2.183 ± 0.110, second-half = 3.250 ± 0.177 — consistent within
the run-to-run variation expected from a shorter hop window.)

For comparison, `generate_random_dag(N=300,000, out_degree=3)` reaches
299,998 of 300,000 nodes (i.e. essentially the entire graph) by hop 7 — no
power-law fit is meaningful for that curve, since it saturates rather than
following a sustained polynomial trend.

A finer per-hop view (local log-log slope via central differences, `k=3`,
single seed) shows the origin of the first-half/second-half gap: the slope is
noisy at every hop (fluctuating roughly between 2.4 and 4.0 past the initial
small-count transient in hops 1-9) rather than settling onto a flat line —
it is not that the curve is clean-but-shifted, it is that it does not
converge to a fixed value within the range measured.

## Reading of the results

**What the rule does establish:** the causal shadow rule sharply suppresses
the naive generic-exponential regime. Where `generate_random_dag` saturates
the entire graph within ~7 hops regardless of `N`, the shadow-rule graphs
reach only 2-14% of a 300,000-node graph after 50 hops. Bounding valence and
forbidding transitive shortcuts genuinely changes the qualitative growth
regime — this is a real, reproducible effect of the rule, not an artifact.

**What it does not establish:** the measured exponent is not stable. For all
three values of `k`, the fitted slope increases substantially between the
first and second half of the hop range (by roughly +1.4 to +2.4), and the
per-hop local slope is noisy rather than flat throughout the measured range.
This is a qualitatively different (and weaker) result than the sprinkling
model's behavior, where the exponent is stable and matches the imposed
embedding dimension to within measurement noise (see
`math/causal_set_dimension.md`). **A drifting exponent is not a confirmed
power law**, and in particular this data does not support treating any of
these numbers as "the" growth exponent of the rule.

**On the numeric proximity to 3:** for `k = 3`, the full-range exponent
(2.613) and the two half-window exponents (2.107, 3.506) bracket 3. This is
exactly the kind of coincidence the project's own discipline (TEI 5.0,
Partie 1) says must not be treated as confirmation without independent,
stable evidence — and stable evidence is precisely what is missing here: the
number is only "close to 3" in the sense that 3 sits inside a fairly wide,
still-widening range, not because the measurement has converged there. Taken
at face value, this data does not confirm the N³ hypothesis for this
generator.

**A candidate (unverified) explanation for the drift:** because a front node
retains its remaining valence until used up rather than being retired after
one use, a node can still be selected as a parent long after — in generation
order — it first appeared, producing edges that span very large jumps in
node index within a single hop. In a metric-embedded model, a "tick" is a
bounded proper-time step, so no single hop can skip an arbitrary distance;
here, hop count has no such bound built in, and a small number of
long-lived, long-range edges could act like small-world shortcuts, inflating
the reachable count at a given hop faster than any fixed power of that hop
as more of them accumulate with depth. This reads as plausible from the data
but has **not** been isolated or confirmed as the mechanism — it is offered
as a hypothesis for follow-up work, not a result.

## Conclusion

This specific realization of the Causal Shadow Rule (random selection from a
valence-bounded front, hop count as the tick measure) does **not** produce a
stable polynomial growth exponent, and in particular does not confirm N³. It
does demonstrate that the antichain/transitive-reduction constraint alone is
enough to break the generic saturating-exponential regime, which is a
genuine, non-trivial finding in its own right — but the open question from
TEI 7.5 (why a local, non-embedded rule would produce a *stable* exponent of
exactly 3) remains unanswered by this generator as implemented. Candidate
refinements worth trying next, none of which are implemented here: bounding
how long a node may remain in the front regardless of remaining valence (to
suppress long-range jumps), or measuring growth by longest-path depth rather
than shortest-path hop count (less sensitive to shortcut edges).
