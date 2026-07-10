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
under it), but the exponent still depends on `k` and still drifts. A
diagnostic pass (same file, no new mechanism) then found the root cause: a
fixed-height interval slid along the worldline has a transverse width that
**collapses as the Observer ages** (e.g. k=3: 75 at age 100 down to 4 at age
1200), heading to the bare-chain floor of 1 for every `k`. The Observer
*decouples* from the background flux with age, so the asymptotic emergent
spatial dimension is effectively **0 (a bare 1D worldline)**; the rich
early-time width (the k=3 d~3 near-hit) is a transient of birth, not a
dimension — documented and defused so it is never re-reported as a result.
The cheap longest-path-depth-level proxy for width was tried and rejected
(underestimates the exact max antichain 3-7x); use the exact
`max_antichain_size`. The diagnostic also fixed a success criterion for any
future attraction/curvature mechanism, *before* building it: a **stationary**
sliding-window width vs age (at a *nontrivial* value — flat at width 1 is the
degenerate bare-wire fixed point and does not count), not a particular
exponent value near 3.

That attraction mechanism has now been built and tested
(`charge_biased_routing=True`: walk steps ∝ 1+charge, the same law as the
delay, no new free knob) and it **failed the pre-registered criterion in the
predicted way**: flux condenses onto background hubs (max charge 26 → ~1100
vs blind routing) and the width crashes to 1 immediately — the worldline
abandons its charge at every self-continuation step, so implemented gravity
drains its neighbourhood instead of filling it (see the identity/charge-
mismatch section of `math/event_driven_shadow_analysis.md`). Do not try to
rescue this with a tunable bias exponent, charge cap, or hub suppression —
each is a free knob whose only role would be steering the outcome (TEI-3.x
failure mode). That redesign has now been built:
`generate_braided_motif_graph` (v0.7) implements the Observer as a closed
motif per TEI 6ter.3-D — a worldtube of W-node antichain generations braided
by 2 internal parents per node, metabolizing via antichain-checked captures,
with entropy as generational rotation (k=2 is structurally sealed: no
capture slots — recorded as a prediction, test-covered). The pre-registered
halo A/B study verdict (same file): **closure cures the evaporation** — the
motif holds a stationary nontrivial width (~1.6·W) forever, the project's
first persistent structure — but the **refractive halo is zero-to-negative
for every W in {2,4,8}**: matter persists and still casts no gravitational
halo. Root cause recorded: rotation caps per-node residency, so the motif's
mass is collective but the refractive walk weighs per-node charge — membrane
members at charge ~3 are invisible next to background hubs at ~600-900. Do
not "fix" this with a free weighting function on the walk; any change to
what the walk senses must be derived from the delay law/ontology first, and
judged by the same halo criterion.

The conservation-law fix was then applied (capture *consumes* its prey:
pending event invalidated, rescheduled with charge-grown delay — TEI 7.7's
"conserved until interpretation", the same treatment background events
already give their parents; removal of a special case, no new knob). Result
(same file): the charged slow accretion belt forms exactly as designed
(anchor charge ~9-41 mean, ~470 max under refraction vs ~5/20 blind — Canal
1, time dilation near mass, mechanically real), capture holds 98-100%
(no choking), **but the halo is still zero-to-negative**. Verified root
cause: the interval width counts emitted-then-reabsorbed flux, and the
motif is a pure absorber — membrane nodes are the only nodes in the
universe exempt from the event heap, so the motif never radiates (violating
TEI 6bis.2, which demands a mass expel instructions at every internal
reorganization); blind routing closed the emit/reabsorb loop by accident
38% of the time, refraction diverts it to heavy strangers (1%). The
recorded next step (not yet implemented): structural radiation — retired
generations re-enter the event heap — judged by the same halo criterion,
with runaway self-interaction (a solipsist bubble capturing only its own
wake) named in advance as the failure mode to watch.

Structural radiation was then implemented (retirement = generation bump +
reschedule, same operation as consumption; no node in the universe is
exempt from the heap anymore) and the halo verdict is **negative for the
third time** (same file). Radiation itself works — under blind routing the
own-wake fraction of belt anchors jumps to 49-59% — but refraction still
sends the walk to the incumbent hub class (own-wake 0-7%): a first-mover
charge monopoly that no newly emitted population can catch under
p ∝ 1+charge routing. Sharper still: even with the loop closing half the
time (blind), the width plateau did not move — flagged as a possible
*throughput bound* (one body's interval can only be populated by its own
constant-rate excursions, so a single motif's self-halo may be structurally
unable to grow). The recorded candidate next probe is a change of
observable, not mechanism: **two motifs, and the width of the interval
between them** (TEI 6bis.4's own Earth-Mars support question). Do not add
routing-law patches (wake boosts, hub caps, age weighting) to force the
third A/B green — that is the TEI-3.x failure mode.

The two-body probe (`generate_two_motif_graph`, `first_contact_lag`) has now
been built and run (same file, last section). Scale calibration first: the
interaction range (`walk_hops`) shapes the universe's own geometry — hops≥8
gives a one-room universe (bodies merge at birth), hops=2 an extended one
(diameter ~28) but chokes the metabolism (capture ~0%), hops=3 is the
narrow window (capture 63-82%, separations up to ~8). Study verdict:
**the first reproducible positive refractive differential of the project**
— separated bodies couple in 5/10 refractive runs vs 0/10 blind, with a
timed infall dynamic (wake coupling at generation ~11-29, body contact only
45-110 generations later, then fusion) — but the pre-registered stationary
inter-body channel does **not** form: outcomes are bimodal (total silence
or merger), sustained coupling reaches only the partner's fossil past
(lag stays infinite), and "space between bodies" still does not exist in
the model. Do not force the channel by knob search; the recorded obstacles
are the universe's small diameter at metabolism-compatible range and the
absence of anything that stabilizes approach short of merger.

A purely observational metrology pass (same file, last section;
`id_watermarks` + `_hops_at_time` + `intertube_metrics` + `wake_gap`
reconstruct the past metric from creation-ordered ids) then measured all
of it: the recession is real, linear (~1.08 hops/generation) and
routing-independent; the radiated wake front advances at only ~0.53
hops/generation, so **the metric outruns the signal 2:1** and every
generation emitted after the early window radiates into a causal event
horizon (measured: the wake of generation 400 is born 388 hops behind the
partner and never closes) — which is why coupling only ever reaches the
partner's fossil past. Infall is NOT constant acceleration: three phases
(recession, turnaround at the first wake bridge, near-linear closure by
capture-edge knitting — a zipper, not a ballistic fall), and the
silence-vs-merger bimodality is a race at birth (bridge must form within
~30 generations, before recession carries the partner past the horizon).
The recession's numeric rate is architecture-specific (tube-advance
kinematics); the horizon phenomenon is structural.

An "angular momentum" attempt then tried to desax the radial merger into a
stationary orbit via a tangential-kick initial condition
(`generate_two_motif_graph(kick_ticks=, kick_mode=)`: a burn window of
metabolic asymmetry relative to the partner, laws untouched, partner
forgotten after — `kick_ticks=0`/`none` reproduces the untouched generator
bit-for-bit). Verdict (same file, last section): **negative, by ejection**.
The reject-a-distance-class burn starves the motif (capture 2-9% vs 100%),
so tube kinematics fling the bodies to d~54 by generation 25 — past the 2:1
horizon before the burn ends — and all runs go silent (every mode, both kick
lengths, both routings). The proper-motion decomposition (radial vs a
heuristic tangential scalar T) shows T=0 during and after the burn: the
metabolic asymmetry injects no lateral drift at all, and even the unkicked
control shows no *persistent* tangential drift (T>0 only as close-range
membrane noise once bodies fuse). The structural finding: **the substrate
has no angular momentum because it has no inertia** — it conserves what a
body is (closure) and where it is (its neighbourhood), but not how it is
moving (no dynamical variable carries a rate; the depletion-drag
momentum-memory hypothesis is unsupported). The two-body sector is now
closed at this scale: silence or radial merger, never a stable separation.
Do not tune kick_ticks/mode to seek a channel — an orbit would require an
ontological addition giving the substrate a conserved rate, not an initial
condition or a knob.

That two-body inertia conclusion rested on a frame error, now corrected: with
only two bodies there is a *single* distance (a 1D line), so a transverse axis
cannot exist and the tangential scalar T was measuring a coordinate that isn't
there — not a null about inertia. The transverse coordinate first exists with
**three** bodies. `generate_three_motif_graph` + `triangle_angle` (same file,
last section) build it: A, B are plain reference motifs fixing a baseline, C is
the test body, and C's angle off the A-B baseline (graph law of cosines on the
three pairwise hop distances, computed in the past metric via `_hops_at_time`)
is a scale-invariant 2D transverse position — common recession cancels out of
the angle. `test_mode ∈ {plain, correlated, correlated_seed, forced}`:
`correlated` is the A⊕B fusion braid (inherited-heading wake dipole),
`correlated_seed` adds a prepared tangential kick (burn window), and `forced`
is a pre-registered **instrument control** that advects C sideways every
generation — it must move the angle ballistically or the observable is blind.
Only candidate *retention* / walk *start* is constrained; the delay law,
routing, and antichain rule are untouched (so `plain` is the exact control).
5-seed × 900-generation verdict (same file): forced = angle-drift exponent
**1.21 (ballistic — instrument validated)**, while plain / correlated /
correlated_seed all = **~0.56-0.59 (diffusive)**, cleanly separated, with
healthy metabolism (capture 67-89%, no starvation confound) and non-degenerate
birth triangles (angles 34-105°). So **no tangential inertia**, now a positive
null in the frame where the coordinate genuinely exists: the substrate carries
no variable holding a *rate* along the emergent transverse direction; the A⊕B
mechanism encodes a lateral *disposition* (it changes C's braid and birth
angle) but that disposition does not integrate into ballistic motion. Do not
rescue this by searching `(test_mode, seed_ticks, walk_hops)` space for a
ballistic exponent — the instrument control passing while every physical mode
stays diffusive is exactly the evidence that such a find would be meaningless
(TEI-3.x failure mode). An orbit still needs an ontological addition giving the
substrate a conserved rate; three bodies show *where* it is missing (the
transverse channel is real and measurable — it is simply memoryless).

A "topological spin" was then tried as the inertia carrier, since topology is
the one thing this graph conserves naturally: `test_mode="chiral"` (parameter
`chirality ∈ {+1,-1}`) gives C's braid a strict handedness — strand `i` parents
the consecutive block `[i, i+h, …]` mod W and starts its walk from
`previous[(i+h)%W]`, so the intake heading *circulates* one fixed direction
(mirror-symmetric `h`, topologically robust, no free knob; parents still drawn
from the previous antichain so the braid stays valid). Metabolic gate checked
first and passed — the twist *improves* capture (86-91% vs plain 67%), 0
antichain violations. 5-seed × 900-generation verdict (same file): **both
handednesses are diffusive** (h=+1: 0.49, h=−1: 0.64) — indistinguishable from
plain (0.57), cleanly separated from the ballistic `forced` control (1.21) —
and no mirror-antisymmetric net drift. So **a protected spin is not inertia**:
the substrate *can* carry a conserved topological charge (the winding is robust
and alters metabolism) but does not convert it into a conserved *rate*; a spin
here is part of *what the body is*, not *how it moves*. Do not search
`(chirality, walk_hops)` for a ballistic triple — the instrument control passing
while both chiralities stay diffusive is exactly why such a find would be
meaningless (TEI-3.x failure mode). Emergent inertia still needs an ontological
conserved *rate*; a conserved *topology*, which this substrate supports, is not
it.

The framing then shifted (three strict-Markov laws fixed in advance): no
memory — the present N is the complete instruction set ("QR code") for N+1;
constant motion is perpetuation of a state, not a change resisted by inertia;
so a movement state must be encoded in present structure whose *reading*
displaces it while reproducing it (formally, a translation eigenstate
Φ(σ)=T(σ) of the one-step map). Three encodings were analyzed: a charge
dipole (rejected on paper: both existing readings of charge have the
anti-propulsive sign — blind ignores it, refraction *climbs* it back toward
the trail, and flipping that would contradict Canal-1 gravity), strict
whole-membrane antichain exclusion (reserve, not yet built), and the
**self-collimating accretion front** (`test_mode="front"`, built): the QR code
is the membrane's external in-edges (the prey that built the present
generation — pure present edge structure), and all W capture walks of N+1
start from that shared pool. Binary rule, no knob; metabolic gate passed
(capture 99-100%, 0 violations). 5-seed × 900-generation verdict (same file):
**capture-lock, 5/5 seeds** — the feedback self-perpetuates flawlessly (the
Markovian encoding *works*, unlike the cached pointer of `correlated`), but
its fixed point is attachment, not motion: within ~100 generations C locks
onto the nearest reference body and rides at hop distance 1-3 for 580+
generations, eating 94-97% of its captures from the host's living membrane
(one module run showed the variant: squatting the host's fossil trail 39 hops
behind). The angle instrument shows the pre-registered *anchoring* signature
(frozen quantized plateaus at 60/90/120° — tiny integer triangles), not
ballistic drift. Structural reading: the flux is perishable (TEI's own
axiom), so the only renewable intake locus is another worldtube — in this
substrate a self-perpetuating displacement state cannot point at *space*,
only at *matter*: the QR code of movement compiles into gravitational
capture. Silver lining recorded: this is the project's **first stable
two-body bound state** (neither silence nor merger — a contact binary with
C's identity intact), though still at contact range, so "space between
bodies" remains absent. Do not rescue the front by exempting other bodies'
members from the pool ("don't eat bodies" is a new ad-hoc law steering the
mechanism away from its natural attractor — TEI-3.x failure mode); the
attractor is the finding.

Option C (`test_mode="strict"`) then closed the QR-code program: capture
candidates must be causally independent of the *whole* previous generation
(the body as a whole interprets — binary widening of the independence scope,
no knob). Verdict (same file): **metabolic gate failure with a positive
geometric finding**. Capture starts ~60-70% then collapses to 7-13% within
~60 generations — and the measured cause is the strongest result of the arc:
a plain body's neighbourhood contains **0% strictly-independent nodes at
every radius ≤ 6, at every age** — a body's local space is entirely made of
its own causal entanglements (ordinary metabolism is, in strict terms, ~100%
re-interpretation of the body's own extended cone). One seed in three escaped
by locking onto the partner's worldtube (99% of captures, contact range) —
the same bound-state attractor as `front`, reached from the opposite
direction. The program's adjudication: B rejected on sign, A and C both
terminate in matter-bound-to-matter; a self-perpetuating displacement state
pointing at *space* does not exist in this substrate at this scale, because
at metabolic range there is no causally-fresh space to move into. Do not
search for an intermediate independence scope between "chosen parents" and
"whole membrane" that passes the gate — that interpolation is a knob
(TEI-3.x failure mode). Per protocol, no drift study was run for `strict`
(the gate failed first); the frontier profile is a pure observation on the
unmodified plain dynamics.

The program then pivoted from kinematics to **material genesis**
(`generate_soup_graph`): N=20 bodies, all under the option-A front rule,
sown at random (no separation control), blind selection with a
pre-registered death cutoff (0 captures for 5 consecutive generations →
dissolution; fossil stays edible). Verdict (same file, last section): a
**two-phase architecture controlled by flux supply**. Abundance (20
events/body/tick, the labs' standard): a *gas* — 60/60 survive, capture
96-100%, cross-body diet median 21-27%, contacts transient over 500
generations, and **the 3-body lab's capture-lock does not reproduce (0/60
vs 5/5)** — the parasitic binary was a low-density artifact: in a crowd,
every neighbourhood is a mixed-wake soup and the front's feedback never
converges on one tube. Scarcity (5 events/body): *condensation* — still
zero deaths, but cross-body diet jumps to median 90% and contact clusters
condense into a compact (d 2-6) **reciprocal trophic web** (intra-cluster
63-99%, 0% extra-cluster, no dominant host, living-grazing 19-43% + wake
recycling) — a closed communal metabolism that defeats scarcity by recycling
its own matter. Survival and aggregation are the same act; the death rule
has never actually fired (candidate conjecture, not result: population
recycling may make true starvation impossible). A 5-seed crystallography
pass (scarce, seeds 1-5) then characterized the cluster: **the shape is a
law, the size is stochastic**. Topology is always a **dense homogeneous
liquid droplet** — a mutual-grazing clique (density ≥0.94, clustering ≥0.95,
degree-Gini ~0, flow balance 0.71-0.88), NOT a star/chain/ring, and
progressive flow-thresholding dissolves it uniformly (no crystalline core,
no privileged strong bond). There **is** a core/surface differentiation
(core: bg 0-2%, intra 98-100%, saturated; surface: bg 20-41%, reduced
degree, still hunting external flux = free valence). But final cluster size
is stochastic (seeds 1-5: 9,6,4,5,4; median ~5, and the universe makes
*several* coexisting droplets), and the growth curve is noisy (not the
clean monotone accretion the single-seed pass suggested). Caveats: scarce
now 5-seed (architecture replicates, size does not); abundance negative is
3-seed; death rule never fired in any of the 10+ runs. `info["capture_logs"]`
carries per-body per-generation captured ids — the raw material for the
trophic analysis (owner/living/fossil classification is post-hoc, see the
analysis file).

An **emergent thermodynamics** was then read off the soup via
`grazing_bond_volatility` (temperature = topological volatility of the
grazing bonds; a bond i→j is active when j's tube supplies ≥20% of i's
captures in a disjoint time-window; `turnover`/`occupancy_mean`/
`frozen_fraction` measure its churn). Verdict (same file): **a single
emergent observable resolves three states of matter, ordered monotonically
by flux supply** — gas (abundance, turnover 0.96, occupancy 0.12, 0 frozen
bonds), liquid (scarcity, 0.81 / 0.21), cold liquid (2 ev/body, 0.71 / 0.28)
— and at low flux **plus a long horizon, some seeds crystallize into a
solid** (turnover collapses to ~0.08-0.29, frozen_fraction jumps to
0.56-0.94): a sharp, stochastic, time-driven nucleation (the rest stay
supercooled-liquid, with a pre-freezing continuum). So flux alone (at 250
gen) does not freeze it; flux-low + time does, via nucleation. A
**crystal-vs-glass horizon study** (12 seeds × 1500 gen, 2 ev/body) then
settled the endgame: the nucleation rate **plateaus at ~17%** (2/12 at 1500
gen = the *same* 2 seeds as 2/11 at 600 gen — zero new nucleation across 900
extra generations), crystallization is an **early-or-never** event (~gen
250-600), and the 10 non-nucleated seeds stay trapped in a metastable
supercooled liquid — a **causal glass**. Freezing is not fatal: the
substrate supports gas, liquid, crystal *and* glass. Seed anatomy (2
crystallizers): the crystal **nucleates in the saturated core** (core-core
bonds freeze at onset, median block 9) and radiates outward (free-valence
surface bonds lock 2-6 blocks / ~50-150 gen later) — the surface is the last
to freeze, not the first. Methodology lesson baked into the tool: use
**disjoint** windows (an overlapping sliding window pins turnover to a width
floor and hides the signal); the `turnover` metric is partly
density-confounded, so read it with the density-free per-bond
`occupancy_mean`/`frozen_fraction`, which move the same way. Caveats:
"temperature/liquid/solid/glass" are analogies (no derived free energy);
nucleation rate ~2/12 is small-sample and a finite horizon can't prove no
late nucleation ever occurs. Do not tune toward a target — flux supply and
horizon are the swept physical controls, not fitted knobs.

## Keeping this file current

If the toy model grows further (new generators, refinements to the shadow
rule, a gravity-deflection calculation per TEI 7.7-7.8), update this file's
layout section and governing-discipline section to match — don't let it
drift into describing scaffolding that no longer reflects the code.
