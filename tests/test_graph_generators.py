import networkx as nx
import numpy as np
import pytest

from sim.graph_generators import (
    causal_future_mask,
    fit_growth_exponent,
    generate_event_driven_shadow_graph,
    generate_random_dag,
    generate_tei_shadow_graph,
    longest_path_depths,
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
