# Design history: the event-driven, observer-relative Causal Shadow Rule

`generate_event_driven_shadow_graph` (`sim/graph_generators.py`) is a second
realization of TEI's Causal Shadow Rule, built to remove two god's-eye-view
assumptions still present in `generate_tei_shadow_graph`: a global `for` loop
that advances every node in lockstep, and parent selection sampled uniformly
from the entire front (which requires knowing the whole universe's history at
every step). This note records the design process, including two attempts
that failed outright, because the failures are informative in their own right
and the project's discipline (TEI 5.0, Partie 1) asks that near-misses be
surfaced, not quietly discarded.

## What was being solved

Three requirements, validated in conversation before any code was written:

1. No global tick — node creation driven by an asynchronous event queue, each
   node with its own pending "next action" time.
2. No arbitrary saturation wall — out-degree ("charge") is unbounded; only the
   *delay* before a node's next action grows with its charge
   (`delay(charge) = 1 + charge`, strictly linear — each additional active
   relation costs exactly one silent-relay unit, never a geometric penalty).
3. Growth measured from a designated Observer's own point of view (its own
   accumulated ticks), not from an external, God's-eye count.

## Attempt 1: global heap + uniform-random front sampling — failed (bug)

First prototype kept the original generator's fixed valence wall (a node
retired after `k` uses) inside the new async engine. Result: the elected
Observer exhausted its own valence and stopped participating after exactly
`k` ticks (2 ticks measured for `k=2`) — precisely the "arbitrary saturation
wall" requirement 2 forbids. Implementation bug, not a design flaw: fixed by
removing the wall entirely (unbounded charge, as specified above).

## Attempt 2: global heap + local random walk for co-parents — failed (starvation)

With the wall removed, and co-parent selection changed from uniform-front
sampling to a bounded local random walk (2-3 hops from the trigger, over
existing edges), the *generator* worked fine for building a graph — but a
**fixed** Observer node still failed to accumulate ticks: instrumented
directly, a fixed node was hit only **8 times after 50,000 events** (flat
from event 35,000 to 50,000 — not slowly improving, stalled).

Root cause, confirmed with a minimal isolated test (uniform sampling from a
pool that gains one member per draw): a fixed candidate's cumulative hit
count grows only logarithmically and effectively plateaus — **15 hits after
2,000,000 draws** from a linearly-growing pool. A shared global heap, even
with locally-selected co-parents, reduces to the same statistics once every
node's own charge is low and comparable: rescheduling puts a node "near the
front" of the heap, but the size of that "near the front" cohort keeps
growing too, so any one fixed node's relative share keeps shrinking. This is
not a performance problem (running longer does not fix it) — it is a
structural one.

## Attempt 3: single wandering cursor, inverse-charge-weighted — failed worse

Next attempt replaced the shared heap with a single "activity cursor" that
hops to a neighbor of the most recently created node, weighted toward
lower-charge (less loaded) neighbors — no global comparison at all. Result:
**0 hits on a fixed observer node after 20,000 events.** Diagnosis: any local
process on a growing DAG, where new edges are drawn from the *current*
position's neighborhood, structurally sweeps forward through the DAG's
frontier and does not return to older regions (a form of transience). This
is not specific to the weighting scheme — it is a property of "always attach
near the newest activity" as a growth rule.

## The resolution: the Observer is a worldline, not a node

TEI 5.0's own ontology already states the fix (Partie 6ter.3-D): a persistent
object is a "motif ferme" — a closed loop of recurring executions — not a
single static point. Modeling the Observer as one fixed node that hopes to be
rediscovered was the wrong frame from the start. The Observer is instead a
**self-continuing worldline**: at each of its own ticks, its current self
picks co-parents via the same local random walk and antichain rule as
everything else, but *always* designates its own newly created child as its
next self. This guarantees steady, uncompeted progress — the Observer's own
proper time advances by exactly one tick per iteration, by construction,
"exactly as a real observer never feels their own time dilating" (matching
the descriptive-delay requirement below).

This resolved the starvation completely: the Observer reaches its full tick
budget every run, at negligible cost (well under a second for a few hundred
ticks).

## A second finding: the worldline alone measures nothing interesting

With only the worldline self-continuing and no *concurrent* background
growth, the Observer's causal future is exactly its own chain — a straight
line, slope 1 by construction, for any `k`. This is not a useful measurement:
it says nothing about branching or dimension, since nothing else in the
universe is choosing worldline members as co-parents.

Fix: run the general background dynamics (global heap + local walk, exactly
as validated for graph-building in Attempt 2) *concurrently* with the
worldline, interleaved at a fixed ratio (`background_ratio` background
events per worldline tick) — not via a time-based comparison. A time-based
interleaving (fire whichever of the worldline or the background heap has the
smaller scheduled time) was tried and abandoned: the background heap
accumulates a large backlog of closely-spaced low-delay entries, so its
clock advances far more slowly per event than the worldline's, and the
comparison let hundreds of thousands of background events fire per single
worldline tick before the run was killed for exceeding a reasonable time
budget.

With a fixed ratio, both `background_ratio` and `walk_hops` need to be large
enough for background events to actually walk back and reconnect with the
Observer's past — otherwise the curve stays close to the trivial linear
baseline. Measured (`k=3`, `warmup_events=3000`, `n_ticks_observer=300`,
single seed):

| background_ratio | walk_hops | final count (of 300 ticks) |
|---|---|---|
| 5 | 3 | 312 (barely above the linear baseline of 300) |
| 20 | 3 | 385 |
| 50 | 3 | 579 |
| 20 | 6 | 552 |
| 50 | 8 | 1,517 |
| 100 | 10 | 2,263 |
| 200 | 10 | 5,019 |
| 300 | 12 | 8,047 |

Defaults were set to `background_ratio=50`, `walk_hops=8` as a reasonable
middle ground between signal strength and runtime; both are exposed as
parameters (and CLI flags, `--background-ratio` / `--walk-hops`) since the
right values are a genuine open tuning question, not something to bake in
silently.

## Architecture status

The generator is implemented and tested (`tests/test_graph_generators.py`):
correctness of the antichain/transitive-reduction rule (checked
independently via `nx.has_path`, same method as the synchronous generator),
the worldline's chain structure, monotonicity of the growth curve, and the
`max_nodes` safety cap. The architecture works and produces a non-trivial,
measurable growth curve. The multi-seed statistical study called for at the
end of the design phase has now been run — its results are below.

## Multi-seed statistical study (the "test de verite")

Protocol: `k in {2, 3, 4}`, **50 seeds each**, `n_ticks_observer = 2000`,
`warmup_events = 3000`, `walk_hops = 8`, `background_ratio = 50`. These two
last parameters were fixed at the module defaults *before* looking at any
exponent, and were **not** adjusted afterward to move the result (a
sensitivity check on them is reported at the end, precisely because leaving
them free would otherwise be a hidden tuning knob). The measured quantity is
the size of the Observer's causal future (`observer_growth_curve`) as a
function of the Observer's own tick count, fit as a log-log slope in windows,
per seed, then averaged.

### Raw results — mean growth curve

Mean count (across 50 seeds) of nodes in the Observer's causal future, at
selected own-ticks:

| k | t=50 | t=100 | t=200 | t=400 | t=800 | t=1200 | t=1600 | t=2000 |
|---|---|---|---|---|---|---|---|---|
| 2 | 65.4 | 154.7 | 421.8 | 1204.8 | 3432.9 | 6253.6 | 9548.4 | 13379.7 |
| 3 | 84.3 | 244.1 | 734.8 | 2123.1 | 5389.6 | 8814.0 | 12236.4 | 15716.3 |
| 4 | 98.2 | 260.0 | 672.9 | 1615.2 | 3576.3 | 5651.4 | 7675.7 | 9804.1 |

Final-count spread across seeds (at t=2000): k=2 mean 13380 (min 8129, max
15767); k=3 mean 15716 (min 12979, max 18083); k=4 mean 9804 (min 8201, max
11307). The curve is reproducible seed-to-seed to within ~10%.

### Raw results — windowed log-log slope (exponent), mean +- std over 50 seeds

| k | 1-100 | 100-400 | 400-900 | 900-1400 | 1400-2000 | 200-2000 | 1-2000 |
|---|---|---|---|---|---|---|---|
| 2 | 1.126 +- 0.022 | 1.479 +- 0.027 | 1.524 +- 0.032 | 1.495 +- 0.033 | 1.490 +- 0.055 | 1.509 +- 0.029 | 1.437 +- 0.022 |
| 3 | 1.248 +- 0.033 | 1.567 +- 0.043 | 1.309 +- 0.032 | 1.169 +- 0.036 | 1.137 +- 0.024 | 1.274 +- 0.024 | 1.370 +- 0.023 |
| 4 | 1.270 +- 0.031 | 1.301 +- 0.047 | 1.149 +- 0.030 | 1.099 +- 0.022 | 1.065 +- 0.038 | 1.138 +- 0.024 | 1.224 +- 0.025 |

### Raw results — fine sliding-window local slope (half-window 75 ticks)

| k | 100 | 250 | 400 | 550 | 700 | 850 | 1000 | 1150 | 1300 | 1450 | 1600 | 1750 | 1900 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 1.29 | 1.48 | 1.49 | 1.48 | 1.66 | 1.46 | 1.57 | 1.41 | 1.64 | 1.25 | 1.49 | 1.59 | 1.37 |
| 3 | 1.51 | 1.56 | 1.44 | 1.36 | 1.33 | 1.15 | 1.10 | 1.37 | 0.97 | 1.35 | 0.98 | 1.16 | 1.24 |
| 4 | 1.41 | 1.27 | 1.19 | 1.16 | 1.15 | 1.14 | 1.17 | 1.17 | 1.00 | 1.13 | 1.08 | 1.07 | 1.04 |

### Parameter-sensitivity check (k=3, 7 seeds, slope over ticks 200-1000)

| background_ratio | walk_hops | slope |
|---|---|---|
| 50  | 8  | 1.365 +- 0.032 |
| 100 | 8  | 1.306 +- 0.049 |
| 200 | 8  | 1.221 +- 0.013 |
| 50  | 12 | 1.375 +- 0.053 |
| 100 | 16 | 1.314 +- 0.050 |
| 300 | 12 | 1.192 +- 0.027 |

### Reading of the results

**The exponent is nowhere near 3.** Every measured slope, for every `k` and
every window, lies between 1.0 and 1.6. The observer-relative, event-driven
architecture — despite being ontologically cleaner than the synchronous
generator (no global clock, no saturation wall, purely local sampling,
worldline Observer) — produces a causal-cone growth only modestly above
*linear*. That is the headline, and it is a negative result for the N^3
hypothesis, stated plainly. The lower bound of 1 is structural: the
Observer's worldline is a chain, which alone contributes exactly slope 1;
what sits on top of it (the background flux that walks back and reconnects to
the Observer's past) adds only a weak polynomial halo, not a jump to a higher
integer.

**The exponent depends on `k`.** k=2 settles near 1.5; k=3 and k=4 sit lower
and *decline* with depth toward ~1.1. A genuine emergent spatial dimension
cannot depend on an arbitrary antichain-size parameter — so whatever these
numbers are measuring, it is not a dimension in the sense TEI 7.5 needs.
(Note the non-monotonic ordering: k=2 gives the *highest* exponent, not the
lowest. More parents per node does not mean faster causal-cone growth from
the Observer's view — it means the graph spends more of its edges on local
antichain bookkeeping and less on reaching back to the Observer.)

**The exponent is not stable for k=3, 4.** For those two, the local slope
drifts monotonically downward across the measured range (k=3: 1.57 -> 1.14;
k=4: 1.30 -> 1.07), heading toward the bare-chain value of 1. Only k=2 shows
a roughly flat slope (~1.5) across ticks 100-2000 — stable, but at a
non-integer value, and only for that one `k`.

**Worst of all for interpretation: the exponent is not even a
parameter-independent invariant.** The sensitivity check shows the k=3 slope
sliding from 1.37 (background_ratio=50) down to 1.19 (background_ratio=300) —
monotonically with a parameter that has *no ontological fixing* in the
theory. `background_ratio` is a simulation convenience (how much background
flux to interleave per Observer tick), not a physical constant. If the
measured exponent moves when that knob moves, then "the exponent of the rule"
is not a well-defined quantity to begin with. This is a stronger negative
finding than the `tei-shadow` drift: there, the exponent at least did not
depend on a free simulation parameter; here it does.

### Conclusion

The event-driven, observer-relative architecture is a genuine conceptual
improvement — it removes the global clock and the global sampling that made
the synchronous generator ontologically suspect, and it realizes the
Observer as a worldline exactly as TEI 6ter.3-D describes. But on the one
question it was built to answer, the verdict from 50 seeds is unambiguous and
negative:

- the Observer's causal-cone growth exponent is ~1.0-1.5, never near 3;
- it depends on the free parameter `k`;
- it is unstable (drifts toward 1) for k=3 and k=4;
- and it is not even independent of the arbitrary `background_ratio`
  simulation parameter.

**This architecture does not confirm N^3, and does not produce a stable,
parameter-independent, integer growth exponent of any value.** Per the
project's governing discipline (TEI 5.0, Partie 1), this is recorded exactly
as measured — a clean negative result from a test that was set up to be able
to fail, and did. It closes the "does the observer-relative reading rescue
the exponent?" question with a no, and it should not be worked around by
searching parameter space for a `(k, background_ratio, walk_hops)` triple
that happens to land near 3: that search is the TEI-3.x failure mode, and the
parameter-sensitivity table above is precisely the evidence that such a
triple would be meaningless if found.

Raw per-seed curves are saved alongside this study (not committed; regenerate
with the reproduction command in `README.md`, or the study script used here).
The two candidate next directions that would be *ontological* rather than
parameter-hunting: (1) ask why the reconnection of background flux to the
Observer's past is so weak (is it a property of the antichain rule, or of the
local-walk radius being a poor model of "causal neighborhood"?), and (2)
question whether cumulative causal-cone size is even the right observable, vs.
some measure that does not have the worldline's own slope-1 chain baked into
its floor.
