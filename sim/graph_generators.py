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

Neither `generate_random_dag` nor `sprinkle_minkowski` explains why an exponent
of 3 (rather than 2 or 4) should emerge from purely local, non-embedded
coupling rules -- that is the actual open question (TEI 7.5). This module is
instrumentation for exploring it, not a claimed solution to it.
"""

import argparse

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


def causal_future_mask(points, origin_index):
    """Boolean mask of points causally following `points[origin_index]`.

    p precedes q iff q lies within p's future light cone: dt > 0 and dt > |dx|.
    """
    origin = points[origin_index]
    dt = points[:, 0] - origin[0]
    dx = np.linalg.norm(points[:, 1:] - origin[1:], axis=1)
    return dt > dx


def reachable_within_hops(graph, origin, max_hops):
    """Cumulative count of nodes reachable from `origin` within each hop count 1..max_hops."""
    lengths = nx.single_source_shortest_path_length(graph, origin, cutoff=max_hops)
    counts = np.zeros(max_hops, dtype=int)
    for hop in lengths.values():
        if hop > 0:
            counts[hop - 1:] += 1
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
    parser.add_argument("--mode", choices=["random-dag", "sprinkling", "tei-shadow"], required=True)
    parser.add_argument("--dim", type=int, default=4, help="Embedding dimension (sprinkling mode)")
    parser.add_argument("--N", type=int, default=100000, help="Number of nodes/points")
    parser.add_argument("--out-degree", type=int, default=4, help="Out-degree (random-dag mode)")
    parser.add_argument("--k", type=int, default=3, help="Max valence / antichain size (tei-shadow mode)")
    parser.add_argument("--valence", type=int, default=None, help="Parent-selection budget per node (tei-shadow mode, default: k)")
    parser.add_argument("--ticks", type=int, default=20, help="Number of tick buckets to measure")
    parser.add_argument("--window-frac", type=float, default=0.3, help="Analysis window fraction (sprinkling mode)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=None, help="Path to save counts as .npz")
    args = parser.parse_args()

    if args.mode == "random-dag":
        graph = generate_random_dag(args.N, args.out_degree, seed=args.seed)
        counts = reachable_within_hops(graph, origin=0, max_hops=args.ticks)
    elif args.mode == "tei-shadow":
        graph = generate_tei_shadow_graph(args.N, args.k, valence=args.valence, seed=args.seed)
        counts = reachable_within_hops(graph, origin=0, max_hops=args.ticks)
    else:
        points = sprinkle_minkowski(args.N, args.dim, seed=args.seed)
        origin_index = int(np.argmin(points[:, 0]))
        counts = reachable_within_ticks(points, origin_index, args.ticks, window_frac=args.window_frac)

    exponent = fit_growth_exponent(counts)
    print(f"mode={args.mode} estimated growth exponent = {exponent:.3f}")
    print(f"counts per tick: {counts.tolist()}")

    if args.out:
        np.savez(args.out, counts=counts, exponent=exponent)


if __name__ == "__main__":
    main()
