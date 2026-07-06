import networkx as nx
import numpy as np
import pytest

from sim.graph_generators import (
    causal_future_mask,
    fit_growth_exponent,
    generate_random_dag,
    generate_tei_shadow_graph,
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
