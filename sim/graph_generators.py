"""Causal graph generators and connectivity-growth measurement.

Toy model for the open question in TEI 5.0 Partie 3.2 / 7.5: the number of nodes
reachable within N causal steps ("ticks") from a point is claimed to grow
polynomially (as N^dim), never exponentially like a generic graph. This module
gives two concrete generators to compare against each other:

- `generate_random_dag`: a generic random causal DAG with no embedding and no
  notion of distance. Its reachable set is expected to grow much faster than any
  fixed power of N (it saturates at the total node count within a handful of
  hops) -- the "regime generique" TEI contrasts itself against.

- `sprinkle_minkowski` + `reachable_within_ticks`: a Poisson sprinkling of points
  into `dim`-dimensional Minkowski coordinates, ordered by the standard causal
  relation. The volume of a causal light cone up to proper time tau in a
  `dim`-dimensional spacetime scales as tau**dim -- this is standard causal set
  theory (the Myrheim-Meyer volume-dimension estimator; see Bombelli, Henson,
  Sorkin and math/causal_set_dimension.md for the derivation and references), not
  a new TEI result. It reproduces the polynomial growth by construction, since an
  embedding dimension is imposed externally on the sprinkling.

- `generate_tei_shadow_graph`: TEI's own candidate mechanism for that open
  question (the "Regle de l'Ombre Causale" / Causal Shadow Rule) -- a purely
  local assembly rule with no embedding at all. Each new node draws edges to at
  most `k` existing nodes, under one hard constraint: the chosen nodes must be
  mutually causally independent (no existing directed path between any two of
  them), so the edge set is always a strict transitive reduction of the causal
  order it defines -- no node may connect directly to an ancestor when a more
  recent descendant of that ancestor is also being connected to (that would be
  a redundant "shortcut" past the intermediate relay). Whether this rule alone
  produces polynomial growth, and whether any resulting exponent stabilises
  near an integer such as 3, is an empirical question answered (not assumed) in
  math/tei_shadow_rule_analysis.md; see that file for the raw results and their
  honest reading -- they do not confirm the N^3 hypothesis.

- `generate_event_driven_shadow_graph`: a second, more ontologically careful
  realization of the same Causal Shadow Rule. `generate_tei_shadow_graph`
  still has two god's-eye-view assumptions baked in -- a global `for` loop
  that advances every node in lockstep, and parent selection sampled
  uniformly from the *entire* front. This generator removes both (async,
  per-node delay instead of a tick loop; bounded local random walk instead of
  global sampling; no saturation wall, only unbounded-but-diluting delay) and
  measures growth from a designated Observer's own point of view rather than
  from an outside "God's eye" origin -- see its docstring and
  math/event_driven_shadow_analysis.md for the design history (including a
  documented dead end: a fixed-node Observer, rather than a self-continuing
  worldline, empirically fails to accumulate meaningful ticks at all).

- `generate_braided_motif_graph`: the same event-driven engine, but the
  Observer is a *closed motif* (matter) instead of an open chain (light): a
  worldtube of generations, each an antichain of `motif_width` nodes, braided
  by >= 2 internal parents per node and metabolizing via antichain-checked
  captures from the background flux. Built after the open-chain Observer was
  shown to be photon-like (it abandons its charge at every step) and therefore
  structurally unable to hold space around itself under attractive routing --
  see math/event_driven_shadow_analysis.md for that verdict and for the
  pre-registered halo criterion this generator is judged by.

- `generate_two_motif_graph`: the two-body ("Earth-Mars", TEI 6bis.4) probe.
  Two independent closed motifs, born as localized clusters of fresh nodes at
  a controlled relational separation (undirected graph distance -- the only
  distance a non-embedded universe has), advancing concurrently in the same
  flux. Built after the single-body self-halo failed its criterion three
  times for three different verified reasons; the probe question changes
  from "does a body dress itself in space" to "does the crossing of two
  bodies' radiations sustain an inter-body causal channel" -- measured via
  `first_contact_lag` (causal distance in proper-time units, the theory's
  own distance-regularity question) and `interval_width` between the two
  worldtubes (the transverse thickness of the A->B channel).

Neither `generate_random_dag` nor `sprinkle_minkowski` explains why an exponent
of 3 (rather than 2 or 4) should emerge from purely local, non-embedded
coupling rules -- that is the actual open question (TEI 7.5). This module is
instrumentation for exploring it, not a claimed solution to it.
"""

import argparse
import bisect
import heapq
import math
from collections import deque

import networkx as nx
import numpy as np


def generate_random_dag(n_nodes, out_degree, seed=None):
    """Generic random causal DAG: node i links back to `out_degree` earlier nodes chosen uniformly at random."""
    rng = np.random.default_rng(seed)
    graph = nx.DiGraph()
    graph.add_nodes_from(range(n_nodes))
    for node in range(1, n_nodes):
        n_links = min(out_degree, node)
        parents = rng.choice(node, size=n_links, replace=False)
        for parent in parents:
            graph.add_edge(int(parent), node)
    return graph


def sprinkle_minkowski(n_points, dim, seed=None):
    """Poisson sprinkling of `n_points` into a unit hypercube in Minkowski coordinates.

    Coordinate 0 is time, coordinates 1..dim-1 are space.
    """
    rng = np.random.default_rng(seed)
    return rng.uniform(0.0, 1.0, size=(n_points, dim))


def generate_tei_shadow_graph(n_nodes, k, valence=None, seed=None):
    """TEI Causal Shadow Rule generator: bounded valence + strict transitive reduction.

    Starts from a small initial antichain of `k` nodes ("the front"). At each
    step a new node draws edges from up to `k` existing front members, subject
    to one hard constraint (the "causal shadow"): the chosen parents must be a
    local antichain -- no two of them may already be connected by a directed
    path. Connecting to both an ancestor A and a descendant B of A would make
    the A -> new_node edge a redundant shortcut past the relay at B, which is
    exactly what a transitive reduction forbids.

    Each node can be selected as a parent at most `valence` times (default:
    `k`) before it drops out of the front; this "cadence gauge" is what lets
    the front keep being replenished by new nodes instead of collapsing after
    the initial antichain is used up. Ancestor sets are tracked incrementally
    as integer bitmasks (bit i set means node i is an ancestor) so the
    antichain check is a cheap bitwise test rather than a graph traversal.

    No coordinates, no metric, no embedding dimension is ever used: connectivity
    growth is purely a consequence of this local assembly rule.
    """
    if valence is None:
        valence = k
    if n_nodes <= k:
        raise ValueError("n_nodes must exceed k")

    rng = np.random.default_rng(seed)
    graph = nx.DiGraph()

    n0 = k
    graph.add_nodes_from(range(n0))

    remaining_valence = np.full(n_nodes, valence, dtype=np.int64)
    ancestors = [0] * n_nodes  # bitmask ancestor sets, indexed by node id

    front = list(range(n0))
    max_attempts = max(50, k * 20)

    for new_node in range(n0, n_nodes):
        graph.add_node(new_node)
        chosen = []
        attempts = 0
        while len(chosen) < k and attempts < max_attempts and front:
            candidate = front[rng.integers(0, len(front))]
            attempts += 1
            if remaining_valence[candidate] <= 0 or candidate in chosen:
                continue
            candidate_ancestors = ancestors[candidate]
            independent = all(
                not (candidate_ancestors >> parent) & 1 and not (ancestors[parent] >> candidate) & 1
                for parent in chosen
            )
            if independent:
                chosen.append(candidate)

        if not chosen:
            # Extremely unlikely with a healthy front: fall back to any one
            # available node rather than leaving the new node parentless.
            chosen = [c for c in front if remaining_valence[c] > 0][:1]

        new_ancestors = 0
        for parent in chosen:
            graph.add_edge(parent, new_node)
            new_ancestors |= ancestors[parent] | (1 << parent)
            remaining_valence[parent] -= 1

        ancestors[new_node] = new_ancestors
        front.append(new_node)

        if (new_node - n0) % 5000 == 0:
            front = [node for node in front if remaining_valence[node] > 0]

    return graph


def _local_walk_candidate(graph, start, rng, max_hops, charge=None):
    """One candidate found by a bounded random walk from `start` over existing edges (either direction).

    With `charge=None` the walk is blind: each neighbor is equally likely.
    With a `charge` list, each step lands on a neighbor with probability
    proportional to `1 + charge[neighbor]` -- *exactly* the same law that sets
    a node's delay (`delay = 1 + charge`). This is the "refraction in the
    flux" routing (TEI 7.7): the walk is not given a new attraction knob; the
    charge landscape that already slows dense nodes down is simply made
    visible to the same walk that routes flux through them. Denser = slower =
    more likely to be where the walk ends up. No free coupling parameter
    exists to tune.
    """
    node = start
    for _ in range(int(rng.integers(1, max_hops + 1))):
        neighbors = list(graph.predecessors(node)) + list(graph.successors(node))
        if not neighbors:
            break
        if charge is None:
            node = neighbors[rng.integers(0, len(neighbors))]
        else:
            weights = np.array([1.0 + charge[n] for n in neighbors], dtype=float)
            node = neighbors[rng.choice(len(neighbors), p=weights / weights.sum())]
    return node


def _pick_independent_parents(graph, trigger, k, rng, walk_hops, ancestors, max_attempts, charge=None):
    """`trigger` plus up to k-1 more mutually causally independent parents, found via local walk."""
    chosen = [trigger]
    attempts = 0
    while len(chosen) < k and attempts < max_attempts:
        candidate = _local_walk_candidate(graph, trigger, rng, walk_hops, charge=charge)
        attempts += 1
        if candidate in chosen:
            continue
        candidate_ancestors = ancestors[candidate]
        independent = all(
            not (candidate_ancestors >> p) & 1 and not (ancestors[p] >> candidate) & 1
            for p in chosen
        )
        if independent:
            chosen.append(candidate)
    return chosen


def generate_event_driven_shadow_graph(
    n_ticks_observer,
    k,
    warmup_events=3000,
    walk_hops=8,
    background_ratio=50,
    charge_biased_routing=False,
    seed=None,
    max_nodes=2_000_000,
):
    """Event-driven, local, observer-relative realization of the Causal Shadow Rule.

    `generate_tei_shadow_graph` still has two god's-eye-view assumptions baked
    in: a global `for` loop that advances every node in lockstep, and parent
    selection sampled uniformly from the *entire* front (which requires
    knowing the whole universe's history at every step, however large it has
    grown). This generator removes both:

    1. No global tick. Node creation is driven by an asynchronous priority
       queue (the standard discrete-event-simulation pattern): each node has
       its own pending "next action" time, and whichever is smallest fires
       next. Nothing is woken up except by its own accumulated delay.
    2. No saturation wall. Out-degree ("charge") is unbounded -- a node is
       never retired from eligibility. What grows with charge is only its own
       delay before its next action (`delay(charge) = 1 + charge`, strictly
       linear: each additional active relation costs exactly one silent-relay
       unit, never a geometric square/exponential). A busy node is never
       blocked, only diluted.
    3. No global sampling anywhere. Both the background dynamics and the
       Observer's own parent selection draw candidates via a bounded local
       random walk (`walk_hops` steps, over existing edges in both
       directions) starting at the acting node -- never a draw from the
       whole population.

    Growth is measured from a designated Observer's own point of view (TEI
    6ter.3-D: a persistent object is a "motif ferme", a closed loop of
    recurring executions -- not a single static point). This matters
    concretely: an earlier version of this generator modeled the Observer as
    one fixed node hoping to be reselected by the dynamics above, and that
    empirically failed under both global-heap selection and local-random-walk
    selection alike -- a fixed node's cumulative participation count plateaus
    (logarithmic growth at best, often outright starvation), because any
    newly created node competes on equal footing and the population never
    stops growing. The fix, grounded in the project's own ontology rather
    than invented ad hoc: the Observer is not a node, it is a worldline. At
    each of its own ticks, its current self picks its own next self among its
    newly created children (self-continuation), guaranteeing steady progress
    with no competition against the rest of the universe.

    Three phases:

    - Warmup (`warmup_events`, background only): dissipates the initial
      antichain's structural artifacts before anything is measured.
    - Observer election: a *fresh* node (zero charge, so its later successors
      are exactly its own worldline, uncontaminated by pre-election activity)
      is drawn at random from the population active at the end of warmup.
    - Concurrent phase: the Observer's worldline self-continues once per
      tick, interleaved with `background_ratio` background events per tick
      -- a fixed ratio, not a time-based comparison. A time-based comparison
      (fire whichever of the worldline or the background heap has the
      smaller scheduled time) was tried first and abandoned: the background
      heap accumulates a large backlog of closely-spaced low-delay entries,
      so its clock advances far more slowly per event than the worldline's,
      and the comparison let hundreds of thousands of background events fire
      per single worldline tick. `background_ratio` and `walk_hops` both
      need to be reasonably large (a few dozen, and roughly 8+, respectively)
      for the Observer's causal shadow to pick up meaningful branching beyond
      its own guaranteed self-continuation chain -- at low settings the
      measured curve is barely distinguishable from a bare line, since
      outside events rarely walk back to reconnect with the Observer's own
      past. See math/event_driven_shadow_analysis.md for measurements.

    `charge_biased_routing` selects the routing law of the local walk (both
    for background events and for the Observer's co-parent picks). False
    (default): blind walk, every neighbor equally likely -- the variant whose
    sliding-window diagnostic showed the Observer decoupling from the flux as
    it ages (transverse width collapsing toward the bare-chain floor; see
    math/event_driven_shadow_analysis.md). True: each walk step lands on a
    neighbor with probability proportional to `1 + charge[neighbor]`, i.e.
    the *same* law that sets delays -- the "refraction in the flux" reading
    of gravity (TEI 7.7: denser = slower = trajectories bend toward it),
    with the bias strength fixed by the delay law rather than by any new
    free parameter. This is a variant selector for A/B comparison, not a
    tunable knob.

    Returns `(graph, worldline, external_time)`:
      - `graph`: the full nx.DiGraph (background + worldline).
      - `worldline`: list of node ids, the Observer's own identity at each of
        its own ticks (`worldline[0]` is "Observer zero"; length
        `n_ticks_observer + 1`).
      - `external_time`: cumulative descriptive delay at each tick (length
        `n_ticks_observer`) -- how much "external coordinate time" the
        network experienced per unit of the Observer's own proper time.
        Purely descriptive: computed from the real charge of the parents
        chosen at each tick, but never gates the loop -- the Observer's own
        proper time advances by exactly one tick per iteration, exactly as a
        real observer never feels their own time dilating.
    """
    rng = np.random.default_rng(seed)
    graph = nx.DiGraph()

    n0 = k
    graph.add_nodes_from(range(n0))

    charge = [0] * n0
    current_gen = [0] * n0
    ancestors = [0] * n0
    max_attempts = max(50, k * 20)

    def delay(load):
        return 1.0 + load

    def new_slot():
        charge.append(0)
        current_gen.append(0)
        ancestors.append(0)

    heap = []
    next_id = n0
    for node in range(n0):
        heapq.heappush(heap, (1.0, node, 0))

    # The routing law: blind (None) or refractive (the charge list itself, so
    # the walk sees exactly the landscape that the delay law defines).
    routing_charge = charge if charge_biased_routing else None

    def fire_background_event(t, trigger):
        nonlocal next_id
        chosen = _pick_independent_parents(
            graph, trigger, k, rng, walk_hops, ancestors, max_attempts, charge=routing_charge
        )
        new_node = next_id
        next_id += 1
        graph.add_node(new_node)
        new_slot()
        new_ancestors = 0
        for p in chosen:
            graph.add_edge(p, new_node)
            new_ancestors |= ancestors[p] | (1 << p)
            charge[p] += 1
            current_gen[p] += 1
            heapq.heappush(heap, (t + delay(charge[p]), p, current_gen[p]))
        ancestors[new_node] = new_ancestors
        heapq.heappush(heap, (t + delay(0), new_node, current_gen[new_node]))

    # --- Phase 1: warmup (background only, dissipate initial-antichain artifacts) ---
    t = 0.0
    for _ in range(warmup_events):
        if next_id >= max_nodes:
            raise RuntimeError(f"max_nodes ({max_nodes}) reached during warmup")
        t, trigger, gen = heapq.heappop(heap)
        if gen != current_gen[trigger]:
            continue
        fire_background_event(t, trigger)

    # --- Phase 2: elect "Observer zero" (fresh node from the stabilized population) ---
    fresh = [node for node in range(next_id) if charge[node] == 0]
    observer_root = int(rng.choice(fresh))

    # --- Phase 3: concurrent background growth + self-continuing worldline ---
    worldline = [observer_root]
    external_time = np.zeros(n_ticks_observer)
    self_node = observer_root
    worldline_time = t

    for tick in range(n_ticks_observer):
        if next_id >= max_nodes:
            raise RuntimeError(
                f"max_nodes ({max_nodes}) reached with only {tick}/{n_ticks_observer} "
                "observer ticks -- raise max_nodes or lower background_ratio"
            )
        chosen = _pick_independent_parents(
            graph, self_node, k, rng, walk_hops, ancestors, max_attempts, charge=routing_charge
        )
        step_delay = delay(float(np.mean([charge[p] for p in chosen])))
        new_node = next_id
        next_id += 1
        graph.add_node(new_node)
        new_slot()
        new_ancestors = 0
        for p in chosen:
            graph.add_edge(p, new_node)
            new_ancestors |= ancestors[p] | (1 << p)
            charge[p] += 1
        ancestors[new_node] = new_ancestors
        self_node = new_node
        worldline.append(self_node)
        worldline_time += step_delay
        external_time[tick] = worldline_time

        for _ in range(background_ratio):
            if not heap or next_id >= max_nodes:
                break
            t2, trigger, gen = heapq.heappop(heap)
            if gen != current_gen[trigger]:
                continue
            fire_background_event(t2, trigger)

    return graph, worldline, external_time


def generate_braided_motif_graph(
    n_generations,
    k,
    motif_width,
    warmup_events=3000,
    walk_hops=8,
    background_ratio=50,
    internal_parents=2,
    charge_biased_routing=False,
    seed=None,
    max_nodes=2_000_000,
):
    """Event-driven Causal Shadow Rule with a *closed-motif* (matter-like) Observer.

    The open-chain worldline of `generate_event_driven_shadow_graph` was shown
    (math/event_driven_shadow_analysis.md) to be, in TEI's own classification,
    photon-like: it abandons its charge at every self-continuation step, so
    under attractive (refractive) routing the flux drains *away* from it and
    its transverse space collapses to a bare wire. TEI 6ter.3-D says matter is
    instead a closed motif -- a loop of recurring executions that re-executes
    "sur place". A DAG forbids literal cycles, so the closure is implemented
    as a *braid in causal time*: a worldtube of generations, each generation
    an antichain of `motif_width` (W) nodes, re-executing the same connection
    pattern over a persistent neighbourhood.

    Per generation (one tick of the motif's proper time), each of the W new
    nodes takes:

    - `internal_parents` (default 2) distinct parents from the previous
      generation -- the braiding. Two is the minimum closure: with a single
      internal parent the "tube" degenerates into W independent chains (W
      photons, not one object). Generations are automatically antichains
      (fresh siblings share no edges), and internal parents are drawn from an
      antichain, so the Causal Shadow Rule holds by construction.
    - `k - internal_parents` *capture* attempts: local-walk candidates from
      the background flux, subject to the same mutual-independence check as
      every other parent in this module. Captures can fail the check; the
      realized capture rate is therefore a *measured* metabolic property of
      the run (returned as `capture_counts`), never a decreed one. Capture
      *consumes* its prey (conservation law, TEI 7.7: an instruction is
      conserved until interpretation -- interpretation spends it): the
      captured node's pending background event is invalidated and rescheduled
      after a charge-grown delay, exactly the treatment every background
      event already applies to its own parents. An earlier version skimmed
      without consuming (the captured node kept its agenda untouched), which
      left the surrounding medium tension-free -- see the radial-anisotropy
      section of math/event_driven_shadow_analysis.md.

    Entropy is the generational rotation itself: once generation g+1 exists,
    the motif never re-executes over generation g again. Old members are not
    deleted (the DAG is append-only) -- they are *radiated*: on retirement
    they are scheduled onto the event heap (generation bump + reschedule
    after a charge-grown delay, the same operation as capture consumption),
    so the motif's wake re-enters the flux and fires background events of its
    own. This implements TEI 6bis.2 (a mass in permanent restructuring expels
    instructions at every internal reorganization): the motif's entropy and
    its emission are one and the same event, and no node in the universe is
    exempt from the heap. The motif's identity is the unbroken succession of
    generations; nothing stores it (present encodes present+1, per the
    no-memory rule).

    Structural consequence, stated before any measurement: `k = 2` cannot
    make matter under this rule -- braiding consumes both parent slots
    (`internal_parents = 2`) leaving zero capture slots (a sealed crystal with
    no metabolism), and dropping to one internal parent un-braids the tube
    into photons. Matter requires `k >= 3`.

    `motif_width` W is the motif's *mass* -- a physical property of the object
    under test, to be swept (e.g. W in {2, 4, 8}), never tuned toward a target
    exponent. `internal_parents` is a discrete structural choice: 2 is the
    main rule, `k - 1` the robustness control.

    The pre-registered success criterion for the gravity question lives in
    math/event_driven_shadow_analysis.md: the signal is the *halo* -- the
    sliding-window interval width in excess of what the identical motif shows
    under blind routing -- not the tube's own built-in width, which this
    construction guarantees and which therefore proves nothing.

    Returns `(graph, generations, external_time, capture_counts)`:
      - `generations`: list of `n_generations + 1` lists of node ids
        (`generations[0]` is the seeded antichain of W fresh nodes).
      - `external_time`: cumulative descriptive delay per generation (same
        convention as the worldline generator: computed from real parent
        charges, never gating the loop).
      - `capture_counts`: successful background captures per generation.
    """
    if internal_parents < 2:
        raise ValueError("braiding requires internal_parents >= 2")
    if k < internal_parents:
        raise ValueError("k must be >= internal_parents")
    if motif_width < 2:
        raise ValueError("motif_width must be >= 2")

    rng = np.random.default_rng(seed)
    graph = nx.DiGraph()

    n0 = k
    graph.add_nodes_from(range(n0))

    charge = [0] * n0
    current_gen = [0] * n0
    ancestors = [0] * n0
    max_attempts = max(50, k * 20)

    def delay(load):
        return 1.0 + load

    def new_slot():
        charge.append(0)
        current_gen.append(0)
        ancestors.append(0)

    heap = []
    next_id = n0
    for node in range(n0):
        heapq.heappush(heap, (1.0, node, 0))

    routing_charge = charge if charge_biased_routing else None

    def fire_background_event(t, trigger):
        nonlocal next_id
        chosen = _pick_independent_parents(
            graph, trigger, k, rng, walk_hops, ancestors, max_attempts, charge=routing_charge
        )
        new_node = next_id
        next_id += 1
        graph.add_node(new_node)
        new_slot()
        new_ancestors = 0
        for p in chosen:
            graph.add_edge(p, new_node)
            new_ancestors |= ancestors[p] | (1 << p)
            charge[p] += 1
            current_gen[p] += 1
            heapq.heappush(heap, (t + delay(charge[p]), p, current_gen[p]))
        ancestors[new_node] = new_ancestors
        heapq.heappush(heap, (t + delay(0), new_node, current_gen[new_node]))

    # --- Phase 1: warmup (background only) ---
    t = 0.0
    for _ in range(warmup_events):
        if next_id >= max_nodes:
            raise RuntimeError(f"max_nodes ({max_nodes}) reached during warmup")
        t, trigger, gen = heapq.heappop(heap)
        if gen != current_gen[trigger]:
            continue
        fire_background_event(t, trigger)

    # --- Phase 2: seed generation 0 with W fresh nodes. A node with charge 0
    # has no descendants, so any set of charge-0 nodes is automatically an
    # antichain -- no search needed. ---
    fresh = [node for node in range(next_id) if charge[node] == 0]
    if len(fresh) < motif_width:
        raise RuntimeError("not enough fresh nodes after warmup to seed the motif")
    generation_zero = [int(x) for x in rng.choice(fresh, size=motif_width, replace=False)]

    generations = [generation_zero]
    external_time = np.zeros(n_generations)
    capture_counts = np.zeros(n_generations, dtype=int)
    worldtube_time = t
    background_time = t  # latest known background-clock time, for consumption rescheduling

    # --- Phase 3: braided advance, interleaved with background growth ---
    for g in range(n_generations):
        previous = generations[-1]
        previous_set = set(previous)
        new_generation = []
        new_generation_set = set()
        parent_charges = []
        captures = 0
        for _ in range(motif_width):
            if next_id >= max_nodes:
                raise RuntimeError(
                    f"max_nodes ({max_nodes}) reached at generation {g}/{n_generations}"
                )
            picks = rng.choice(len(previous), size=internal_parents, replace=False)
            chosen = [previous[i] for i in picks]
            captured_nodes = []
            attempts = 0
            while len(captured_nodes) < k - internal_parents and attempts < max_attempts:
                candidate = _local_walk_candidate(
                    graph, chosen[0], rng, walk_hops, charge=routing_charge
                )
                attempts += 1
                # Capture must metabolize *background* flux: both membranes of
                # the motif are excluded -- the previous generation (its
                # members would pass the antichain check, being mutually
                # independent, but eating a sibling strand is not nourishment)
                # and the generation under construction (a fresh sibling can
                # pass the check too, when the internal parents are disjoint,
                # which would create a same-generation edge and silently break
                # the generation's antichain property, corrupting every later
                # internal-parent pick).
                if candidate in chosen or candidate in previous_set or candidate in new_generation_set:
                    continue
                candidate_ancestors = ancestors[candidate]
                independent = all(
                    not (candidate_ancestors >> p) & 1 and not (ancestors[p] >> candidate) & 1
                    for p in chosen
                )
                if independent:
                    chosen.append(candidate)
                    captured_nodes.append(candidate)
            captures += len(captured_nodes)

            new_node = next_id
            next_id += 1
            graph.add_node(new_node)
            new_slot()
            new_ancestors = 0
            for p in chosen:
                graph.add_edge(p, new_node)
                new_ancestors |= ancestors[p] | (1 << p)
                charge[p] += 1
            ancestors[new_node] = new_ancestors
            new_generation.append(new_node)
            new_generation_set.add(new_node)
            parent_charges.extend(charge[p] for p in chosen)

            # Consumption (conservation law, TEI 7.7: an instruction is
            # conserved *until interpretation* -- interpretation spends it).
            # Capture applies to its prey exactly what every background event
            # already applies to its parents: invalidate the pending event
            # (generation bump) and reschedule after a charge-grown delay.
            # Without this, captured flux was interpreted AND kept its own
            # agenda intact -- double-counting that left the motif skimming
            # the medium without ever taking anything from it (no tension, no
            # accretion). Internal membrane parents are left as before:
            # rotation already retires them, and whether the motif's spent
            # membrane should also re-enter the flux (radiation) is a separate
            # question, deliberately not part of this fix.
            for captured in captured_nodes:
                current_gen[captured] += 1
                heapq.heappush(
                    heap,
                    (background_time + delay(charge[captured]), captured, current_gen[captured]),
                )

        generations.append(new_generation)
        capture_counts[g] = captures
        worldtube_time += delay(float(np.mean(parent_charges)))
        external_time[g] = worldtube_time

        # Radiation (TEI 6bis.2: a mass in permanent restructuring expels
        # instructions at every internal reorganization). The generation just
        # retired by the rotation re-enters the flux: entropy and emission are
        # the same event. Retirement applies the same operation as capture
        # consumption -- generation bump (which invalidates any stale pending
        # entry, e.g. generation zero's original background birth event, so a
        # single instruction never fires twice) and rescheduling after a
        # charge-grown delay. This removes the last special exemption in the
        # universe: membrane nodes were the only nodes never scheduled on the
        # event heap.
        for retired in previous:
            current_gen[retired] += 1
            heapq.heappush(
                heap,
                (background_time + delay(charge[retired]), retired, current_gen[retired]),
            )

        for _ in range(background_ratio):
            if not heap or next_id >= max_nodes:
                break
            t2, trigger, gen = heapq.heappop(heap)
            if gen != current_gen[trigger]:
                continue
            background_time = t2
            fire_background_event(t2, trigger)

    return graph, generations, external_time, capture_counts


def _undirected_distances(graph, source):
    """BFS hop distances from `source` over the graph viewed as undirected.

    The only notion of "how far apart" two nodes are in a non-embedded
    relational universe: count relays, ignoring edge direction.
    """
    distances = {source: 0}
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v in list(graph.predecessors(u)) + list(graph.successors(u)):
            if v not in distances:
                distances[v] = distances[u] + 1
                queue.append(v)
    return distances


def generate_two_motif_graph(
    n_generations,
    k,
    motif_width,
    birth_separation=4,
    warmup_events=3000,
    walk_hops=8,
    background_ratio=50,
    internal_parents=2,
    charge_biased_routing=False,
    kick_ticks=0,
    kick_mode="none",
    seed=None,
    max_nodes=2_000_000,
):
    """Two-body probe: two independent closed motifs in the same flux (TEI 6bis.4).

    Identical physics to `generate_braided_motif_graph` (braiding, metabolism
    with consumption, radiation on retirement, optional refractive routing) --
    but with *two* motifs, A and B, so the observable can change from a
    single body's self-halo (which failed its pre-registered criterion three
    times, see math/event_driven_shadow_analysis.md) to the causal channel
    *between* bodies: TEI 6bis.4's own "how is a stable Earth-Mars relation
    maintained across perishable flux" question.

    Birth: each motif's generation zero is a *localized cluster* -- a fresh
    (charge-0) node plus its `motif_width - 1` nearest fresh nodes by
    undirected hop distance. Localization at birth is an initialization
    requirement, not a new dynamic law: two motifs seeded from scattered
    nodes would interpenetrate from the start and there would be no
    "between" to measure. Cluster B's seed is the closest fresh node at
    undirected distance >= `birth_separation` from cluster A's seed; the
    realized separation is returned (the warmup universe is small-world --
    diameter ~6 at 3000 warmup events -- so only modest separations exist,
    and requesting an unavailable one raises).

    Per tick of shared proper time, A advances one generation, then B, then
    `background_ratio` background events fire (fixed order, a deliberate
    small asymmetry, documented rather than hidden). Nothing excludes one
    motif's walk from the other's nodes -- the dynamics stay purely local
    with no new rule -- but cross-couplings are *counted*:
    `contact_living` (a capture landing on the other motif's living
    membrane: direct body contact) and `contact_wake_by_a` /
    `contact_wake_by_b` (a capture landing on the other motif's
    retired/radiated members -- the desired channel coupling, split by
    direction: A eating B's wake is matter flowing B -> A, and vice versa).

    Tangential kick (the "angular momentum" initial condition, off by default).
    For the first `kick_ticks` generations only, each motif's *metabolism* is
    temporarily made asymmetric relative to its partner -- the dynamical laws
    (delay, refractive routing, antichain rule) are never touched. Among the
    candidates the ordinary walk produces and the antichain rule validates, a
    kick-active generation additionally constrains which are *retained*, by
    the candidate's undirected distance to the partner's living membrane
    versus the capturing motif's own distance `d_self`:

    - `kick_mode="none"` (default): no constraint -- identical to the untouched
      generator (so `kick_ticks=0` or `kick_mode="none"` is the exact control).
    - `kick_mode="noinfall"`: reject radial-in candidates (dist < d_self) --
      during the burn the motif refuses to grow toward its partner; captures
      land iso-distant or outward.
    - `kick_mode="iso"`: retain only iso-distant candidates (dist == d_self) --
      pure tangential growth along the equidistance shell; the strongest and
      most starvation-prone variant.

    After `kick_ticks` the partner is never referenced again -- this is a
    preparation of the initial state, exactly like the birth separation `D`
    and mass `W`, not a change of law. `kick_ticks` is the sanctioned
    initial-condition parameter (how much "angular momentum" is prepared);
    whether any induced lateral drift *persists* past the burn is the
    emergent-inertia question the orbit test exists to answer, not something
    the burn can force.

    Returns `(graph, generations_a, generations_b, info)` where `info` is a
    dict with `realized_separation`, `capture_counts_a/b` (per generation),
    `contact_living`, `contact_wake_by_a/b`, `first_living_gen`,
    `first_wake_gen`, `id_watermarks`, and `external_time_a/b`.
    """
    if internal_parents < 2:
        raise ValueError("braiding requires internal_parents >= 2")
    if k < internal_parents:
        raise ValueError("k must be >= internal_parents")
    if motif_width < 2:
        raise ValueError("motif_width must be >= 2")
    if kick_mode not in ("none", "noinfall", "iso"):
        raise ValueError("kick_mode must be 'none', 'noinfall', or 'iso'")

    rng = np.random.default_rng(seed)
    graph = nx.DiGraph()

    n0 = k
    graph.add_nodes_from(range(n0))

    charge = [0] * n0
    current_gen = [0] * n0
    ancestors = [0] * n0
    max_attempts = max(50, k * 20)

    def delay(load):
        return 1.0 + load

    def new_slot():
        charge.append(0)
        current_gen.append(0)
        ancestors.append(0)

    heap = []
    next_id = n0
    for node in range(n0):
        heapq.heappush(heap, (1.0, node, 0))

    routing_charge = charge if charge_biased_routing else None

    def fire_background_event(t, trigger):
        nonlocal next_id
        chosen = _pick_independent_parents(
            graph, trigger, k, rng, walk_hops, ancestors, max_attempts, charge=routing_charge
        )
        new_node = next_id
        next_id += 1
        graph.add_node(new_node)
        new_slot()
        new_ancestors = 0
        for p in chosen:
            graph.add_edge(p, new_node)
            new_ancestors |= ancestors[p] | (1 << p)
            charge[p] += 1
            current_gen[p] += 1
            heapq.heappush(heap, (t + delay(charge[p]), p, current_gen[p]))
        ancestors[new_node] = new_ancestors
        heapq.heappush(heap, (t + delay(0), new_node, current_gen[new_node]))

    # --- Phase 1: warmup ---
    t = 0.0
    for _ in range(warmup_events):
        if next_id >= max_nodes:
            raise RuntimeError(f"max_nodes ({max_nodes}) reached during warmup")
        t, trigger, gen = heapq.heappop(heap)
        if gen != current_gen[trigger]:
            continue
        fire_background_event(t, trigger)

    # --- Phase 2: seed two localized clusters at controlled separation ---
    fresh = [node for node in range(next_id) if charge[node] == 0]
    if len(fresh) < 2 * motif_width:
        raise RuntimeError("not enough fresh nodes after warmup to seed two motifs")
    seed_a = int(rng.choice(fresh))
    dist_from_a = _undirected_distances(graph, seed_a)
    reachable_fresh = [f for f in fresh if f != seed_a and f in dist_from_a]
    by_distance_from_a = sorted(reachable_fresh, key=lambda f: dist_from_a[f])
    cluster_a = [seed_a] + by_distance_from_a[: motif_width - 1]

    far_candidates = [
        f for f in by_distance_from_a
        if dist_from_a[f] >= birth_separation and f not in cluster_a
    ]
    if not far_candidates:
        raise RuntimeError(
            f"no fresh node at undirected distance >= {birth_separation} from cluster A "
            f"(max available: {max(dist_from_a[f] for f in reachable_fresh)})"
        )
    seed_b = far_candidates[0]  # the closest one satisfying the separation
    dist_from_b = _undirected_distances(graph, seed_b)
    candidates_b = sorted(
        (f for f in fresh if f not in cluster_a and f != seed_b and f in dist_from_b),
        key=lambda f: dist_from_b[f],
    )
    cluster_b = [seed_b] + candidates_b[: motif_width - 1]
    realized_separation = dist_from_a[seed_b]

    generations_a = [cluster_a]
    generations_b = [cluster_b]
    membrane_a = set(cluster_a)
    membrane_b = set(cluster_b)
    external_time_a = np.zeros(n_generations)
    external_time_b = np.zeros(n_generations)
    capture_counts_a = np.zeros(n_generations, dtype=int)
    capture_counts_b = np.zeros(n_generations, dtype=int)
    contacts = {
        "living": 0,
        "wake_by_a": 0,
        "wake_by_b": 0,
        "first_living_gen": None,  # generation index of first direct body contact
        "first_wake_gen": None,    # generation index of first cross-wake capture
    }
    id_watermarks = np.zeros(n_generations, dtype=np.int64)
    worldtube_time_a = t
    worldtube_time_b = t
    background_time = t

    def advance_motif(generations, membrane_self, membrane_other, living_other, wake_key, gen_index):
        """One generation step for one motif; returns (captures, mean parent charge)."""
        nonlocal next_id
        previous = generations[-1]
        previous_set = set(previous)
        new_generation = []
        new_generation_set = set()
        parent_charges = []
        captures = 0

        # Tangential kick (preparation only, first kick_ticks generations):
        # snapshot the distance field from the partner's living membrane and
        # this motif's own distance to it. Retention of otherwise-valid
        # candidates is then constrained by kick_mode. Nothing here changes
        # how candidates are produced (the walk) or judged causally (the
        # antichain rule) -- only which of the already-valid ones the motif
        # keeps, and only during the burn window.
        kick_active = kick_mode != "none" and gen_index < kick_ticks
        dist_to_partner = None
        d_self = None
        if kick_active:
            dist_to_partner = _hops_at_time(graph, list(living_other), next_id)
            self_dists = [dist_to_partner[m] for m in previous if m in dist_to_partner]
            d_self = min(self_dists) if self_dists else None

        for _ in range(motif_width):
            if next_id >= max_nodes:
                raise RuntimeError(f"max_nodes ({max_nodes}) reached at generation {gen_index}")
            picks = rng.choice(len(previous), size=internal_parents, replace=False)
            chosen = [previous[i] for i in picks]
            captured_nodes = []
            attempts = 0
            while len(captured_nodes) < k - internal_parents and attempts < max_attempts:
                candidate = _local_walk_candidate(
                    graph, chosen[0], rng, walk_hops, charge=routing_charge
                )
                attempts += 1
                if candidate in chosen or candidate in previous_set or candidate in new_generation_set:
                    continue
                if kick_active and d_self is not None:
                    # None distance = unreachable from partner = maximally "away".
                    dc = dist_to_partner.get(candidate)
                    if kick_mode == "noinfall" and dc is not None and dc < d_self:
                        continue
                    if kick_mode == "iso" and dc != d_self:
                        continue
                candidate_ancestors = ancestors[candidate]
                independent = all(
                    not (candidate_ancestors >> p) & 1 and not (ancestors[p] >> candidate) & 1
                    for p in chosen
                )
                if independent:
                    chosen.append(candidate)
                    captured_nodes.append(candidate)
                    if candidate in living_other:
                        contacts["living"] += 1
                        if contacts["first_living_gen"] is None:
                            contacts["first_living_gen"] = gen_index
                    elif candidate in membrane_other:
                        contacts[wake_key] += 1
                        if contacts["first_wake_gen"] is None:
                            contacts["first_wake_gen"] = gen_index
            captures += len(captured_nodes)

            new_node = next_id
            next_id += 1
            graph.add_node(new_node)
            new_slot()
            new_ancestors = 0
            for p in chosen:
                graph.add_edge(p, new_node)
                new_ancestors |= ancestors[p] | (1 << p)
                charge[p] += 1
            ancestors[new_node] = new_ancestors
            new_generation.append(new_node)
            new_generation_set.add(new_node)
            parent_charges.extend(charge[p] for p in chosen)

            for captured in captured_nodes:
                current_gen[captured] += 1
                heapq.heappush(
                    heap,
                    (background_time + delay(charge[captured]), captured, current_gen[captured]),
                )

        generations.append(new_generation)
        membrane_self.update(new_generation)

        # Radiation: the retired generation re-enters the flux (TEI 6bis.2).
        for retired in previous:
            current_gen[retired] += 1
            heapq.heappush(
                heap,
                (background_time + delay(charge[retired]), retired, current_gen[retired]),
            )
        return captures, float(np.mean(parent_charges))

    for g in range(n_generations):
        living_b = set(generations_b[-1])
        captures_a, mean_charge_a = advance_motif(
            generations_a, membrane_a, membrane_b, living_b, "wake_by_a", g
        )
        capture_counts_a[g] = captures_a
        worldtube_time_a += delay(mean_charge_a)
        external_time_a[g] = worldtube_time_a

        living_a = set(generations_a[-1])
        captures_b, mean_charge_b = advance_motif(
            generations_b, membrane_b, membrane_a, living_a, "wake_by_b", g
        )
        capture_counts_b[g] = captures_b
        worldtube_time_b += delay(mean_charge_b)
        external_time_b[g] = worldtube_time_b

        for _ in range(background_ratio):
            if not heap or next_id >= max_nodes:
                break
            t2, trigger, gen = heapq.heappop(heap)
            if gen != current_gen[trigger]:
                continue
            background_time = t2
            fire_background_event(t2, trigger)

        # Observational only: snapshot of the id high-water mark at the end of
        # this tick. Node ids are creation-ordered and every edge points
        # old -> new, so the graph as it existed at the end of tick g is
        # exactly the subgraph induced on ids < id_watermarks[g] -- which lets
        # post-hoc metrology (recession, infall kinematics) reconstruct the
        # metric at any past moment without touching the dynamics.
        id_watermarks[g] = next_id

    info = {
        "realized_separation": realized_separation,
        "capture_counts_a": capture_counts_a,
        "capture_counts_b": capture_counts_b,
        "contact_living": contacts["living"],
        "contact_wake_by_a": contacts["wake_by_a"],  # A captured B's radiated wake: matter flowing B -> A
        "contact_wake_by_b": contacts["wake_by_b"],  # B captured A's radiated wake: matter flowing A -> B
        "first_living_gen": contacts["first_living_gen"],
        "first_wake_gen": contacts["first_wake_gen"],
        "external_time_a": external_time_a,
        "external_time_b": external_time_b,
        "id_watermarks": id_watermarks,
    }
    return graph, generations_a, generations_b, info


def _hops_at_time(graph, sources, watermark, targets=None):
    """Multi-source undirected BFS over the graph *as it existed* at `watermark`.

    Node ids are creation-ordered and every edge points old -> new, so the
    id-filtered subgraph (ids < watermark) is exactly the past state of the
    universe -- including its past metric: a shortcut created later cannot
    leak backward in time through this filter.

    With `targets`: returns the smallest hop distance from any source to any
    target (None if unreachable at that time). Without: returns the full
    distance dict from the sources.
    """
    sources = [s for s in sources if s < watermark]
    target_set = None if targets is None else {t for t in targets if t < watermark}
    distances = {s: 0 for s in sources}
    if target_set is not None and target_set & set(sources):
        return 0
    queue = deque(sources)
    while queue:
        u = queue.popleft()
        for v in list(graph.predecessors(u)) + list(graph.successors(u)):
            if v >= watermark or v in distances:
                continue
            distances[v] = distances[u] + 1
            if target_set is not None and v in target_set:
                return distances[v]
            queue.append(v)
    return None if target_set is not None else distances


def intertube_metrics(graph, generations_a, generations_b, generation, watermark, slack=1):
    """Instantaneous metric between the two living membranes, at a past moment.

    Returns `(distance, corridor_volume)` where `distance` is the undirected
    hop distance between the two motifs' generation-`generation` membranes in
    the graph as of `watermark`, and `corridor_volume` counts the nodes lying
    on near-geodesic paths between them (nodes u with
    d_A(u) + d_B(u) <= distance + slack) -- the causal volume "between" the
    bodies. `(None, None)` if the membranes are not mutually reachable at
    that time. Purely observational: the recession/expansion monitor.
    """
    from_a = _hops_at_time(graph, generations_a[generation], watermark)
    reachable_b = [b for b in generations_b[generation] if b in from_a]
    if not reachable_b:
        return None, None
    distance = min(from_a[b] for b in reachable_b)
    from_b = _hops_at_time(graph, generations_b[generation], watermark)
    corridor = sum(
        1 for node, da in from_a.items()
        if node in from_b and da + from_b[node] <= distance + slack
    )
    return distance, corridor


def wake_gap(graph, generations_from, generations_to, source_generation, target_generation, watermark):
    """The race between signal and expansion, at a past moment.

    Hop distance (in the graph as of `watermark`) from the target motif's
    generation-`target_generation` membrane to the nearest node of the causal
    wake of the source motif's generation `source_generation` (its
    descendants existing at that time). Tracking this against
    `target_generation - source_generation` shows directly whether the
    radiated signal is closing on the receding body (gap shrinks) or being
    outrun by the metric's growth (gap grows). None if no wake exists yet or
    it is unreachable.
    """
    root = generations_from[source_generation][0]
    wake = {w for w in nx.descendants(graph, root) if w < watermark}
    if not wake:
        return None
    return _hops_at_time(graph, generations_to[target_generation], watermark, targets=wake)


def worldtube_drift(graph, generations, gen, delta, watermark):
    """Proper drift: undirected hop distance a motif's membrane has moved over
    `delta` generations, measured in the graph as of `watermark`.

    Distance between the membrane at `gen` and the membrane at `gen - delta`
    -- how far the body's own neighbourhood has slid through the flux. Combined
    with the radial change (delta of the inter-tube distance from
    `intertube_metrics`), this separates displacement into "toward/away from
    partner" (radial) and "the rest" (tangential drift -- the lateral motion
    the angular-momentum kick is meant to induce and, more importantly, that
    depletion-drag inertia is meant to sustain after the burn). None if the two
    membranes are not mutually reachable at that time.
    """
    if gen - delta < 0:
        return None
    return _hops_at_time(
        graph, generations[gen], watermark, targets=generations[gen - delta]
    )


def first_contact_lag(graph, generations_from, generations_to, anchor, max_lag):
    """Causal distance between two worldtubes, in proper-time units.

    Smallest L <= max_lag such that some member of `generations_to[anchor + L]`
    is a causal descendant of `generations_from[anchor][0]` -- i.e. how many of
    the target's own generations elapse before the source's instructions can
    first reach it. Returns None if no contact within `max_lag` (causally
    disconnected at this horizon). This is the toy model's reading of TEI
    6bis.4's distance-regularity question: a *stable* lag(anchor) profile is a
    stable Earth-Mars distance.
    """
    reachable = nx.descendants(graph, generations_from[anchor][0])
    horizon = min(anchor + max_lag, len(generations_to) - 1)
    for lag in range(0, horizon - anchor + 1):
        if any(member in reachable for member in generations_to[anchor + lag]):
            return lag
    return None


def generate_three_motif_graph(
    n_generations,
    k,
    motif_width,
    warmup_events=20000,
    walk_hops=3,
    background_ratio=60,
    internal_parents=2,
    test_mode="plain",
    seed_ticks=100,
    charge_biased_routing=True,
    seed=None,
    max_nodes=2_000_000,
):
    """Three-body inertia probe: does a transverse ("tangential") coordinate exist?

    The two-body sector (`generate_two_motif_graph`) proved that with *two*
    bodies there is only one distance -- a line, hence a strictly 1D relation
    -- so a lateral/transverse axis literally cannot exist and "angular
    momentum" cannot be tested there (that is why the kick test could only
    ever produce silence or radial merger). A transverse coordinate needs a
    *third* body: with A, B, C the two reference bodies A and B fix a baseline,
    and C's angle off that baseline (by the graph law of cosines on the three
    pairwise hop distances, `triangle_angle`) is a genuine 2D transverse
    position that is scale-invariant -- common recession of all three cancels
    out of the angle, so it isolates lateral motion from expansion.

    A and B are ordinary closed motifs (identical physics to
    `generate_braided_motif_graph`: braiding, consumption, radiation, optional
    refractive routing) advanced with the plain rule. C is the *test body*,
    advanced with a `test_mode` that probes whether the substrate carries a
    conserved tangential rate (inertia):

    - `test_mode="plain"`: C is an ordinary motif too -- the null.
    - `test_mode="correlated"`: A⊕B braiding. Each strand starts its capture
      walk from that strand's *previous* intake node (an inherited heading =
      wake dipole), so a lateral disposition, once present, is carried forward
      by the metabolism itself. No burn, no partner reference.
    - `test_mode="correlated_seed"`: correlated braiding *plus* a burn window
      (first `seed_ticks` generations) that biases which valid captures C
      keeps toward the B-side of the A--B baseline -- a prepared tangential
      "kick", after which the partners are never referenced again. This is the
      physical initial condition whose *persistence* past the burn is the
      emergent-inertia question.
    - `test_mode="forced"`: the burn's tangential bias is applied at *every*
      generation, not just the seed window -- a non-physical instrument
      control that continuously advects C sideways. It must move the angle
      ballistically; if it does not, the observable itself is blind. (It is
      not a law, it is the ruler's calibration.)

    Only the *retention* of already-valid, already-antichain-checked candidates
    is constrained (and, for correlated modes, the walk's *start*); the delay
    law, refractive routing, and the causal antichain rule are never touched.
    So `test_mode="plain"` is the untouched three-motif control.

    Birth: three fresh (charge-0) clusters chosen to form a roughly
    equilateral triangle (each seed maximizes `min(dA, dB, dAB) - |dA - dB|/2`
    over the fresh warmup nodes), so the transverse angle at birth is
    non-degenerate rather than a collapsed sliver.

    Returns `(graph, generations, info)` where `generations` is a dict
    `{"A": [...], "B": [...], "C": [...]}` of per-generation membranes and
    `info` carries `id_watermarks` (creation-order high-water mark per tick,
    for past-metric reconstruction), `capture_counts_c` (C's metabolism per
    generation), and `birth_sides` (the three birth distances dA, dB, dAB).
    """
    if internal_parents < 2:
        raise ValueError("braiding requires internal_parents >= 2")
    if k <= internal_parents:
        raise ValueError("k must be > internal_parents (need at least one capture slot)")
    if motif_width < 2:
        raise ValueError("motif_width must be >= 2")
    if test_mode not in ("plain", "correlated", "correlated_seed", "forced"):
        raise ValueError(
            "test_mode must be 'plain', 'correlated', 'correlated_seed', or 'forced'"
        )

    rng = np.random.default_rng(seed)
    graph = nx.DiGraph()
    n0 = k
    graph.add_nodes_from(range(n0))
    charge = [0] * n0
    current_gen = [0] * n0
    ancestors = [0] * n0
    max_attempts = max(50, k * 20)

    def delay(load):
        return 1.0 + load

    def new_slot():
        charge.append(0)
        current_gen.append(0)
        ancestors.append(0)

    heap = []
    next_id = n0
    for node in range(n0):
        heapq.heappush(heap, (1.0, node, 0))
    routing_charge = charge if charge_biased_routing else None
    background_time = 0.0

    def fire_background_event(t, trigger):
        nonlocal next_id
        chosen = _pick_independent_parents(
            graph, trigger, k, rng, walk_hops, ancestors, max_attempts, charge=routing_charge
        )
        new_node = next_id
        next_id += 1
        graph.add_node(new_node)
        new_slot()
        new_ancestors = 0
        for p in chosen:
            graph.add_edge(p, new_node)
            new_ancestors |= ancestors[p] | (1 << p)
            charge[p] += 1
            current_gen[p] += 1
            heapq.heappush(heap, (t + delay(charge[p]), p, current_gen[p]))
        ancestors[new_node] = new_ancestors
        heapq.heappush(heap, (t + delay(0), new_node, current_gen[new_node]))

    # --- Phase 1: warmup ---
    t = 0.0
    for _ in range(warmup_events):
        if next_id >= max_nodes:
            raise RuntimeError(f"max_nodes ({max_nodes}) reached during warmup")
        t, trigger, gen = heapq.heappop(heap)
        if gen != current_gen[trigger]:
            continue
        fire_background_event(t, trigger)
    background_time = t
    warm_n = next_id

    # --- Phase 2: seed three near-equilateral clusters ---
    fresh = [node for node in range(next_id) if charge[node] == 0]
    if len(fresh) < 3 * motif_width:
        raise RuntimeError("not enough fresh nodes after warmup to seed three motifs")

    def warm_distances(src):
        return _hops_at_time(graph, [src], warm_n)

    seed_a = int(rng.choice(fresh))
    dist_a = warm_distances(seed_a)
    seed_b = max((f for f in fresh if f in dist_a and f != seed_a), key=lambda f: dist_a[f])
    dist_b = warm_distances(seed_b)
    baseline = dist_a.get(seed_b, 1)

    def triangle_score(f):
        if f not in dist_a or f not in dist_b:
            return -1
        da, db = dist_a[f], dist_b[f]
        return min(da, db, baseline) - 0.5 * abs(da - db)

    seed_c = max(
        (f for f in fresh if f not in (seed_a, seed_b)), key=triangle_score
    )
    dist_c = warm_distances(seed_c)

    def cluster(seed_node, dist, excluded):
        others = sorted(
            (f for f in fresh if f != seed_node and f in dist and f not in excluded),
            key=lambda f: dist[f],
        )
        return [seed_node] + others[: motif_width - 1]

    cluster_a = cluster(seed_a, dist_a, set())
    cluster_b = cluster(seed_b, dist_b, set(cluster_a))
    cluster_c = cluster(seed_c, dist_c, set(cluster_a) | set(cluster_b))

    generations = {"A": [cluster_a], "B": [cluster_b], "C": [cluster_c]}
    headings = {node: None for node in cluster_c}  # per-strand last intake (C only)
    id_watermarks = np.zeros(n_generations, dtype=np.int64)
    capture_counts_c = np.zeros(n_generations, dtype=int)

    def bounded_hops(source, targets, radius):
        """Undirected hop distance from `source` to the nearest `targets` node,
        capped at `radius` (returns radius + 1 if none is within radius)."""
        target_set = set(targets)
        distances = {source: 0}
        queue = deque([source])
        while queue:
            u = queue.popleft()
            if distances[u] >= radius:
                continue
            for v in list(graph.predecessors(u)) + list(graph.successors(u)):
                if v in distances:
                    continue
                distances[v] = distances[u] + 1
                if v in target_set:
                    return distances[v]
                queue.append(v)
        return radius + 1

    def advance_motif(key, correlated, tangential):
        """One generation for motif `key`. `correlated` starts each strand's
        walk from its inherited heading; `tangential` biases retained captures
        toward the B-side of the A--B baseline (the prepared / forced kick).
        Returns the number of captures."""
        nonlocal next_id, headings
        previous = generations[key][-1]
        previous_set = set(previous)
        new_generation = []
        new_generation_set = set()
        new_headings = {}
        captures = 0
        if tangential:
            membrane_a = generations["A"][-1]
            membrane_b = generations["B"][-1]
        for strand in range(motif_width):
            if next_id >= max_nodes:
                raise RuntimeError(f"max_nodes ({max_nodes}) reached")
            anchor = previous[strand % len(previous)]
            if correlated and headings.get(anchor) is not None and headings[anchor] in graph:
                start = headings[anchor]
            else:
                start = previous[rng.integers(0, len(previous))]
            picks = rng.choice(len(previous), size=internal_parents, replace=False)
            chosen = [previous[i] for i in picks]
            captured_nodes = []
            attempts = 0
            while len(captured_nodes) < k - internal_parents and attempts < max_attempts:
                candidate = _local_walk_candidate(
                    graph, start, rng, walk_hops, charge=routing_charge
                )
                attempts += 1
                if (
                    candidate in chosen
                    or candidate in previous_set
                    or candidate in new_generation_set
                    or candidate in captured_nodes
                ):
                    continue
                candidate_ancestors = ancestors[candidate]
                if not all(
                    not (candidate_ancestors >> p) & 1 and not (ancestors[p] >> candidate) & 1
                    for p in chosen
                ):
                    continue
                if tangential:
                    # Prefer intake nearer B than A -> swing C toward the B side
                    # of the baseline (a lateral push). Skip an A-side candidate
                    # once, but fall back rather than starve the metabolism.
                    d_to_a = bounded_hops(candidate, membrane_a, walk_hops + 4)
                    d_to_b = bounded_hops(candidate, membrane_b, walk_hops + 4)
                    if d_to_b > d_to_a and attempts < max_attempts - 2 and not captured_nodes:
                        continue
                chosen.append(candidate)
                captured_nodes.append(candidate)
            new_node = next_id
            next_id += 1
            graph.add_node(new_node)
            new_slot()
            new_ancestors = 0
            for p in chosen:
                graph.add_edge(p, new_node)
                new_ancestors |= ancestors[p] | (1 << p)
                charge[p] += 1
            ancestors[new_node] = new_ancestors
            new_generation.append(new_node)
            new_generation_set.add(new_node)
            new_headings[new_node] = captured_nodes[0] if captured_nodes else headings.get(anchor)
            captures += len(captured_nodes)
            for captured in captured_nodes:
                current_gen[captured] += 1
                heapq.heappush(
                    heap, (background_time + delay(charge[captured]), captured, current_gen[captured])
                )
        generations[key].append(new_generation)
        # Radiation: the retired generation re-enters the flux (TEI 6bis.2).
        for retired in previous:
            current_gen[retired] += 1
            heapq.heappush(
                heap, (background_time + delay(charge[retired]), retired, current_gen[retired])
            )
        if key == "C":
            headings = new_headings
        return captures

    for g in range(n_generations):
        advance_motif("A", correlated=False, tangential=False)
        advance_motif("B", correlated=False, tangential=False)
        correlated_c = test_mode in ("correlated", "correlated_seed")
        tangential_c = test_mode == "forced" or (
            test_mode == "correlated_seed" and g < seed_ticks
        )
        capture_counts_c[g] = advance_motif("C", correlated_c, tangential_c)

        for _ in range(background_ratio):
            if not heap or next_id >= max_nodes:
                break
            t2, trigger, gen = heapq.heappop(heap)
            if gen != current_gen[trigger]:
                continue
            background_time = t2
            fire_background_event(t2, trigger)

        id_watermarks[g] = next_id

    info = {
        "id_watermarks": id_watermarks,
        "capture_counts_c": capture_counts_c,
        "birth_sides": (dist_a.get(seed_b), dist_a.get(seed_c), dist_b.get(seed_c)),
    }
    return graph, generations, info


def triangle_angle(graph, generations, watermarks, generation):
    """Transverse angle of test body C off the A--B baseline (radians).

    Uses the graph law of cosines on the three pairwise undirected hop
    distances between the motif membranes, measured in the graph *as it
    existed* at `watermarks[generation]` (past-metric reconstruction via id
    order, see `_hops_at_time`). The angle is the one at vertex A in triangle
    A-B-C, so common recession of all three bodies cancels and only C's
    lateral position survives. Returns None if the three membranes are not
    mutually reachable, or the triangle degenerates (a zero side at A).
    """
    watermark = int(watermarks[min(generation, len(watermarks) - 1)])

    def side(key_1, key_2):
        return _hops_at_time(
            graph, generations[key_1][generation], watermark,
            targets=generations[key_2][generation],
        )

    ab = side("A", "B")
    ac = side("A", "C")
    bc = side("B", "C")
    if None in (ab, ac, bc) or ab == 0 or ac == 0:
        return None
    cos_a = (ab * ab + ac * ac - bc * bc) / (2 * ab * ac)
    return math.acos(max(-1.0, min(1.0, cos_a)))


def observer_growth_curve(graph, worldline):
    """Number of distinct nodes in the Observer's causal future, indexed by its own tick count.

    `worldline[0]` is "Observer zero"; the causal future of the *worldline as
    a whole* is exactly `nx.descendants(graph, worldline[0])`, since every
    later self is by construction a descendant of the first. At tick t
    (1-indexed), the count is how many of those descendants already existed
    at the moment `worldline[t]` was created (using node id order, since ids
    are assigned in creation order throughout this module).

    NOTE: this cumulative-cone measure has the worldline's own chain (slope 1)
    baked into its floor and mixes the timelike "memory" direction with the
    transverse "spatial" one. The 50-seed study in
    math/event_driven_shadow_analysis.md shows its exponent depends on the
    arbitrary `background_ratio` knob, so it does not measure an intrinsic
    dimension. `interval_width` (below) is the better observable: it isolates
    the transverse/spacelike direction and its exponent is, unlike this one,
    invariant under `background_ratio`.
    """
    descendant_ids = sorted(nx.descendants(graph, worldline[0]))
    return np.array([bisect.bisect_right(descendant_ids, node) for node in worldline[1:]])


def max_antichain_size(graph):
    """Exact size of the largest antichain of a DAG (its "width"), via Dilworth.

    Dilworth's theorem: the maximum antichain equals the minimum number of
    chains needed to cover the poset. For a DAG, that minimum chain cover
    equals `n - (maximum matching in the bipartite reachability graph)`
    (Fulkerson), where the reachability graph has an edge u->v' whenever v is
    reachable from u (the transitive closure). Exact, but O(transitive
    closure + bipartite matching) -- fine for the modest causal intervals used
    here, not for the whole graph at large N.

    A cheap proxy (the largest longest-path-depth level set, which is always a
    valid antichain) was tried first and REJECTED: it underestimates the true
    width by 3-7x and worsens with interval size (see
    math/event_driven_shadow_analysis.md). Hence the exact computation here.
    """
    closure = nx.transitive_closure_dag(graph)
    nodes = list(closure.nodes())
    bip = nx.Graph()
    left = [("L", u) for u in nodes]
    bip.add_nodes_from(left, bipartite=0)
    bip.add_nodes_from([("R", u) for u in nodes], bipartite=1)
    for u, v in closure.edges():
        bip.add_edge(("L", u), ("R", v))
    matching = nx.bipartite.maximum_matching(bip, top_nodes=left)
    matched = sum(1 for key in matching if key[0] == "L")
    return len(nodes) - matched


def causal_interval(graph, x, y):
    """Node set of the Alexandrov interval I[x, y] = {z : x <= z <= y}.

    That is: descendants of x (inclusive) that are also ancestors of y
    (inclusive). Empty/degenerate unless y is reachable from x.
    """
    return (nx.descendants(graph, x) | {x}) & (nx.ancestors(graph, y) | {y})


def interval_width(graph, x, y):
    """Transverse spatial width of the causal interval I[x, y]: its max antichain.

    For a causal set faithfully embeddable in `d`-dimensional Minkowski, an
    interval of height (longest chain) `T` has width ~ `T**(d-1)`, so measuring
    width vs `T` estimates the emergent *spatial* dimension `d-1` directly --
    without any embedding, and without the timelike worldline chain
    contaminating the count (the chain is the interval's height, not its
    width). This is the observable argued for in
    math/event_driven_shadow_analysis.md; see that file for what it does and
    does not establish for the event-driven generator.
    """
    interval = causal_interval(graph, x, y)
    if len(interval) < 2:
        return 0
    return max_antichain_size(graph.subgraph(interval))


def causal_future_mask(points, origin_index):
    """Boolean mask of points causally following `points[origin_index]`.

    p precedes q iff q lies within p's future light cone: dt > 0 and dt > |dx|.
    """
    origin = points[origin_index]
    dt = points[:, 0] - origin[0]
    dx = np.linalg.norm(points[:, 1:] - origin[1:], axis=1)
    return dt > dx


def reachable_within_hops(graph, origin, max_hops):
    """Cumulative count of nodes reachable from `origin` within each hop count 1..max_hops.

    Hop count is the *shortest*-path distance. In a graph with no embedded
    metric this is a convenient default, but it is not the only defensible
    notion of causal depth -- see `reachable_within_depth` for the
    longest-path alternative and why it matters for `generate_tei_shadow_graph`.
    """
    lengths = nx.single_source_shortest_path_length(graph, origin, cutoff=max_hops)
    counts = np.zeros(max_hops, dtype=int)
    for hop in lengths.values():
        if hop > 0:
            counts[hop - 1:] += 1
    return counts


def longest_path_depths(graph, origin):
    """Longest directed path length (edge count) from `origin` to each of its descendants.

    If every edge is itself a relay delay -- a unit of sequential computation
    that must complete before its target event can occur -- then an event is
    only reached once *every* instruction chain leading to it has finished,
    including the slowest one. The shortest path is a classical geometric
    shortcut with no principled meaning in a purely relational graph that has
    no embedded metric to justify preferring it; the longest path from the
    origin is the "proper time" analogue used here instead.

    Computed by dynamic programming over a topological order of the subgraph
    reachable from `origin` (well-defined because the graph is a DAG).
    """
    reachable = nx.descendants(graph, origin)
    reachable.add(origin)
    subgraph = graph.subgraph(reachable)
    depth = {origin: 0}
    for node in nx.topological_sort(subgraph):
        if node == origin:
            continue
        depth[node] = max(depth[parent] for parent in subgraph.predecessors(node)) + 1
    return depth


def reachable_within_depth(graph, origin, max_depth):
    """Cumulative count of nodes at longest-path depth <= d, for d in 1..max_depth."""
    depths = longest_path_depths(graph, origin)
    counts = np.zeros(max_depth, dtype=int)
    for depth in depths.values():
        if 0 < depth <= max_depth:
            counts[depth - 1:] += 1
    return counts


def reachable_within_ticks(points, origin_index, n_ticks, window_frac=0.3):
    """Cumulative count of causal-future points within each of `n_ticks` equal time slices.

    `window_frac` restricts the analysis to the first fraction of the origin's
    causal future: near the far edge of the unit cube, the light cone is
    truncated by the spatial boundary, which biases the measured growth exponent
    downward. Keeping to the early, unobstructed part of the cone avoids this
    finite-volume artifact.
    """
    origin_t = points[origin_index, 0]
    future = causal_future_mask(points, origin_index)
    dt = points[:, 0] - origin_t
    max_dt = dt[future].max() if future.any() else 0.0
    cutoff = max_dt * window_frac
    counts = np.zeros(n_ticks, dtype=int)
    for tick in range(1, n_ticks + 1):
        threshold = cutoff * tick / n_ticks
        counts[tick - 1] = int(np.sum(future & (dt <= threshold)))
    return counts


def fit_growth_exponent(counts):
    """Log-log linear fit of reachable count vs tick index; returns the estimated exponent."""
    ticks = np.arange(1, len(counts) + 1)
    valid = counts > 0
    if valid.sum() < 2:
        return float("nan")
    slope, _ = np.polyfit(np.log(ticks[valid]), np.log(counts[valid]), 1)
    return slope


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["random-dag", "sprinkling", "tei-shadow", "event-shadow", "braided-motif"], required=True)
    parser.add_argument("--dim", type=int, default=4, help="Embedding dimension (sprinkling mode)")
    parser.add_argument("--N", type=int, default=100000, help="Number of nodes/points")
    parser.add_argument("--out-degree", type=int, default=4, help="Out-degree (random-dag mode)")
    parser.add_argument("--k", type=int, default=3, help="Max valence / antichain size (tei-shadow, event-shadow modes)")
    parser.add_argument("--valence", type=int, default=None, help="Parent-selection budget per node (tei-shadow mode, default: k)")
    parser.add_argument("--ticks", type=int, default=20, help="Number of tick buckets to measure (random-dag/sprinkling/tei-shadow modes)")
    parser.add_argument(
        "--depth-metric",
        choices=["shortest", "longest"],
        default="shortest",
        help="Notion of causal depth for random-dag/tei-shadow modes (see reachable_within_hops vs reachable_within_depth)",
    )
    parser.add_argument("--window-frac", type=float, default=0.3, help="Analysis window fraction (sprinkling mode)")
    parser.add_argument("--observer-ticks", type=int, default=300, help="Observer's own tick budget (event-shadow mode)")
    parser.add_argument("--warmup-events", type=int, default=3000, help="Background-only warmup events before electing the Observer (event-shadow mode)")
    parser.add_argument("--walk-hops", type=int, default=8, help="Local random-walk radius for candidate selection (event-shadow mode)")
    parser.add_argument("--background-ratio", type=int, default=50, help="Background events per Observer tick (event-shadow mode)")
    parser.add_argument(
        "--charge-biased-routing",
        action="store_true",
        help="Refractive routing: walk steps land on a neighbor with probability ~ 1+charge, the same law as the delay (event-shadow, braided-motif modes)",
    )
    parser.add_argument("--motif-width", type=int, default=4, help="W, the motif's mass: nodes per generation (braided-motif mode)")
    parser.add_argument("--internal-parents", type=int, default=2, help="Internal braid parents per node, structural choice: 2 main, k-1 control (braided-motif mode)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=None, help="Path to save counts as .npz")
    args = parser.parse_args()

    if args.mode in ("random-dag", "tei-shadow"):
        if args.mode == "random-dag":
            graph = generate_random_dag(args.N, args.out_degree, seed=args.seed)
        else:
            graph = generate_tei_shadow_graph(args.N, args.k, valence=args.valence, seed=args.seed)
        if args.depth_metric == "shortest":
            counts = reachable_within_hops(graph, origin=0, max_hops=args.ticks)
        else:
            counts = reachable_within_depth(graph, origin=0, max_depth=args.ticks)
    elif args.mode == "event-shadow":
        graph, worldline, external_time = generate_event_driven_shadow_graph(
            args.observer_ticks,
            args.k,
            warmup_events=args.warmup_events,
            walk_hops=args.walk_hops,
            background_ratio=args.background_ratio,
            charge_biased_routing=args.charge_biased_routing,
            seed=args.seed,
        )
        counts = observer_growth_curve(graph, worldline)
    elif args.mode == "braided-motif":
        graph, generations, external_time, capture_counts = generate_braided_motif_graph(
            args.observer_ticks,
            args.k,
            args.motif_width,
            warmup_events=args.warmup_events,
            walk_hops=args.walk_hops,
            background_ratio=args.background_ratio,
            internal_parents=args.internal_parents,
            charge_biased_routing=args.charge_biased_routing,
            seed=args.seed,
        )
        # Growth curve of the motif's causal future, sampled at each
        # generation's first member (ids are creation-ordered).
        counts = observer_growth_curve(graph, [gen[0] for gen in generations])
    else:
        points = sprinkle_minkowski(args.N, args.dim, seed=args.seed)
        origin_index = int(np.argmin(points[:, 0]))
        counts = reachable_within_ticks(points, origin_index, args.ticks, window_frac=args.window_frac)

    exponent = fit_growth_exponent(counts)
    print(f"mode={args.mode} estimated growth exponent = {exponent:.3f}")
    print(f"counts per tick: {counts.tolist()}")

    if args.mode == "event-shadow":
        print(f"external_time (descriptive) per tick: {external_time.round(2).tolist()}")
    elif args.mode == "braided-motif":
        print(f"mean capture rate: {capture_counts.mean():.2f}/generation "
              f"(max possible {args.motif_width * (args.k - args.internal_parents)})")

    if args.out:
        if args.mode == "event-shadow":
            np.savez(args.out, counts=counts, exponent=exponent, external_time=external_time)
        elif args.mode == "braided-motif":
            np.savez(args.out, counts=counts, exponent=exponent,
                     external_time=external_time, capture_counts=capture_counts)
        else:
            np.savez(args.out, counts=counts, exponent=exponent)


if __name__ == "__main__":
    main()
