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

The generator itself (bounded valence + strict transitive reduction) is not
in question and is unchanged throughout this note. What is compared below is
two different readings of "how far is a node from the origin, in ticks" on
the *same* graphs: shortest-path hop count (Part A, the original measurement)
and longest-path depth (Part B, added afterward on the hypothesis that hop
count's geometric shortcuts, not the generator, were responsible for the
drifting exponent seen in Part A).

## Part A — shortest-path hops as the tick measure

### What was measured

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

### Raw results

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

### Reading of the results

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

### Part A conclusion

This specific realization of the Causal Shadow Rule (random selection from a
valence-bounded front, hop count as the tick measure) does **not** produce a
stable polynomial growth exponent, and in particular does not confirm N³. It
does demonstrate that the antichain/transitive-reduction constraint alone is
enough to break the generic saturating-exponential regime, which is a
genuine, non-trivial finding in its own right — but the open question from
TEI 7.5 (why a local, non-embedded rule would produce a *stable* exponent of
exactly 3) remains unanswered by this generator as implemented under this
metric. The candidate explanation offered above (long-range, small-world-like
jumps from front nodes that stay eligible for a long time) motivates Part B.

## Part B — longest-path depth as the tick measure

### Rationale

If every edge in the graph is itself a relay delay — a unit of sequential
computation that must complete before its target event can occur — then an
event is only reached once *every* instruction chain leading to it, including
the slowest one, has finished. Under that reading, the shortest path between
two nodes is not the physically meaningful "number of ticks" at all: it is a
classical geometric shortcut, and this purely relational graph has no
embedded metric to justify preferring it. The longest directed path from the
origin is the candidate "proper time" analogue instead. This is implemented
as `longest_path_depths` / `reachable_within_depth` in
`sim/graph_generators.py` (dynamic programming over a topological order of
the origin's descendant subgraph).

### What was measured

Same graphs as Part A (`generate_tei_shadow_graph(N=300000, k, seed)` for
`k = 2, 3, 4`, 5 seeds each), re-read using `reachable_within_depth` instead
of `reachable_within_hops`, up to depth 300. Two things are worth noting
about scale before reading the numbers: (1) the *unbounded* longest-path
depth from origin 0 reaches into the thousands (max depth ~2,000-2,500,
mean ~1,200-1,450 across the three `k` values at `N = 300,000`) — depth 300
is therefore still well inside the early-growth region, not close to the
tail of the distribution; (2) `nx.descendants(graph, 0)` shows origin 0 is
eventually an ancestor of essentially the *entire* 300,000-node graph (all
but 2-4 nodes) for every `k` tested — the front-recycling mechanism (a node
stays eligible as a parent until its valence is used up, however long that
takes) means an early node's causal shadow eventually spans almost
everything, it just takes many more sequential relays to get there than the
shortest path suggests.

A first pass at this analysis fit each window's slope using the sliced
array's local index (1, 2, 3, ...) as the x-axis instead of the true depth
values (e.g. 150, 151, 152, ... for a window starting at depth 150). That
bug produced an apparently flat, stable "exponent" of about 0.3 across a
wide range — which would have been a striking (and wrong) result. It is
recorded here, not in a private note, because catching a false stabilization
before reporting it is exactly the discipline this project asks for (TEI 5.0,
Partie 1): the numbers below use the corrected fit (true depth values on
both axes of the log-log regression).

### Raw results — coarse windows

Log-log slope fit per window, mean ± standard deviation across 5 seeds,
`N = 300,000`:

| k | depth 1-15 (transient) | depth 15-60 | depth 60-150 | depth 150-220 | depth 220-300 (tail) | depth 1-300 (full) |
|---|---|---|---|---|---|---|
| 2 | 1.037 ± 0.018 | 1.310 ± 0.075 | 2.310 ± 0.058 | 3.501 ± 0.170 | 2.657 ± 0.053 | 1.930 ± 0.007 |
| 3 | 1.075 ± 0.022 | 1.380 ± 0.023 | 1.942 ± 0.024 | 2.612 ± 0.135 | 2.257 ± 0.049 | 1.720 ± 0.018 |
| 4 | 1.101 ± 0.022 | 1.359 ± 0.025 | 1.821 ± 0.051 | 2.265 ± 0.058 | 1.944 ± 0.099 | 1.622 ± 0.009 |

### Raw results — fine sliding-window profile

To check whether the coarse windows above were hiding or creating structure,
the local slope was refit in a ±20-depth window centered on each value below
(3 seeds, `N = 300,000`):

| k | 30 | 50 | 70 | 90 | 110 | 130 | 150 | 170 | 190 | 210 | 230 | 250 | 270 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 1.27 | 1.41 | 1.83 | 2.11 | 2.50 | 2.83 | 3.08 | 3.35 | **3.53** | 3.14 | 2.91 | 2.78 | 2.62 |
| 3 | 1.31 | 1.52 | 1.65 | 1.92 | 2.04 | 2.19 | 2.35 | 2.37 | 2.57 | **2.70** | 2.38 | 2.27 | 2.19 |
| 4 | 1.26 | 1.52 | 1.70 | 1.74 | 1.82 | 2.06 | 2.25 | **2.28** | 2.28 | 2.18 | 2.12 | 1.96 | 1.91 |

(bold = the peak local slope observed in the measured range, for each `k`)

### Reading of the results

**The exponent does not stabilize under this metric either — it traces a
hump, not a plateau.** For all three `k`, the local slope rises
monotonically from about 1.3 at depth 30 to a peak somewhere between depth
170 and 210, then declines again toward the edge of the measured window
(depth 300). This is a different shape of non-stationarity than Part A (which
drifted upward without turning over in the range measured), not a
confirmation of a fixed value.

**Does this "clean up" the small-world-shortcut effect from Part A?** Partly,
and differently than hoped. The pure monotonic climb seen with hop count is
gone — replaced by a rise-then-fall curve. That is consistent with the
Part-A hypothesis that long-range, long-lived front edges were inflating hop
counts (longest-path depth is far less sensitive to a single long edge, since
it takes the *slowest* route, not the fastest). But removing that artifact
did not reveal a hidden stable exponent underneath; it revealed a different
non-power-law shape. Both metrics agree on one thing: the growth is not a
clean, fixed-exponent power law anywhere in the ranges tested.

**On the numeric proximity to 3:** for `k = 2`, the peak local slope (3.53 at
depth ~190) passes near 3 on its way up (crossing 3 somewhere around depth
150-160) and again on its way back down. For `k = 3` the peak (2.70) and for
`k = 4` the peak (2.28) never reach 3 at all. A curve that is continuously
rising and falling will cross or approach any fixed reference value somewhere
in its range purely as a matter of arithmetic — that is exactly the kind of
transient numeric coincidence the project's discipline (TEI 5.0, Partie 1)
says must not be read as confirmation. There is no `k`-independent plateau
at 3, and two of the three `k` values never even reach it.

**What is a plausible (unconfirmed) explanation for the hump?** The rising
part is consistent with the causal shadow spreading out through progressively
more of the graph's branching structure as depth increases. The falling part
is plausibly a finite-size effect: `N = 300,000` bounds how much of the graph
exists at all, and although depth 300 is still early relative to the full
depth range (mean ~1,200-1,450), some saturation pressure from the finite
graph could already be curving the tail downward. Pushing `N` an order of
magnitude higher (to `10^6`) to check whether the hump simply shifts outward
(finite-size artifact) or persists at the same depth (a real feature of the
rule) was attempted but was not computationally tractable in this toy
model's current implementation within a reasonable runtime, so this remains
an open, explicitly flagged limitation rather than a resolved point.

## Combined conclusion (Parts A and B)

Answering the two questions this second pass set out to answer, directly:

1. **Does switching from shortest-path hops to longest-path depth smooth out
   the small-world-shortcut effect?** Yes, in the sense that the monotonic
   upward drift from Part A disappears and is replaced by a rise-then-fall
   curve, consistent with long-range front edges having inflated hop-based
   reachability counts. But "smoothing out an artifact" is not the same as
   "revealing a stable law": the replacement curve is still not flat anywhere.
2. **Does the growth exponent stabilize within the measured window?** No.
   Under neither metric does the local slope settle onto a constant value
   for any sustained stretch of the measured range, for any of `k = 2, 3, 4`.

Across both metrics, the Causal Shadow Rule (as currently implemented —
random selection from a valence-bounded front, no additional structure)
robustly breaks the generic saturating-exponential regime of an arbitrary
causal DAG. That remains a genuine, reproducible, non-trivial result. But
neither metric supports treating any measured number — 2.6, 2.7, 3.5, or
anything else — as *the* growth exponent of this rule, and in particular
**neither confirms the N³ hypothesis from TEI 7.5**. The open question
(why a local, non-embedded rule would produce a stable exponent of exactly 3)
remains unanswered by this generator as implemented, under both measures of
causal depth tried so far.

Candidate refinements worth trying next, none of which are implemented here:
bounding how long a node may remain in the front regardless of remaining
valence (to test whether that specifically is what drives the Part A drift);
running at larger `N` to check whether the Part B hump is a finite-size
artifact or a persistent feature; and choosing front candidates by a rule
other than uniform random selection, since nothing about the rule as stated
requires uniform-random parent selection specifically.
