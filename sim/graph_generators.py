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

Neither `generate_random_dag` nor `sprinkle_minkowski` explains why an exponent
of 3 (rather than 2 or 4) should emerge from purely local, non-embedded
coupling rules -- that is the actual open question (TEI 7.5). This module is
instrumentation for exploring it, not a claimed solution to it.
"""

import argparse
import bisect
import heapq

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
      the run (returned as `capture_counts`), never a decreed one.

    Entropy is the generational rotation itself: once generation g+1 exists,
    the motif never re-executes over generation g again. Old members are not
    deleted (the DAG is append-only) -- they simply return to being ordinary
    background, their pending queue events still fire. The motif's identity is
    the unbroken succession of generations; nothing stores it (present encodes
    present+1, per the no-memory rule).

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
            attempts = 0
            captured = 0
            while captured < k - internal_parents and attempts < max_attempts:
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
                    captured += 1
            captures += captured

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

        generations.append(new_generation)
        capture_counts[g] = captures
        worldtube_time += delay(float(np.mean(parent_charges)))
        external_time[g] = worldtube_time

        for _ in range(background_ratio):
            if not heap or next_id >= max_nodes:
                break
            t2, trigger, gen = heapq.heappop(heap)
            if gen != current_gen[trigger]:
                continue
            fire_background_event(t2, trigger)

    return graph, generations, external_time, capture_counts


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
