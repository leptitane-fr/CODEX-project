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

## Changing the observable: transverse width instead of cumulative cone

Direction (2) above was pursued next, on the **unchanged** generator (no new
generative parameter). The cumulative cone conflates two things: the timelike
"memory" direction (the worldline chain, slope 1 by construction) and the
transverse "spatial" direction. The standard causal-set way to isolate the
spatial direction, with no embedding, is the width/height split of an
Alexandrov interval `I[x,y] = {z : x <= z <= y}`:

- **height** = longest chain in the interval = proper time; here it is exactly
  `t` for `I[worldline[0], worldline[t]]`, since the worldline is the longest
  chain.
- **width** = maximum antichain (largest set of mutually spacelike events).
  For a faithfully `d`-embeddable interval, width ~ height^(d-1), so the
  width-vs-`t` exponent estimates the emergent *spatial* dimension `d-1`
  directly. The worldline chain is the height, not the width, so its slope-1
  contribution is removed from this measure by construction.

Implemented as `max_antichain_size` / `causal_interval` / `interval_width` in
`sim/graph_generators.py`.

### A rejected proxy (methodological note)

The width was first proxied by the largest longest-path-depth level set (each
level is a provable antichain, and it is cheap). Validated against the exact
maximum antichain (Dilworth: `n - max bipartite matching on the reachability
relation`), **the proxy underestimates the true width by 3-7x, and the error
grows with interval size** (ratio 0.67 at ~100 nodes down to 0.14 at ~580
nodes). A maximum antichain is not in general a single graded level -- it
pulls mutually-incomparable events from many longest-path depths. The proxy
was discarded; all numbers below use the exact computation. (This is exactly
why the level-set "saturation" seen in a first pass was an artifact, not a
real ceiling: the true width keeps growing.)

### Raw results — exact interval width vs proper time (30 seeds)

Fixed `warmup_events=3000, walk_hops=8, background_ratio=50`; mean exact width
of `I[worldline[0], worldline[t]]` over 30 seeds:

| k | t=100 | t=150 | t=200 | t=300 | t=400 | t=600 | t=800 |
|---|---|---|---|---|---|---|---|
| 2 | 1.7 | 2.7 | 4.9 | 9.7 | 18.1 | 39.7 | 68.7 |
| 3 | 16.9 | 39.2 | 71.2 | 149.7 | 240.2 | 441.8 | 646.4 |
| 4 | 45.2 | 75.3 | 101.1 | 146.8 | 186.9 | 254.8 | 300.9 |

Width-vs-`t` log-log exponent (= d-1 estimate), mean +- std over 30 seeds:

| k | full [100-800] | early [100-300] | late [300-800] |
|---|---|---|---|
| 2 | 1.779 +- 0.554 | 1.588 +- 0.627 | 1.865 +- 0.743 |
| 3 | 1.770 +- 0.128 | 2.027 +- 0.239 | 1.495 +- 0.098 |
| 4 | 0.718 +- 0.467 | 0.939 +- 0.507 | 0.501 +- 0.462 |

### The decisive test — is the width exponent background_ratio-invariant?

This is the test the cumulative cone failed (its exponent slid 1.37 -> 1.19
as `background_ratio` rose 50 -> 300). k=3, 12 seeds, exponent over [100-400]:

| background_ratio | width exponent (d-1) | mean width @[100,200,400] |
|---|---|---|
| 50  | 1.866 +- 0.148 | 19, 75, 243 |
| 150 | 1.840 +- 0.134 | 38, 152, 487 |
| 400 | 1.824 +- 0.142 | 77, 305, 945 |

**The exponent is invariant** (it moves 2% across an 8x change in the knob,
well inside the error bars), while the *amplitude* scales roughly linearly
with `background_ratio`. The knob sets how much flux there is (the prefactor),
not the scaling (the exponent). This is a genuine, qualitative improvement
over the cone: swapping the observable removed the parameter pathology exactly
as the theory predicted it should.

### Reading of the width results — one criterion fixed, two still failing

Recall the three criteria a real emergent dimension must meet: the exponent
must be (a) stable in proper time, (b) independent of `k`, (c) independent of
the simulation knobs. Scoring the width observable:

- **(c) knob-independence: now PASSED.** The background_ratio pathology that
  killed the cone is gone. This also corrects an earlier interpretation: the
  cone's ~1.5 was read as "a brownian tube around a 1D wire, spatial dimension
  ~0.5." That was an artifact of the cumulative measure. The *transverse*
  width actually grows as ~t^1.8 for k=2,3 -- far richer than brownian
  (t^0.5). The observable choice changed the qualitative conclusion, which is
  itself the lesson.
- **(b) k-independence: still FAILS.** k=2 and k=3 sit near d-1 ~ 1.8 but k=4
  is much lower (~0.7), and the early-window values (1.59, 2.03, 0.94) plainly
  disagree. A dimension cannot depend on the arbitrary antichain-size `k`.
- **(a) stability: still FAILS for k=3, 4.** Both drift downward with proper
  time (k=3: 2.03 -> 1.50; k=4: 0.94 -> 0.50). Only k=2 is arguably stable,
  but with error bars too large (+-0.6) to claim anything.

**On the k=3 early-window value of d-1 ~ 2.03 (i.e. d ~ 3.0):** this is
exactly the seductive near-hit the project's discipline exists to neutralize.
It is disqualified three ways over, and must not be promoted: it is the
*early* window only (drifts down to 1.50 by late `t`), it is `k`-specific
(k=2 and k=4 give nothing near it), and a drifting, k-dependent number is not
a measured dimension no matter how close to 3 it lands in one window. It is
recorded here precisely so it is on the table and defused, not buried and not
celebrated.

### Verdict on axis 2

Changing the observable from cumulative cone to transverse interval width was
the right move and it did real work: it removed the `background_ratio`
pathology, and it revealed that the transverse structure is substantially
richer (~t^1.8) than the cone's brownian-looking ~t^1.5 suggested. But it did
**not**, on its own, produce a stable, k-independent emergent dimension: the
width exponent still depends on `k` and still drifts with proper time for
k=3,4. So the observable was necessary but not sufficient. This is the clean
setup for the second ontological axis (a local, charge-biased routing of the
flux -- "attraction/curvature" -- with the bias strength fixed by the
existing delay law rather than a new free knob), which is now worth testing
*because* we finally have an observable whose exponent is not an artifact of a
simulation parameter. Whether attraction stabilizes the exponent and removes
the k-dependence is the open question; it has not been implemented or tested.

## Diagnosing the drift and k-dependence (before adding any new mechanism)

Rather than immediately reaching for attraction, the drift and k-dependence
were diagnosed on the unchanged generator. Two experiments (8 seeds each,
`n_ticks=2000`, `warmup=3000`, `walk_hops=8`, `background_ratio=50`):

**(1) Is the drift a finite-run boundary artifact?** The earlier width study
used `n_ticks=800` and measured up to `t=800`, so `worldline[800]` was the
last node and the top of the interval `I[wl[0], wl[t]]` was squeezed by the
end of the run. Re-running with `n_ticks=2000` but measuring only to `t=800`
(large headroom) gives, for the cone-from-origin width exponent:

| k | early [100-300] | late [300-800] |
|---|---|---|
| 2 | 1.909 +- 0.627 | 1.897 +- 0.540 |
| 3 | 1.955 +- 0.182 | 1.507 +- 0.047 |
| 4 | 1.220 +- 0.236 | 0.697 +- 0.397 |

For k=2 the early/late values now agree (~1.9) -- part of its earlier
wobble was the boundary. But for **k=3 and k=4 the drift persists** with full
headroom (1.96 -> 1.51; 1.22 -> 0.70). So the k=3,4 drift is *not* a boundary
artifact; it is intrinsic to the dynamics.

**(2) Is the transverse structure stationary along the worldline?** Slide a
*fixed-height* interval `I[wl[a], wl[a+400]]` (height always 400) along the
worldline and measure its width vs the anchor age `a`:

| k | a=100 | a=300 | a=500 | a=800 | a=1200 |
|---|---|---|---|---|---|
| 2 | 5.5 | 2.2 | 1.6 | 1.2 | 1.0 |
| 3 | 75.4 | 24.4 | 13.2 | 5.2 | 3.9 |
| 4 | 114.0 | 39.5 | 17.0 | 6.0 | 2.9 |

This is the decisive diagnostic. The transverse width of a fixed-duration
worldline segment **collapses as the Observer ages**, monotonically, for every
`k`, heading toward the bare-chain floor of 1 (roughly a power law, ~a^-0.7
for k=2 up to ~a^-1.5 for k=4, read off the means above). The process has **no
steady state**: the Observer progressively *decouples* from the background
flux. Mechanically this is the transience already suspected in the design
phase, now measured -- the worldline self-continues into its own freshly
created frontier, while the background heap fires across an ever-larger graph,
so the fraction of background events landing near the Observer's current self
shrinks with age. The tube around the worldline thins to a wire.

**What this explains.** Both puzzles dissolve into this one fact:

- The *drift* of the cone-from-origin exponent (k=3,4) is the integral of a
  decaying transverse profile: `I[wl[0], wl[t]]` piles up more and more of the
  thin, old, decoupled worldline as `t` grows, so the width grows sublinearly
  in the added length and the fitted exponent falls.
- The *k-dependence* is that `k` sets the *initial* tube thickness (k=4 starts
  at 114, k=2 at 5.5) and the *decay rate* -- not an asymptotic dimension. All
  three `k` values are heading to the same floor (width 1). So there is no
  k-indexed family of stable dimensions; there is one behaviour (collapse) at
  different starting thicknesses.

**The real verdict on the event-driven generator, sharpened.** The emergent
*asymptotic* spatial dimension is not merely "unstable" or "k-dependent" -- it
is **zero**: the Observer's transverse extent decays to a bare 1D worldline as
it ages. The rich early-time width (~t^2 for k=3, the seductive d~3 near-hit)
is a *transient of birth*, not a dimension: it is the thick coupling the
Observer has while still embedded in the warmed-up region it was born into,
and it washes out as the Observer escapes into its own future.

**What this tells axis 1 to do (a sharpened target, not a solution).** The
missing ingredient is not "more branching" -- the early-time branching is
already ~t^2. It is *persistence of transverse coupling against age*: something
must keep pulling background flux into the Observer's neighbourhood as it moves
forward, so the sliding-window width in experiment (2) becomes **stationary**
(flat vs `a`) instead of collapsing. That is exactly what a charge-biased,
attractive routing of the flux is meant to do -- make the worldline a
persistent attractor (a "massive" filament, in the TEI reading) that the
surrounding flux keeps re-coupling to instead of draining away from. The
diagnostic thus gives axis 1 a concrete, falsifiable success criterion defined
*before* it is built: **a flat `W_L(a)` vs age**, not any particular exponent
value. If attraction cannot flatten that curve, it has not produced a space,
whatever exponent it prints -- and if it can, the exponent it then yields is
worth measuring. This keeps the next step honest: the target is stationarity,
fixed in advance, not a number near 3. (Precisely: stationary at a
*nontrivial* width. `W_L(a) = 1` for all `a` is also "flat", but it is the
degenerate fixed point -- a bare wire, no space at all -- and does not count.)

## Axis 1 tested: refractive routing FAILS by hub condensation

The mechanism (`charge_biased_routing=True` in
`generate_event_driven_shadow_graph`): every step of the local random walk --
background events and the Observer's co-parent picks alike -- lands on a
neighbor with probability proportional to `1 + charge[neighbor]`, i.e.
**exactly the delay law**, no new coupling parameter. Flux is drawn toward
dense/slow regions: the routing component of TEI 7.7's "refraction in the
flux". Structural invariants (acyclicity, antichain rule, worldline chain) are
test-covered under both routing laws.

### Raw results — sliding-window width, blind vs refractive (same protocol)

`W_L(a)` = exact max-antichain width of the fixed-height interval
`I[wl[a], wl[a+400]]`; 8 seeds, `n_ticks=2000`, `warmup=3000`, `walk_hops=8`,
`background_ratio=50`:

| k | routing | a=100 | a=300 | a=500 | a=800 | a=1200 |
|---|---|---|---|---|---|---|
| 2 | blind      | 5.5 | 2.2 | 1.6 | 1.2 | 1.0 |
| 2 | refractive | 1.5 | 1.1 | 1.0 | 1.0 | 1.0 |
| 3 | blind      | 75.4 | 24.4 | 13.2 | 5.2 | 3.9 |
| 3 | refractive | 1.5 | 1.0 | 1.0 | 1.0 | 1.0 |
| 4 | blind      | 114.0 | 39.5 | 17.0 | 6.0 | 2.9 |
| 4 | refractive | 5.4 | 1.4 | 1.1 | 1.0 | 1.0 |

The pre-registered criterion is failed in the strongest possible way: the
refractive width does not flatten at a nontrivial value -- it crashes to the
bare-chain floor of 1 essentially *immediately*, for every `k`. Attraction did
not slow the Observer's decoupling; it accelerated it to completion.

### The failure mode is the predicted condensation — measured

| k=3, same protocol | max out-degree (charge) | top-10 nodes' edge share |
|---|---|---|
| blind      | 26 | 0.15% |
| refractive | 1,114 +- 287 | 2.8% |

Under blind routing no node ever accumulates charge beyond ~26. Under
refractive routing a population of hubs with charge in the hundreds-to-
thousands forms (a 40x jump in max charge): preferential attachment in its
classic rich-get-richer form, distributed over many hubs rather than one
monopoly. This is the "condensation galopante" failure mode named *before*
the experiment -- with one refinement: the flux is captured not by a single
black-hole node but by a hub *class*, and the entity starved is the Observer.

### Why the Observer specifically starves — the identity/charge mismatch

The mechanism is clean and worth recording, because it is a genuine
ontological finding, not a tuning accident:

- Charge (the "mass" that attracts flux) is a **per-node** property.
- The Observer's identity is a **moving node**: at every tick it abandons its
  current self (with whatever little charge it had, ~k) and continues as a
  freshly created child with charge ~0.

So the worldline *leaves its mass behind at every step of self-continuation*.
Under attractive routing, flux goes where the mass is -- into the old
background hubs -- and the perpetually newborn Observer is the *least*
attractive thing in the universe. Implemented gravity therefore empties the
Observer's surroundings instead of filling them. As modeled, the worldline is
a **massless** particle, and refraction bends flux away from massless
particles' neighbourhoods, exactly as measured.

This exposes a real tension between the implementation and the ontology it
claims to implement. TEI 6ter.3-D defines matter as a closed loop that
re-executes "sur place" -- localized *because* it keeps re-executing in the
same place. Our worldline never re-executes in place: it is a bare chain that
always moves on. It is, in TEI's own classification, a *photon-like open
motif*, not a matter-like closed one -- and the experiment just demonstrated,
mechanically, that an open motif cannot gravitationally bind space to itself.
For attraction to work *for the Observer*, mass would have to be carried by
the recurring pattern (a closed loop over a persistent neighbourhood) rather
than left behind on each dead self.

### Verdict on axis 1 as implemented

Negative, by the pre-registered criterion, with the failure mode being the one
predicted in advance (condensation) plus a sharp diagnosis of *why* it starves
the Observer specifically (identity/charge mismatch). Recorded per the
project's discipline: the mechanism was ontologically motivated (bias law =
delay law, no free knob), the test was fixed before the run, and it failed
cleanly. Do **not** attempt to rescue it by adding a tunable bias exponent, a
charge cap, or hub suppression -- every one of those is a new free knob whose
only purpose would be to steer the outcome (the TEI-3.x failure mode).

The honest open direction this leaves (not implemented, not tested): make the
Observer an actual closed motif in the sense of 6ter.3-D -- a loop that
re-executes over a persistent set of nodes, accumulating charge *as a
pattern* -- and ask whether such a bound structure, under the same refractive
routing, retains a nontrivial stationary width where the open chain could
not. That is an ontological redesign of what "the Observer" is, not a
parameter fix, and it is exactly the distinction (open motif = light, closed
motif = matter) that the theory itself insists on.

## v0.7 — the braided closed motif: matter persists, but still casts no halo

That redesign has now been built (`generate_braided_motif_graph`) and run
through a pre-registered A/B study. Architecture in brief (full details in
the generator's docstring): the Observer is a worldtube of generations, each
an antichain of `motif_width` (W) nodes; each new node takes 2 distinct
internal parents from the previous generation (the braid -- the minimum
closure, since one internal parent un-braids the tube into W photon chains)
plus `k-2` capture attempts from the background flux under the usual
independence check. Entropy is the generational rotation itself. Structural
prediction recorded before measurement: **k=2 cannot make matter** (braiding
consumes both slots -- a sealed crystal with no metabolism; test-covered).
W is the motif's mass, swept over {2, 4, 8}, never tuned.

The pre-registered criterion (fixed above, before the run): the gravity
signal is the **halo** -- the sliding-window width in excess of the identical
motif under blind routing. The tube's own built-in width proves nothing,
since we constructed it.

### Raw results (k=3, 5 seeds, n_generations=1600, anchors 100-1200, L=200)

`W_L(a)` = exact max-antichain width of `I[gen_a[0], gen_{a+200}[0]]`:

| W | routing | a=100 | a=300 | a=600 | a=1000 | a=1200 | capture | max charge |
|---|---|---|---|---|---|---|---|---|
| 2 | blind      | 16.0 | 5.8 | 2.4 | 2.8 | 2.4 | 100% | 26 |
| 2 | refractive | 2.2 | 2.0 | 2.0 | 2.0 | 2.0 | 99% | 897 |
| 4 | blind      | 27.4 | 8.6 | 7.2 | 7.0 | 6.8 | 100% | 24 |
| 4 | refractive | 4.8 | 6.4 | 5.8 | 5.8 | 5.8 | 99% | 608 |
| 8 | blind      | 25.4 | 10.8 | 13.6 | 12.8 | 12.8 | 100% | 25 |
| 8 | refractive | 10.2 | 12.8 | 12.0 | 12.8 | 12.4 | 99% | 700 |

### Reading — one genuine breakthrough, one clean failure

**The breakthrough: closure cures the evaporation.** For the first time in
this project, a structure holds a *stationary, nontrivial* transverse width
indefinitely: under both routings, every W settles onto a flat plateau
(~2, ~6-7, ~12-13 -- roughly 1.6W) instead of collapsing to the bare-chain
floor of 1 as the open worldline did. The "mort thermique" diagnosed for the
photon-like chain is cured by closure alone: a braided, metabolizing motif
does not evaporate. Matter, in the 6ter.3-D sense, now exists and persists in
this toy model -- with a working metabolism (99-100% of capture slots filled
at every age, under both routings). Note this plateau is the *body* (tube
cross-section plus the motif's own recycled flux), which the criterion
deliberately does not count as a gravity signal.

**The failure: the halo is zero-to-negative at every mass.** At late ages the
refractive width sits at or slightly below the blind width (2.0 vs 2.4;
5.8 vs 6.8; 12.4 vs 12.8). Attraction adds nothing around the body -- if
anything the refractive runs hold slightly *less* recycled flux than the
blind ones, and the early-age birth halo (16-27 blind) is destroyed rather
than retained (2-10 refractive). Meanwhile the background hub condensation
persists unchanged (max charge ~600-900 vs ~25 blind). By the pre-registered
criterion: **failure**. Refraction still does not make matter hold space, at
any of the three masses tested; there is no sign of a critical-mass threshold
within {2, 4, 8}.

### Why — the identity/charge mismatch, one level up

The v0.6 failure was: per-node charge + moving identity = the chain abandons
its mass at every step. The motif fixes identity (it persists), but rotation
now caps *residency*: a membrane member serves as a parent for exactly one
generation (~2-3 charge units) before the motif stops re-executing over it.
So the motif's mass is large *in aggregate* (W new edges per generation,
forever) but tiny *per node* -- and the refractive walk weighs **per-node**
charge. Against background hubs at charge 600-900, a membrane at charge 3 is
invisible. The collective mass of a rotating dissipative structure is
unsensed by a per-node-weighted walk: this is the same mismatch as v0.6,
displaced from "identity moves" to "membership rotates". It appears to be a
genuine structural tension between entropy (rotation, which the dissipative
ontology demands) and attractivity (per-node charge accumulation, which
per-node-weighted refraction demands).

### Status and the honest fork ahead

Recorded per discipline: the closed-motif architecture achieves something
real and new (persistent matter with stationary nontrivial extent -- the
first stationary structure this project has produced), and cleanly fails the
gravity criterion it was built to test. Two directions remain that are
questions of physics rather than knob-turning, neither implemented:

1. **Critical mass as a sign question**: does the halo (refractive minus
   blind) turn *positive* at some W (16, 32, ...)? This is a qualitative
   sign-flip question, not an exponent target, so sweeping W further is
   legitimate -- but the per-node-charge argument above predicts it will not
   flip, since membrane charge per node is independent of W.
2. **What carries mass**: the deeper question the mismatch poses is whether
   the quantity the walk senses should be per-node charge at all, or
   something a membrane can actually accumulate (e.g. flux *through* a
   neighbourhood rather than degree *of* a node). Any such change must be
   derived from the delay law / ontology first and tested against the same
   halo criterion -- introduced as a free weighting function, it would be
   the TEI-3.x failure mode in a new costume.

## The consumption law: the belt forms, the halo still does not

The skimming exception was then removed (commit "Enforce the conservation
law on capture"): capture now invalidates the prey's pending event and
reschedules it after a charge-grown delay -- the exact treatment every
background event already applies to its own parents (TEI 7.7: an instruction
is conserved *until interpretation*; interpretation spends it). No new
parameter. The A/B halo study was rerun identically, with three
pre-registered monitors: belt charge (anchors = non-membrane parents of
membrane nodes), capture rate early vs late (choking monitor), background
condensation (screening monitor).

### Raw results (k=3, 5 seeds, 1600 generations, anchors 100-1200, L=200)

| W | routing | W_L: 100 | 300 | 600 | 1000 | 1200 | capture e/l | belt charge mean / max | max charge |
|---|---|---|---|---|---|---|---|---|---|
| 2 | blind      | 14.6 | 4.4 | 3.6 | 2.4 | 2.4 | 99% / 80% | 4.3 / 18 | 25 |
| 2 | refractive | 2.0 | 2.4 | 2.0 | 2.0 | 2.0 | 99% / 98% | 8.7 / 467 | 811 |
| 4 | blind      | 16.6 | 8.2 | 6.8 | 6.4 | 6.4 | 100% / 100% | 4.5 / 20 | 24 |
| 4 | refractive | 5.4 | 6.0 | 4.6 | 5.4 | 5.4 | 99% / 99% | 9.0 / 470 | 611 |
| 8 | blind      | 18.4 | 13.2 | 13.4 | 13.6 | 12.8 | 100% / 100% | 8.2 / 23 | 25 |
| 8 | refractive | 12.2 | 12.8 | 10.8 | 13.0 | 12.8 | 99% / 98% | 41.2 / 459 | 795 |

### Reading

**The halo verdict is unchanged: zero-to-negative at every mass.** Late-age
refractive minus blind: -0.4 (W=2), -1.0 (W=4), ~-0.2 (W=8). By the
pre-registered criterion, the consumption law alone does not produce the
gravitational halo.

**But the radial mechanism it was built to create did appear.** Under
refraction the belt is now heavily charged: anchor charge mean 9-41 (up to
5x the blind belt) and belt maxima ~460-470, approaching hub class -- where
blind belts stay at 4-8 mean, max ~20. The "causal accretion belt" (slow,
charged vacuum around the membrane -- Canal 1 of TEI 7.7, local time
dilation near mass) exists, mechanically sourced, exactly as designed. No
choking either: capture holds at 98-100% to the end (mild 80% only for W=2
blind). The realized failure mode is **screening** -- and a targeted
verification pinned down its precise structure:

- Under **blind** routing, 38% of belt anchors are *descendants of the
  motif's own earlier generations* (recycled emissions), and the membrane
  has ~2000 accidental emission edges (background events that happened to
  pick membrane members as co-parents).
- Under **refraction**, emission edges are comparable (~1700), but only
  **1%** of belt anchors descend from the motif. The refractive walk climbs
  charge gradients, and the motif's own emitted flux is young and light --
  so refraction systematically diverts capture away from the motif's own
  wake, toward heavy causal strangers.

This matters because of what the Alexandrov interval actually counts: nodes
that are both descendants of the earlier endpoint *and* ancestors of the
later one -- i.e. **flux that was emitted by the motif and then re-absorbed
by it**. The out-and-back loop. Blind routing closes that loop accidentally
38% of the time; refraction almost never does. That is, mechanically, why
refractive plateaus sit slightly *below* blind ones in both studies.

### The two-channel reading (the theory predicted this failure shape)

TEI 7.8 insists gravity needs two channels: Canal 1, retard de cadence
(time dilation), and Canal 2, *espace secrete* -- the mass "expels flux
continuously; that flux, as long as it is not executed, traces" geometry.
A theory with only the time channel famously yields no (or half) spatial
deflection -- the scalar trap. What we have now built is exactly Canal 1
alone: consumption creates the slow, charged belt (time dilation:
mechanically real, measured), but the motif is a **pure absorber**. Every
edge points into the membrane; nothing structural points out. Its interval
therefore contains nothing but its own tube plus whatever emission happens
by accident -- and refraction suppresses precisely that accident. The width
probe is correctly reporting that **no space is being secreted, because the
motif never emits**.

Implementation fact that makes this concrete: membrane nodes are the *only*
nodes in the entire universe exempt from the event heap (background nodes
are all scheduled at birth; membrane nodes never are). The exemption was
inherited from the v0.6 worldline for control reasons. Meanwhile TEI 6bis.2
says a mass is a subgraph in permanent restructuring that expels
instructions *at every reorganization* -- our motif reorganizes every
generation and expels nothing. The ontology demands radiation; the
implementation forbids it.

### Status and next step (not implemented)

Consumption is kept: it is a conservation law, it works (the belt is real),
and it is one of the two channels. The honest next step is the other
channel, and it is once again the removal of a special exemption rather
than a new force: **retired generations re-enter the flux** (membrane
members are scheduled on the event heap when their generation rotates out
-- the motif's wake radiates, per 6bis.2). Expected mechanism: the wake is
dense, near the membrane, and *descends from it*; with consumption charging
whatever gets captured, the motif's own re-absorbable emissions finally
become the heaviest things in its neighbourhood, letting the refractive
walk close the emit-capture loop that the interval width measures. Success
criterion unchanged (halo A/B). Failure modes to name at design time; the
obvious one is runaway self-interaction (the motif capturing only its own
wake and decoupling from the universe -- a solipsist bubble).

## Structural radiation: the wake exists, refraction still ignores it

The last exemption was removed (commit "Structural radiation"): on rotation,
retired generations re-enter the event heap (generation bump + reschedule at
`background_time + delay(charge)` -- the same operation as capture
consumption, so a single instruction never fires twice). Entropy and
emission become the same event, per TEI 6bis.2. The A/B study was rerun
identically, now with the solipsist monitor (own-wake fraction of belt
anchors, i.e. anchors descending from `gens[50][0]`; pre-radiation baseline
was 38% blind / 1% refractive).

### Raw results (k=3, 5 seeds, 1600 generations, anchors 100-1200, L=200)

| W | routing | W_L: 100 | 300 | 600 | 1000 | 1200 | capture e/l | belt mean/max | own-wake | max charge |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | blind      | 14.8 | 4.8 | 3.0 | 2.4 | 2.2 | 100%/100% | 4.3 / 20 | **59%** | 28 |
| 2 | refractive | 2.4 | 2.0 | 2.0 | 2.0 | 2.0 | 99%/79% | 9.5 / 434 | **5%** | 826 |
| 4 | blind      | 20.0 | 5.6 | 6.0 | 4.4 | 6.0 | 100%/100% | 4.5 / 22 | **49%** | 24 |
| 4 | refractive | 6.2 | 5.4 | 5.8 | 5.8 | 5.6 | 99%/99% | 9.0 / 494 | **7%** | 559 |
| 8 | blind      | 15.2 | 13.6 | 12.8 | 10.2 | 12.8 | 100%/100% | 8.1 / 21 | 9% | 25 |
| 8 | refractive | 13.0 | 12.4 | 12.4 | 12.6 | 12.4 | 99%/99% | 37.5 / 535 | **0%** | 657 |

### Reading

**Halo verdict: negative for the third time.** Late-age refractive minus
blind is ~-0.3 (W=2), ~-0.4 (W=4), ~-0.4 (W=8). Same magnitude as both
previous studies.

**Radiation itself works as designed.** Under blind routing the own-wake
fraction of belt anchors jumps from the pre-radiation 38% to 49-59% (W=2,4):
the motif's emitted wake is real, present in its neighbourhood, and gets
re-captured when the walk is unbiased. The emit-and-reabsorb loop that the
interval width counts is now closing half the time -- under *blind* routing.

**But refraction still refuses to close it: own-wake 0-7%.** The radiated
wake is young and light (charge ~3-4 at birth); the incumbent hub class
(charge 434-826, seeded during warmup and compounding ever since) wins every
weighted step. This is a first-mover monopoly: charge advantage under
`p ~ 1+charge` routing compounds multiplicatively, so no newly emitted
population can ever catch up with the incumbents, no matter how well-placed
it is. Radiation put the right flux in the right place; the routing law
still sends gravity's pull toward the oldest strangers in the universe.

**And a sharper structural observation, visible only now:** even under blind
routing, where the loop closes 49-59% of the time, the late-age width
plateau did not budge (still ~2.2 / ~6 / ~12.8 -- the same ~1.6W as with no
radiation and no consumption). Recycling *fraction* rose; width did not.
This suggests (interpretation, flagged as such) a **throughput bound**: the
interval between two generations can only be populated by flux that
actually makes an out-and-back trip, and the motif's emission/capture
throughput is constant per generation (~O(W) excursions, each short-lived).
Constant concurrency of excursions = constant cross-section = width pinned
at ~1.6W regardless of interval height. If this reading is right, no
routing law whatsoever can make a *single* motif's self-halo grow with
proper time: one body's atmosphere is rate-limited by that body's own
constant metabolism. In a sprinkled causal set the diamond fills up because
the vacuum's causal relations all exist geometrically; here, relations
exist only where edges were actually created, and one body can only create
O(W) of them per tick.

### Where this leaves the gravity question

Three ontologically-motivated mechanisms are now in place and validated at
the mechanism level (closure -> persistence; consumption -> the charged slow
belt, Canal 1; radiation -> a real, re-capturable wake), and the
pre-registered halo criterion has failed three times, each time for a
different, precisely identified reason (no mass retention; pure absorber;
incumbent monopoly + throughput bound). The pattern of the three failures
points away from "one more mechanism" and toward the possibility that the
*question* -- a single body dressing itself in space -- is the wrong probe.
TEI's own text says as much: 6bis.4 defines the medium as the saturated flux
of *all* bodies ("le tissu, c'est le flux lui-meme", every body radiating),
and poses as its central open support question how a stable *Earth-Mars*
relation is maintained across perishable flux -- a **two-body** question.
The natural next probe, not implemented here: two motifs, and the interval
*between* them -- does the inter-body space (width of I[member of motif A,
member of motif B]) behave differently from the self-halo that has now
failed three times? That is a change of observable (like the cone -> width
move, which paid off), not a new mechanism, and it is the question the
theory itself asks.

## The two-body probe: attraction exists between bodies; still no channel

The pivot recorded above was implemented (`generate_two_motif_graph`,
`first_contact_lag`): two closed motifs born as localized clusters at a
controlled undirected-hop separation, advancing concurrently, all previous
laws active (braiding, consumption, radiation), cross-couplings counted by
direction and timed (`first_living_gen`, `first_wake_gen`).

### Scale calibration (before fixing criteria)

The physical requirement was stated in advance: separation must exceed the
interaction range (`walk_hops`), else there are no "two bodies". Measured:

- `walk_hops >= 8`: the warmup universe is one causal room (leaf-to-leaf
  diameter ~6 < range) -- the two motifs merge from birth (contact_living
  ~1300). No two-body regime exists.
- `walk_hops = 2`: the universe becomes *extended* (diameter ~28) -- the
  interaction range shapes the universe's own geometry -- but the metabolism
  chokes (capture ~0%: everything within 2 hops of a membrane is the motif
  itself or its ancestors, all antichain-rejected; the capturable wake lives
  at ~3 hops).
- `walk_hops = 3`: the window. Metabolism healthy (capture 63-82%), genuine
  separation available (D up to ~8 at warmup=20000), zero body contact at
  birth for D=6.

A structural tension worth recording on its own: **the range that permits
geometry starves matter, and the range that feeds matter dissolves
geometry** -- except in a narrow window (here, exactly hops=3).

Also discovered: a seed's *refractive* warmup universe can have a smaller
diameter than its blind counterpart (refraction makes the small world
smaller), so equal nominal separations are not always available in both
arms; the study steps down per seed and reports realized separations.

### Raw results (k=3, W=4, warmup=20000, hops=3, 1200 generations, 5 seeds)

Per seed: total cross-wake captures by direction (@ = generation of first),
living-membrane contacts (@ = first), lag A->B at anchors 100/800, channel
width I[A_a, B_{a+300}] at anchors {100,400,800}:

D=6, blind: **all five seeds totally silent** (no coupling, no contact, no
channel, lag = None everywhere).

D=6, refractive: seeds 2,3,5 silent; seed 1: wakeB=9@5 (small sustained
one-way coupling, no contact, no channel); seed 4: wake@29 -> living@95 ->
full merger (3085+3484 wake captures, 1427 living, channel ~10 post-merger).

D=7, blind: seeds 1,2,5 silent; seeds 3,4: **born touching** (living@1,
wake@0-1) -> immediate merger (~2770 wake each way, ~2950 living,
channel ~10).

D=7, refractive: seed 2 (fallback sep=6) silent; seed 1: wakeB=106@50,
sustained 1150 generations, never touching (living=0), no channel; seed 5:
wakeB=4@27, no contact; seeds 3,4: wake@11-15 -> living@60-124 -> merger
(~3200+3100 wake, ~1450 living, channel ~10).

### Reading

**First reproducible positive refractive differential of the project.**
Across all runs where the bodies were not born touching: cross-body coupling
occurred in **5 of 10 refractive runs and 0 of 10 blind runs**. Under blind
routing, two separated bodies ignore each other forever (1200 generations of
mutual silence, every seed). Under refraction -- and only under refraction --
they find each other. Whatever its limits below, this is the first time in
five studies that the gravity law produced *more* structure than blind
chance, and it did so on the observable the theory itself designates (the
relation between two masses), not on the self-halo where it failed three
times.

**The timing resolves an infall dynamic.** Blind mergers exist only when the
election placed the bodies in contact at birth (living@1). Refractive
mergers are *processes*: wake coupling first (generation ~11-29), living
contact only 45-110 generations later, then fusion. Two masses that sense
each other's wake, approach, and collide. The model has infall; it has no
orbits (nothing supplies angular momentum) and no static hovering -- so
contact, once made, always completes into merger.

**The pre-registered channel criterion is NOT met.** No run shows a
stationary inter-body channel at a distance: channel width is nonzero only
after merger (where ~10 is just the fused pair's own tube width, not space
between bodies). The outcome is bimodal -- total silence or eventual fusion.
Notably, in the sustained-coupling-without-contact runs (D=7 seed 1: 106
captures over 1150 generations) the lag A->B stayed infinite at anchors 100+
even though B demonstrably captured A's wake: the coupling reaches only the
partner's *fossil past* (generations before the anchors), never its present
-- an asymmetric, backward-looking touch that never becomes a forward
channel. (Hypothesis, not verified: as the universe grows, the two tubes'
active regions recede from each other, so only old strata remain mutually
reachable -- an expansion-like recession. Instrumenting *which* generations
get captured would test this.)

**Verdict.** The two-body probe delivered the first genuine gravitational
signature of the framework (refraction-only mutual discovery, timed infall,
merger) and simultaneously showed that at the accessible universe scale
(separations ~2x the interaction range, diameter ~8) there is no stable
"space between bodies" to measure -- the regime menu is silence, infall, or
fusion. The Earth-Mars question (a *stationary* inter-body relation) remains
open, now with a sharper obstacle: it needs either a universe with genuine
extent (which the current growth rule only produces at metabolism-choking
interaction range 2) or a mechanism that stabilizes approach short of merger
-- and per the project's discipline, neither should be forced by knob
search. What exists now, honestly stated: matter that persists, dilates
time, radiates, attracts other matter under the refraction law, falls
together, and merges. What does not exist: space.

## Metrology: the recession proven, the horizon measured, the infall resolved

Strictly observational instruments were added (no dynamics change):
`id_watermarks` (ids are creation-ordered and edges only point old -> new, so
the subgraph on ids < watermark[g] is exactly the universe as it existed at
tick g -- the past metric is reconstructible, and later shortcuts cannot leak
backward), `intertube_metrics` (instantaneous membrane-to-membrane hop
distance d(g) + near-geodesic corridor volume V(g)), and `wake_gap` (distance
from one body's living membrane to the nearest node of the other's radiated
wake -- the signal-vs-metric race). Data acquired on the v2 runs (same
protocol, same seeds).

### The recession is real, linear, and routing-independent

All four silent runs (blind D=6 seeds 1-3, refractive D=6 seed 2), born 6
hops apart:

| g | 100 | 300 | 600 | 900 | 1200 |
|---|---|---|---|---|---|
| d(g), all four runs | 94-110 | 316-329 | 642-660 | 973-979 | 1298-1305 |

**d(g) = ~1.08 g**: constant-velocity recession at ~1.08 hops per
generation, identical under blind and refractive routing. Mechanically: each
living membrane burrows 1 hop per generation away from its birth cluster
(the tube advance is kinematic), for a naive 2g+6; the growing medium knits
shortcuts that recover ~46% of that; the net is ~1.08g. The corridor volume
V(g) grows linearly too (~7 nodes/generation): the space between the bodies
fills at constant rate while stretching faster. This is not a Hubble law
(v independent of d at these scales); it is constant-speed kinematic
recession, and refraction does nothing to slow it.

### The race: the metric outruns the signal 2:1 -- an event horizon

Refractive D=7 seed 1 (the sustained-coupling-without-contact run), tracking
the gap between B's living membrane and the nearest node of the wake of A's
generation 50:

| dg (generations after 50) | 25 | 50 | 100 | 200 | 400 | 800 | 1100 |
|---|---|---|---|---|---|---|---|
| gap (hops) | 8 | 12 | 39 | 95 | 206 | 423 | 585 |

The wake got within 8 hops of B early (hence the 106 fossil captures around
generation 50), then the gap grew *linearly forever* at ~0.55 hops/gen.
Since B recedes at ~1.08, the wake front advances at ~0.53 hops/gen:
**the metric expands about twice as fast as radiation propagates
(1.08 vs 0.53)**. The requested proof is delivered, with a stronger
corollary: from A's generation 400, the wake is born already 388 hops behind
B and never closes -- every generation emitted after the early window
radiates into a **causal event horizon**. This is exactly why sustained
coupling only ever reached the partner's fossil past: the early wake was the
only wake that ever stood within reach.

### Infall kinematics: not constant acceleration -- a three-phase zipper

d(g) for the three dynamic refractive mergers (dense sampling):

- D=7 seed 3 (wake@15, contact@60): 6, 12 | 11, 8, 9, **3** | ~1-2 fused.
- D=7 seed 4 (wake@11, contact@124): 4, 5, 7, 7, 11 | 10, 8, 7, 5, 6, 4, 4,
  **2** | ~1-2 fused.
- D=6 seed 4 (wake@29, contact@95): 5, 6, 6, 8, 15 | 10, 8, 8, 5, **1** |
  ~1-2 fused.

Three phases, cleanly resolved: (1) **recession** -- the pair initially
separates like any silent run; (2) **turnaround** at the first wake bridge
(the capture edges themselves shorten the metric); (3) **roughly linear
closure** (~0.1-0.3 hops/gen net against an ambient recession of ~1.08, so
the knitting outpulls expansion by ~1.2-1.4 hops/gen) down to contact and
fusion (d pinned at 1-2, the born-touching control's flat profile). The
answer to "is it constant gravitational acceleration?" is **no**: the curve
is not parabolic. Infall here is a *capture cascade* -- each cross-body
capture inserts an edge that contracts the metric directly, producing
constant-velocity closure. Gravity in this model pulls by **topological
knitting**, not by accumulating momentum: a zipper, not a ballistic fall.

### The bimodality, mechanically explained

The silence/merger coin-flip is a race at birth: the first wake bridge must
form while the gap is still within walk reach (first couplings at
generations 11-29 in all three mergers), before recession (~1.08 hops/gen,
starting immediately) carries the partner past the horizon. Win the race
early and the zipper closes; lose it once and the 2:1 expansion-to-signal
ratio guarantees permanent separation. There is no third outcome at this
scale -- which is precisely why no stationary inter-body channel was found:
the model's expansion admits no static equilibrium between bound and lost.

Honest limits: single seeds per kinematic curve (the phases are consistent
across all three mergers, but rates carry seed noise); hop distance is the
only metric available (no embedding); and the recession rate is set by the
tube-advance kinematics of this generator, so its numeric value (1.08) is
architecture-specific even though the horizon phenomenon (expansion vs
signal-speed competition) is structural.

## The orbit test: no angular momentum, because no inertia

The bimodality (silence or radial merger) motivated an "angular momentum"
attempt: a tangential kick injected as a strict initial condition
(`kick_ticks` generations of metabolic asymmetry relative to the partner --
`noinfall` refuses radial-in captures, `iso` keeps only equidistant ones;
dynamical laws untouched, partner never referenced after the burn).
Pre-registered success = a post-burn stationary channel (late coupling,
no merger, flat d(g) band >= 300 generations, inter-tube width > 0). Proper
motion was decomposed into radial (inter-tube d change) and a heuristic
tangential scalar T = sqrt(S^2 - R^2) over a 20-generation window (S = the
membrane's own hop displacement; Euclidean analogy, flagged: T is meaningful
only as "drift not explained by radial change").

Protocol: k=3, W=4, warmup=20000, hops=3, D=7 (per-seed fallback), 5 seeds,
1200 generations. Controls: `kick_ticks=0`/`none` (reproduce the bimodality),
and blind+kick (a channel there would be a burn artifact).

### Raw results

**Control (refractive, no kick)** reproduces the known bimodality exactly:
seeds 3,4 merge (@60, @124), seeds 1,5 couple then recede (fossil), seed 2
silent. Proper-motion decomposition: T is nonzero (5-15) *only* in the merged
seeds and *only* at close range (d = 1-2) -- i.e. it is the wiggle of two
fused membranes sitting on top of each other, not orbital drift. In every
non-merging seed T -> 0 by generation 50-100. **No persistent tangential
drift arises naturally.**

**Every kicked run -- `noinfall` kt=25, `noinfall` kt=50, `iso` kt=25, and
the blind+kick control -- is SILENT (0 couplings, 0 contacts) across all 5
seeds.** Two things happen together:

| config | burn capture | d(g) at g25 | d(g) at g100 | outcome | T (any g) |
|---|---|---|---|---|---|
| control (no kick) | 100% | ~11 | 40-96 (bimodal) | 2 merge, 2 couple, 1 silent | 0 except at merge |
| noinfall kt25 | 4-9% | ~54 | ~137 | 5/5 silent | 0 throughout |
| noinfall kt50 | 2-4% | ~54 | ~159 | 5/5 silent | 0 throughout |
| iso kt25 | 4-8% | ~54 | ~135 | 5/5 silent | 0 throughout |
| blind noinfall kt25 | 9-14% | ~53 | ~133 | 5/5 silent | 0 throughout |

### Reading -- the burn starves, and there is no inertia

**The kick did not inject tangential momentum; it starved the body and let
tube kinematics eject it radially.** The reject-a-distance-class burn drops
capture to 2-9% (vs 100%): during the window the motif is a nearly bare
braided tube taking in almost no flux, and tube-advance kinematics fling the
two bodies to d ~ 54 by generation 25 -- roughly 2 hops/generation of pure
recession, far past coupling range before the burn even ends. By the time
metabolism resumes (~60% after the burn) the partner is gone over the 2:1
horizon. This is failure mode #2 (ejection), reached deterministically for
every mode, every kick length, both routings. Neither delayed merger
(orbital decay) nor a razor's-edge channel appeared -- the kicked bodies
never approach at all.

**Crucially, T = 0 during the burn as well as after it.** The metabolic
asymmetry produced no lateral drift even while active: forbidding radial-in
captures does not push the body sideways along the equidistance shell, it
just removes captures and lets radial recession dominate. The mechanism
fails upstream of the inertia question -- it cannot create tangential motion
in the first place.

**And the inertia question itself, answered by the control, is negative.**
Even in the natural dynamics, no tangential drift persists: T is zero in
every open (non-merged) configuration, and nonzero only as close-range
membrane noise once bodies have fused. The depletion-drag hypothesis --
that a body's motion through the flux would leave a self-avoiding wake
sustaining its drift -- is not supported: this substrate exhibits
*position* persistence (a motif stays a coherent body) but no *velocity*
persistence (no momentum memory). A body moves only while actively pushed,
and the only push available is radial (tube advance + gravitational
knitting). There is no free tangential coordinate that, once set in motion,
keeps moving.

### Verdict

The orbit test fails its pre-registered criterion, by ejection, and adds a
structural reason the Earth-Mars channel was never reachable: **the model
has no angular momentum because it has no inertia.** Classical orbits are
stabilized by conserved angular momentum -- a velocity that persists without
being driven. This substrate conserves *what a body is* (closure) and *where
it is* (its neighbourhood), but not *how it is moving*: there is no dynamical
variable carrying a rate. Combined with the metrology (recession, 2:1
horizon, zipper infall), the two-body sector is now fully characterized and
closed at this scale: the only outcomes are silence (lost over the horizon)
or radial merger (caught by the zipper), with no stable separation between,
because nothing in the rules stores momentum. Per discipline: no knob was
tuned to seek a channel, the starvation confound is stated rather than
engineered around, and the negative inertia result is reported as the
substantive finding. Making orbits would require an ontological addition
that gives the substrate a conserved rate -- not an initial condition, and
not a tuning of the existing laws.
