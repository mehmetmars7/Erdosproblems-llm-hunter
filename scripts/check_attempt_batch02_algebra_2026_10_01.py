#!/usr/bin/env python3
"""Exact finite checks quoted in the 2026-10-01 second Ultra attempt batch.

Uses only the Python standard library. Run from any working directory:
    python3 scripts/check_attempt_batch02_algebra_2026_10_01.py
These finite checks do not certify any unrestricted conjecture.
"""
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from math import comb


def adjacency(n, edges):
    result = [set() for _ in range(n)]
    for u, v in edges:
        result[u].add(v)
        result[v].add(u)
    return result


def components(n, edges):
    parent = list(range(n))

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    for u, v in edges:
        parent[find(u)] = find(v)
    return tuple(sorted(Counter(find(v) for v in range(n)).values(), reverse=True))


def normalized(edges):
    return {tuple(sorted(e)) for e in edges}


def cycle_edges(n, offset=0):
    return normalized((offset + i, offset + (i + 1) % n) for i in range(n))


def test_3132():
    minima = []
    for n in range(1, 6):
        pairs = list(combinations(range(n), 2))
        pair_index = {edge: i for i, edge in enumerate(pairs)}
        minimum = len(pairs)
        for orientation in range(1 << len(pairs)):
            triples = []
            for vertices in combinations(range(n), 3):
                out = Counter()
                mask = 0
                for u, v in combinations(vertices, 2):
                    i = pair_index[u, v]
                    mask |= 1 << i
                    out[u if orientation >> i & 1 else v] += 1
                if max(out.values()) == 2:
                    triples.append(mask)

            @lru_cache(None)
            def best(i, used):
                if i == len(triples):
                    return 0
                value = best(i + 1, used)
                if not used & triples[i]:
                    value = max(value, 1 + best(i + 1, used | triples[i]))
                return value

            minimum = min(minimum, best(0, 0))
        minima.append(minimum)
    assert minima == [0, 0, 0, 1, 2], minima
    print('3132: all tournaments through order 5, minima', minima)


def test_3137():
    for m in range(3, 21):
        top = cycle_edges(m)
        bottom = cycle_edges(m, m)
        spokes = normalized((i, m + i) for i in range(m))
        graph = top | bottom | spokes
        tree = spokes | {(m + i, m + i + 1) for i in range(m - 1)}
        matching = {(m, 2 * m - 1)}
        assert not top & tree and not top & matching and not tree & matching
        assert top | tree | matching == graph
        assert len(tree) == 2 * m - 1 and components(2 * m, tree) == (2 * m,)
        deg = list(map(len, adjacency(2 * m, tree)))
        leaves = {i for i, d in enumerate(deg) if d == 1}
        assert leaves == set(range(m))
        assert normalized(e for e in graph if set(e) <= leaves) == top
    print('3137: prism decompositions checked for m = 3,...,20')


def test_3142():
    for n in range(9, 301, 3):
        a, b = next((a, b) for a in range(n // 4 + 1)
                    for b in range(n // 5 + 1) if 4 * a + 5 * b == n)
        colours = [1, 2, 3, 4] * a + [1, 2, 3, 4, 5] * b
        assert len(colours) == n
        for i in range(n):
            for distance in (1, 2, 3):
                assert colours[i] != colours[(i + distance) % n]
    print('3142: cycle block colourings checked for all N = 9,...,300 divisible by 3')


def petersen_from_blocks():
    # v = 0, u_1,u_2,u_3 = 1,2,3; blocks {4,5},{6,7},{8,9}.
    edges = {(0, i) for i in range(1, 4)}
    for i in range(3):
        edges.update((i + 1, 4 + 2 * i + x) for x in (0, 1))
    edges.update({(4, 6), (5, 7), (4, 8), (5, 9), (6, 9), (7, 8)})
    return edges


def test_3143():
    adj = adjacency(10, petersen_from_blocks())
    assert all(len(neighbours) == 3 for neighbours in adj)
    for u, v in combinations(range(10), 2):
        assert len(adj[u] & adj[v]) == (0 if v in adj[u] else 1)
    assert 1 + 1729 + 1520 == 3250
    assert 57 + 7 * 1729 - 8 * 1520 == 0
    assert 57 ** 2 + 49 * 1729 + 64 * 1520 == 3250 * 57
    print('3143: degree-3 matching reduction and degree-57 spectral arithmetic checked')


def flow_value(n, edges, x=Fraction(11, 2)):
    edges = list(edges)  # Retain duplicate edges as distinct subset indices.
    total = Fraction(0)
    for mask in range(1 << len(edges)):
        selected = [edge for i, edge in enumerate(edges) if mask >> i & 1]
        nullity = len(selected) - n + len(components(n, selected))
        assert nullity >= 0
        total += (-1) ** (len(edges) - len(selected)) * x ** nullity
    return total


def test_3146():
    x = Fraction(11, 2)
    for s in range(2, 9):
        value = flow_value(2, [(0, 1)] * s)
        assert value == ((x - 1) ** s + (-1) ** s * (x - 1)) / x
        assert value > 0
    for n in range(3, 9):
        assert flow_value(n, cycle_edges(n)) == x - 1
    theta = [(0, 2), (2, 1), (0, 3), (3, 4), (4, 1),
             (0, 5), (5, 6), (6, 7), (7, 1)]
    assert flow_value(8, theta) == (x - 1) * (x - 2)
    print('3146: exact rational subset sums check bundles, cycles and a 2/3/4 theta')


def csf_coefficients(n, edges):
    coefficients = Counter()
    for mask in range(1 << len(edges)):
        selected = [e for i, e in enumerate(edges) if mask >> i & 1]
        coefficients[components(n, selected)] += (-1) ** len(selected)
    return coefficients


def cut_profile(n, edges):
    return tuple(sorted(min(components(n, edges[:i] + edges[i + 1:]))
                        for i in range(len(edges))))


def test_3150():
    first = [(0, 1), (0, 2), (0, 3), (0, 4), (1, 5), (5, 6)]
    second = [(0, 1), (0, 2), (0, 3), (1, 4), (1, 5), (2, 6)]
    assert components(7, first) == components(7, second) == (7,)
    assert cut_profile(7, first) == cut_profile(7, second) == (1, 1, 1, 1, 2, 3)
    assert sorted(map(len, adjacency(7, first))) != sorted(map(len, adjacency(7, second)))
    a, b = csf_coefficients(7, first), csf_coefficients(7, second)
    assert a[3, 2, 2] == 0 and b[3, 2, 2] == 1
    assert components(7, [(0, 3), (1, 4), (1, 5), (2, 6)]) == (3, 2, 2)
    print('3150: equal single-edge profiles; p_(3,2,2) coefficients are 0 and 1')


def line_graph(n, edges):
    edges = list(edges)
    return len(edges), [(i, j) for i, j in combinations(range(len(edges)), 2)
                        if set(edges[i]) & set(edges[j])]


def line_orders(n, edges):
    orders = [n]
    for _ in range(4):
        n, edges = line_graph(n, edges)
        orders.append(n)
    return tuple(orders)


def test_3151():
    first = [(0, 1), (0, 2), (0, 3), (1, 4), (1, 5), (2, 6), (3, 7)]
    second = [(0, 1), (0, 2), (0, 3), (1, 4), (1, 5), (2, 6), (4, 7)]
    expected = [(8, 7, 8, 14, 41), (8, 7, 8, 14, 40)]
    for edges, orders in zip((first, second), expected):
        assert components(8, edges) == (8,) and len(edges) == 7
        assert line_orders(8, edges) == orders
        deg = list(map(len, adjacency(8, edges)))
        assert sum(comb(d, 2) for d in deg) == orders[2]
        assert sum(comb(deg[u] + deg[v] - 2, 2) for u, v in edges) == orders[3]
    print('3151: line-graph orders checked:', expected)


def connected_after_deletion(n, edges, removed):
    adj = adjacency(n, edges)
    remaining = set(range(n)) - set(removed)
    visited = {next(iter(remaining))}
    pending = list(visited)
    while pending:
        u = pending.pop()
        new = (adj[u] & remaining) - visited
        visited.update(new)
        pending.extend(new)
    return visited == remaining


def domination_number(n, edges):
    adj = adjacency(n, edges)
    closed = [neighbours | {v} for v, neighbours in enumerate(adj)]
    for k in range(1, n + 1):
        for chosen in combinations(range(n), k):
            if len(set().union(*(closed[v] for v in chosen))) == n:
                return k
    raise AssertionError('No dominating set')


def test_3155():
    prism = cycle_edges(3) | cycle_edges(3, 3) | {(i, i + 3) for i in range(3)}
    cube = {(u, v) for u, v in combinations(range(8), 2) if (u ^ v).bit_count() == 1}
    cases = [('K4', 4, list(combinations(range(4), 2)), 1),
             ('K3,3', 6, [(u, v) for u in range(3) for v in range(3, 6)], 2),
             ('prism', 6, prism, 2), ('cube', 8, cube, 2),
             ('Petersen', 10, petersen_from_blocks(), 3)]
    for name, n, edges, expected in cases:
        assert all(len(a) == 3 for a in adjacency(n, edges))
        for size in range(3):
            for removed in combinations(range(n), size):
                assert connected_after_deletion(n, edges, removed), (name, removed)
        assert domination_number(n, edges) == expected, name
    for n in range(3, 101):
        chosen = set(range(0, n, 3))
        assert len(chosen) == (n + 2) // 3
        assert all(v in chosen or (v - 1) % n in chosen or (v + 1) % n in chosen
                   for v in range(n))
    print('3155: five cubic examples, all 2-vertex deletions and cyclic placements checked')


def main():
    for check in (test_3132, test_3137, test_3142, test_3143, test_3146,
                  test_3150, test_3151, test_3155):
        check()
    print('All second-batch algebra/combinatorics finite checks passed.')


if __name__ == '__main__':
    main()
