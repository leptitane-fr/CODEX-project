import networkx as nx
import numpy as np
import pytest

from sim.graph_generators import (
    causal_future_mask,
    causal_interval,
    first_contact_lag,
    fit_growth_exponent,
    generate_braided_motif_graph,
    generate_event_driven_shadow_graph,
    generate_random_dag,
    generate_two_motif_graph,
    generate_tei_shadow_graph,
    interval_width,
    longest_path_depths,
    max_antichain_size,
    observer_growth_curve,
    reachable_within_depth,
    reachable_within_hops,
    reachable_within_ticks,
    sprinkle_minkowski,
)


def test_causal_future_mask_classifies_timelike_and_spacelike_points():
    points = np.array(
        [
            [0.0, 0.0],  # origin
            [1.0, 0.0],  # directly ahead in time: timelike future
            [1.0, 2.0],  # outside the light cone: spacelike
            [-1.0, 0.0],  # behind in time: past, not future
        ]
    )
    mask = causal_future_mask(points, origin_index=0)
    assert mask.tolist() == [False, True, False, False]


def test_fit_growth_exponent_recovers_exact_power_law():
    ticks = np.arange(1, 11)
    counts = ticks**3
    exponent = fit_growth_exponent(counts)
    assert exponent == pytest.approx(3.0, abs=1e-6)


@pytest.mark.parametrize("dim", [2, 3, 4])
def test_sprinkling_growth_exponent_matches_embedding_dimension(dim):
    points = sprinkle_minkowski(100_000, dim, seed=42)
    origin_index = int(np.argmin(points[:, 0]))
    counts = reachable_within_ticks(points, origin_index, n_ticks=20)
    exponent = fit_growth_exponent(counts)
    assert exponent == pytest.approx(dim, abs=0.6)


def test_random_dag_reachable_count_is_monotonic_and_saturates_fast():
    graph = generate_random_dag(5000, out_degree=4, seed=42)
    counts = reachable_within_hops(graph, origin=0, max_hops=10)
    assert np.all(np.diff(counts) >= 0)
    # Contrast case for the polynomial growth above: a generic random DAG with no
    # embedding reaches most of the graph within a handful of hops.
    assert counts[-1] > 0.9 * 5000


def test_tei_shadow_graph_rejects_too_few_nodes():
    with pytest.raises(ValueError):
        generate_tei_shadow_graph(n_nodes=2, k=3, seed=0)


@pytest.mark.parametrize("k", [2, 3, 4])
def test_tei_shadow_graph_is_acyclic(k):
    graph = generate_tei_shadow_graph(n_nodes=800, k=k, seed=7)
    assert nx.is_directed_acyclic_graph(graph)


@pytest.mark.parametrize("k", [2, 3, 4])
def test_tei_shadow_graph_respects_valence_bound(k):
    # In-degree is bounded by k (at most k parents chosen per node); out-degree
    # is bounded by `valence` (default k: each node can be picked as a parent
    # at most k times before it drops out of the front).
    graph = generate_tei_shadow_graph(n_nodes=800, k=k, seed=7)
    assert all(in_degree <= k for _, in_degree in graph.in_degree())
    assert all(out_degree <= k for _, out_degree in graph.out_degree())


@pytest.mark.parametrize("k", [2, 3, 4])
def test_tei_shadow_graph_respects_causal_shadow_rule(k):
    """The core correctness property: no two direct parents of any node may be
    causally related, i.e. connecting to both would create a redundant
    shortcut past a transitive-reduction relay. Checked independently of the
    generator's internal bitmask bookkeeping, via plain graph path-finding.
    """
    graph = generate_tei_shadow_graph(n_nodes=800, k=k, seed=7)
    for node in graph.nodes:
        parents = list(graph.predecessors(node))
        for i in range(len(parents)):
            for j in range(i + 1, len(parents)):
                a, b = parents[i], parents[j]
                assert not nx.has_path(graph, a, b)
                assert not nx.has_path(graph, b, a)


def test_tei_shadow_graph_reachable_count_is_monotonic():
    graph = generate_tei_shadow_graph(n_nodes=20_000, k=3, seed=42)
    counts = reachable_within_hops(graph, origin=0, max_hops=30)
    assert np.all(np.diff(counts) >= 0)


def test_longest_path_depths_prefers_longer_chains_over_shortcuts():
    # 0 -> 2 directly, and also 0 -> 1 -> 2: the shortest path to 2 is 1 hop,
    # but the longest directed path from 0 is 2 hops (via node 1).
    graph = nx.DiGraph([(0, 1), (1, 2), (0, 2)])
    depths = longest_path_depths(graph, origin=0)
    assert depths == {0: 0, 1: 1, 2: 2}


def test_reachable_within_depth_uses_longest_path():
    graph = nx.DiGraph([(0, 1), (1, 2), (0, 2)])
    counts = reachable_within_depth(graph, origin=0, max_depth=3)
    # depth 1: only node 1 has been reached; depth >= 2: nodes 1 and 2.
    assert counts.tolist() == [1, 2, 2]


@pytest.mark.parametrize("k", [2, 3, 4])
def test_tei_shadow_graph_reachable_count_is_monotonic_by_longest_path(k):
    graph = generate_tei_shadow_graph(n_nodes=20_000, k=k, seed=42)
    counts = reachable_within_depth(graph, origin=0, max_depth=100)
    assert np.all(np.diff(counts) >= 0)


def _small_event_driven_graph(k, seed=7):
    return generate_event_driven_shadow_graph(
        n_ticks_observer=50,
        k=k,
        warmup_events=300,
        walk_hops=5,
        background_ratio=10,
        seed=seed,
    )


@pytest.mark.parametrize("k", [2, 3, 4])
def test_event_driven_shadow_graph_is_acyclic(k):
    graph, worldline, external_time = _small_event_driven_graph(k)
    assert nx.is_directed_acyclic_graph(graph)


@pytest.mark.parametrize("k", [2, 3, 4])
def test_event_driven_shadow_graph_respects_causal_shadow_rule(k):
    """Same correctness property as the synchronous generator, checked the same
    way (independent path-finding, not the generator's own bitmask bookkeeping):
    no two direct parents of any node may be causally related.
    """
    graph, worldline, external_time = _small_event_driven_graph(k)
    for node in graph.nodes:
        parents = list(graph.predecessors(node))
        for i in range(len(parents)):
            for j in range(i + 1, len(parents)):
                a, b = parents[i], parents[j]
                assert not nx.has_path(graph, a, b)
                assert not nx.has_path(graph, b, a)


@pytest.mark.parametrize("k", [2, 3, 4])
def test_event_driven_shadow_graph_worldline_is_a_self_continuing_chain(k):
    """Each of the Observer's own selves must be a direct parent of its
    successor -- the worldline is a genuine chain in the graph, not just a
    list of unrelated node ids.
    """
    graph, worldline, external_time = _small_event_driven_graph(k)
    assert len(worldline) == 51  # n_ticks_observer + 1
    for previous_self, next_self in zip(worldline, worldline[1:]):
        assert graph.has_edge(previous_self, next_self)


@pytest.mark.parametrize("k", [2, 3, 4])
def test_observer_growth_curve_is_monotonic_and_at_least_the_chain_itself(k):
    graph, worldline, external_time = _small_event_driven_graph(k)
    counts = observer_growth_curve(graph, worldline)
    assert len(counts) == 50
    assert np.all(np.diff(counts) >= 0)
    # The worldline chain alone guarantees at least tick-many distinct
    # descendants; background branching can only add to that.
    assert np.all(counts >= np.arange(1, 51))


def test_event_driven_shadow_graph_external_time_is_monotonic_and_descriptive():
    graph, worldline, external_time = _small_event_driven_graph(k=3)
    assert len(external_time) == 50
    assert np.all(np.diff(external_time) > 0)


def test_event_driven_shadow_graph_raises_when_max_nodes_too_small():
    with pytest.raises(RuntimeError):
        generate_event_driven_shadow_graph(
            n_ticks_observer=50, k=3, warmup_events=300, seed=7, max_nodes=50
        )


@pytest.mark.parametrize("k", [2, 3])
def test_charge_biased_routing_preserves_structural_invariants(k):
    """The refractive routing changes only the walk's step distribution; the
    causal-shadow rule and worldline structure must be untouched by it."""
    graph, worldline, external_time = generate_event_driven_shadow_graph(
        n_ticks_observer=50, k=k, warmup_events=300, walk_hops=5,
        background_ratio=10, charge_biased_routing=True, seed=7,
    )
    assert nx.is_directed_acyclic_graph(graph)
    for previous_self, next_self in zip(worldline, worldline[1:]):
        assert graph.has_edge(previous_self, next_self)
    for node in graph.nodes:
        parents = list(graph.predecessors(node))
        for i in range(len(parents)):
            for j in range(i + 1, len(parents)):
                a, b = parents[i], parents[j]
                assert not nx.has_path(graph, a, b)
                assert not nx.has_path(graph, b, a)


def test_charge_biased_routing_actually_changes_the_graph():
    # Same seed, only the routing law differs: the two runs must diverge
    # (otherwise the flag is dead code).
    g_blind, wl_blind, _ = generate_event_driven_shadow_graph(
        n_ticks_observer=50, k=3, warmup_events=300, walk_hops=5,
        background_ratio=10, charge_biased_routing=False, seed=7,
    )
    g_bias, wl_bias, _ = generate_event_driven_shadow_graph(
        n_ticks_observer=50, k=3, warmup_events=300, walk_hops=5,
        background_ratio=10, charge_biased_routing=True, seed=7,
    )
    assert set(g_blind.edges()) != set(g_bias.edges())


def test_max_antichain_size_on_a_pure_chain_is_one():
    chain = nx.DiGraph([(0, 1), (1, 2), (2, 3), (3, 4)])
    assert max_antichain_size(chain) == 1


def test_max_antichain_size_on_a_pure_antichain_is_n():
    antichain = nx.DiGraph()
    antichain.add_nodes_from(range(5))
    assert max_antichain_size(antichain) == 5


def test_max_antichain_size_on_a_diamond():
    # 0 -> {1, 2} -> 3 : the largest antichain is {1, 2}.
    diamond = nx.DiGraph([(0, 1), (0, 2), (1, 3), (2, 3)])
    assert max_antichain_size(diamond) == 2


def test_max_antichain_size_counts_only_mutually_incomparable_elements():
    # 0 -> 1 -> 2, plus an isolated pair 3, 4. The largest antichain mixes one
    # element from the chain with the two isolated ones: e.g. {2, 3, 4} (all
    # mutually incomparable) -> size 3, not the naive "levels" answer.
    graph = nx.DiGraph([(0, 1), (1, 2)])
    graph.add_nodes_from([3, 4])
    assert max_antichain_size(graph) == 3


def test_causal_interval_is_the_diamond_between_endpoints():
    # 0 -> 1 -> 3 and 0 -> 2 -> 3, plus 4 outside the interval (not below 3).
    graph = nx.DiGraph([(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)])
    assert causal_interval(graph, 0, 3) == {0, 1, 2, 3}


def test_interval_width_is_the_transverse_max_antichain():
    graph = nx.DiGraph([(0, 1), (0, 2), (1, 3), (2, 3)])
    # Interval I[0,3] = {0,1,2,3}; its widest antichain is {1,2}.
    assert interval_width(graph, 0, 3) == 2


def test_interval_width_degenerate_when_endpoint_unreachable():
    graph = nx.DiGraph([(0, 1)])
    graph.add_node(2)  # 2 is not reachable from 0
    assert interval_width(graph, 0, 2) == 0


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_max_antichain_size_matches_bruteforce_on_small_random_dags(seed):
    # Validate the Dilworth/matching implementation against an exhaustive
    # largest-antichain search (nx.antichains enumerates every antichain, so it
    # is only feasible on tiny graphs -- keep this well under ~15 nodes).
    rng = np.random.default_rng(seed)
    n = 10
    graph = nx.DiGraph()
    graph.add_nodes_from(range(n))
    for v in range(1, n):
        for u in range(v):
            if rng.random() < 0.25:  # only u < v edges => guaranteed acyclic
                graph.add_edge(u, v)
    brute = max(len(anti) for anti in nx.antichains(graph))
    assert max_antichain_size(graph) == brute


def _small_motif_graph(k=3, motif_width=4, charge_biased_routing=False, seed=7):
    return generate_braided_motif_graph(
        n_generations=40, k=k, motif_width=motif_width, warmup_events=300,
        walk_hops=5, background_ratio=10,
        charge_biased_routing=charge_biased_routing, seed=seed,
    )


def test_braided_motif_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        generate_braided_motif_graph(n_generations=10, k=3, motif_width=1, seed=0)
    with pytest.raises(ValueError):
        generate_braided_motif_graph(n_generations=10, k=1, motif_width=4, seed=0)
    with pytest.raises(ValueError):
        generate_braided_motif_graph(
            n_generations=10, k=3, motif_width=4, internal_parents=1, seed=0
        )


@pytest.mark.parametrize("routing", [False, True])
def test_braided_motif_graph_is_acyclic_and_respects_shadow_rule(routing):
    graph, generations, _, _ = _small_motif_graph(charge_biased_routing=routing)
    assert nx.is_directed_acyclic_graph(graph)
    for node in graph.nodes:
        parents = list(graph.predecessors(node))
        for i in range(len(parents)):
            for j in range(i + 1, len(parents)):
                a, b = parents[i], parents[j]
                assert not nx.has_path(graph, a, b)
                assert not nx.has_path(graph, b, a)


def test_braided_motif_generations_are_antichains_of_constant_width():
    graph, generations, _, _ = _small_motif_graph(motif_width=4)
    assert len(generations) == 41  # n_generations + 1
    for generation in generations:
        assert len(generation) == 4
        for i in range(4):
            for j in range(i + 1, 4):
                a, b = generation[i], generation[j]
                assert not nx.has_path(graph, a, b)
                assert not nx.has_path(graph, b, a)


def test_braided_motif_braids_from_previous_generation():
    # Every motif node takes exactly 2 internal parents from the immediately
    # previous generation (the braid), plus possibly captured background nodes.
    graph, generations, _, capture_counts = _small_motif_graph(k=3, motif_width=4)
    for prev, current in zip(generations, generations[1:]):
        prev_set = set(prev)
        for node in current:
            parents = set(graph.predecessors(node))
            assert len(parents & prev_set) == 2
            # k=3, internal=2 => at most one capture per node
            assert len(parents - prev_set) <= 1


def test_braided_motif_metabolism_actually_captures():
    # With k=3 there is one capture slot per node per generation; over 40
    # generations at least some captures must succeed, and none may exceed
    # the slot budget.
    _, _, _, capture_counts = _small_motif_graph(k=3, motif_width=4)
    assert capture_counts.sum() > 0
    assert capture_counts.max() <= 4  # motif_width * (k - internal_parents)


def test_braided_motif_k2_is_sealed_no_metabolism():
    # The structural prediction: k=2 leaves zero capture slots -- a sealed
    # crystal. The run must work but capture nothing.
    _, _, _, capture_counts = _small_motif_graph(k=2, motif_width=4)
    assert capture_counts.sum() == 0


def test_braided_motif_external_time_is_monotonic():
    _, _, external_time, _ = _small_motif_graph()
    assert np.all(np.diff(external_time) > 0)


def test_braided_motif_radiates_its_retired_generations():
    # Radiation (TEI 6bis.2): retired membrane members re-enter the event
    # heap and fire background events of their own, so the membrane must have
    # out-edges to non-membrane children (structural emission, not the
    # accidental kind that background walks used to provide).
    graph, generations, _, _ = _small_motif_graph(k=3, motif_width=4)
    membrane = set()
    for generation in generations:
        membrane.update(generation)
    emission_edges = sum(
        1 for m in membrane for child in graph.successors(m) if child not in membrane
    )
    assert emission_edges > 0


def test_braided_motif_radiation_preserves_shadow_rule_and_antichains():
    # The wake firing back into the neighbourhood must not corrupt the causal
    # invariants: parents of every node stay mutually independent, and each
    # generation stays an antichain.
    graph, generations, _, _ = _small_motif_graph(k=3, motif_width=4, seed=11)
    assert nx.is_directed_acyclic_graph(graph)
    for node in graph.nodes:
        parents = list(graph.predecessors(node))
        for i in range(len(parents)):
            for j in range(i + 1, len(parents)):
                a, b = parents[i], parents[j]
                assert not nx.has_path(graph, a, b)
                assert not nx.has_path(graph, b, a)
    for generation in generations:
        for i in range(len(generation)):
            for j in range(i + 1, len(generation)):
                a, b = generation[i], generation[j]
                assert not nx.has_path(graph, a, b)
                assert not nx.has_path(graph, b, a)


def _small_two_motif_graph(seed=7, birth_separation=3, routing=False):
    return generate_two_motif_graph(
        n_generations=30, k=3, motif_width=3, birth_separation=birth_separation,
        warmup_events=400, walk_hops=5, background_ratio=10,
        charge_biased_routing=routing, seed=seed,
    )


def test_two_motif_graph_advances_both_bodies_with_invariants():
    graph, gens_a, gens_b, info = _small_two_motif_graph()
    assert len(gens_a) == 31 and len(gens_b) == 31
    assert nx.is_directed_acyclic_graph(graph)
    for generations in (gens_a, gens_b):
        for generation in generations:
            assert len(generation) == 3
            for i in range(3):
                for j in range(i + 1, 3):
                    a, b = generation[i], generation[j]
                    assert not nx.has_path(graph, a, b)
                    assert not nx.has_path(graph, b, a)
    for node in graph.nodes:
        parents = list(graph.predecessors(node))
        for i in range(len(parents)):
            for j in range(i + 1, len(parents)):
                a, b = parents[i], parents[j]
                assert not nx.has_path(graph, a, b)
                assert not nx.has_path(graph, b, a)


def test_two_motif_graph_respects_birth_separation():
    graph, gens_a, gens_b, info = _small_two_motif_graph(birth_separation=3)
    assert info["realized_separation"] >= 3
    assert info["contact_living"] >= 0
    assert info["contact_wake_by_a"] >= 0 and info["contact_wake_by_b"] >= 0
    # metabolism works for both bodies (k=3 => 1 capture slot per node)
    assert info["capture_counts_a"].sum() > 0
    assert info["capture_counts_b"].sum() > 0


def test_two_motif_graph_raises_when_separation_unavailable():
    with pytest.raises(RuntimeError):
        generate_two_motif_graph(
            n_generations=5, k=3, motif_width=3, birth_separation=1000,
            warmup_events=400, walk_hops=5, background_ratio=10, seed=7,
        )


def test_first_contact_lag_on_handbuilt_graph():
    # Tube A: generations [[0], [1], [2]]; tube B: [[10], [11], [12]].
    # A bridge 1 -> 11 makes B's generation index 1 the first contact from
    # A's anchor 0 (descendants of 0 include 1 -> 11).
    graph = nx.DiGraph([(0, 1), (1, 2), (10, 11), (11, 12), (1, 11)])
    gens_a = [[0], [1], [2]]
    gens_b = [[10], [11], [12]]
    assert first_contact_lag(graph, gens_a, gens_b, anchor=0, max_lag=2) == 1
    # From B toward A there is no path at all: disconnected within horizon.
    assert first_contact_lag(graph, gens_b, gens_a, anchor=0, max_lag=2) is None


def test_hops_at_time_excludes_later_shortcuts():
    from sim.graph_generators import _hops_at_time

    # Chain 0 -> 1 -> 2 -> 3 (ids in creation order), then a later shortcut
    # via node 4 (0 -> 4 -> 3). The past metric (watermark 4) must not see it.
    graph = nx.DiGraph([(0, 1), (1, 2), (2, 3), (0, 4), (4, 3)])
    assert _hops_at_time(graph, [0], watermark=4, targets=[3]) == 3
    assert _hops_at_time(graph, [0], watermark=5, targets=[3]) == 2
    # Unreachable target at a time before it existed
    assert _hops_at_time(graph, [0], watermark=3, targets=[3]) is None


def test_intertube_metrics_on_handbuilt_bridge():
    from sim.graph_generators import intertube_metrics

    # Tube A gen 0 = [0]; tube B gen 0 = [3]; bridge 0 -> 1 -> 2 -> 3.
    graph = nx.DiGraph([(0, 1), (1, 2), (2, 3)])
    gens_a = [[0]]
    gens_b = [[3]]
    distance, corridor = intertube_metrics(graph, gens_a, gens_b, 0, watermark=4, slack=0)
    assert distance == 3
    # Exact-geodesic corridor: all four nodes lie on the unique shortest path.
    assert corridor == 4


def test_two_motif_graph_records_increasing_id_watermarks():
    graph, gens_a, gens_b, info = _small_two_motif_graph()
    marks = info["id_watermarks"]
    assert len(marks) == 30
    assert np.all(np.diff(marks) > 0)
    assert marks[-1] <= graph.number_of_nodes() + 10
