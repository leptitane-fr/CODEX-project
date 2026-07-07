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

## Status

The generator is implemented and tested (`tests/test_graph_generators.py`):
correctness of the antichain/transitive-reduction rule (checked
independently via `nx.has_path`, same method as the synchronous generator),
the worldline's chain structure, monotonicity of the growth curve, and the
`max_nodes` safety cap. **This note documents that the architecture works and
produces a non-trivial, measurable growth curve — it is not yet a
statistical study of the resulting exponent.** A single demonstration run
(`k=3`, `background_ratio=40`, `walk_hops=8`, `n_ticks_observer=200`) gives a
single-run exponent estimate around 1.4, but this has not been repeated
across seeds or `k` values, and per the project's own discipline that number
should not be read as anything more than "the mechanism produces a curve",
until a proper multi-seed study (matching the rigor of
`math/tei_shadow_rule_analysis.md`) is run.
