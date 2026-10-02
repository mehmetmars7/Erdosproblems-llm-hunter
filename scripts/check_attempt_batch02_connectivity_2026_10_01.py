#!/usr/bin/env python3
"""Exact finite certificates for Ultra attempts 3159--3177, batch 02.

Run with Python 3; standard library only. These checks certify the stated
finite examples and do not establish any unrestricted conjecture.
"""
from itertools import combinations, combinations_with_replacement, permutations, product


def edge(a, b):
    return tuple(sorted((a, b)))


def cycle_edges(order):
    return {edge(a, b) for a, b in zip(order, order[1:] + order[:1])}


def degrees(vertices, edges):
    result = dict.fromkeys(vertices, 0)
    for a, b in edges:
        result[a] += 1
        result[b] += 1
    return result


def components(vertices, edges):
    vertices = set(vertices)
    adjacency = {v: set() for v in vertices}
    for a, b in edges:
        if a in vertices and b in vertices:
            adjacency[a].add(b)
            adjacency[b].add(a)
    result = []
    while vertices:
        root = min(vertices)
        reached, frontier = {root}, [root]
        while frontier:
            v = frontier.pop()
            new = adjacency[v] - reached
            reached.update(new)
            frontier.extend(new)
        vertices -= reached
        result.append(reached)
    return result


def verify_cycle(vertices, edges, order):
    assert len(order) == len(set(order)) == len(vertices)
    assert set(order) == set(vertices)
    assert cycle_edges(order) <= set(edges)


def hamilton_cycles(vertices, edges):
    vertices = list(vertices)
    edges = set(edges)
    result = set()
    for tail in permutations(vertices[1:]):
        order = [vertices[0], *tail]
        if tail[0] > tail[-1]:
            continue
        candidate = frozenset(cycle_edges(order))
        if candidate <= edges:
            result.add(candidate)
    return result


def check_3159():
    count = 0
    for a, b in product(range(1, 5), repeat=2):
        denominator = a + b + 2
        for multiplicities in product(range(11), repeat=3):
            if any(sum(multiplicities[i] for i in pair) < denominator
                   for pair in combinations(range(3), 2)):
                continue
            red = [((a + 1) * m) // denominator for m in multiplicities]
            blue = [m - r for m, r in zip(multiplicities, red)]
            for pair in combinations(range(3), 2):
                assert sum(red[i] for i in pair) >= a
                assert sum(blue[i] for i in pair) >= b
            count += 1
    print(f'3159: all {count} eligible three-bundle instances passed')


def check_3160():
    vertices = list(range(5))
    edges = set(combinations(vertices, 2))
    for r in range(1, 5):
        for subset in combinations(vertices, r):
            assert sum((a in subset) != (b in subset) for a, b in edges) >= 4
    star = {edge(0, i) for i in range(1, 5)}
    assert len(components(vertices, star)) == 1
    assert degrees(vertices, edges - star)[0] == 0
    print('3160: K5 has all cuts >=4; deleting the chosen star isolates 0')


def check_3162():
    c, d = [0, 1, 2, 3, 4], [0, 2, 4, 1, 3]
    assert not cycle_edges(c) & cycle_edges(d)
    assert cycle_edges(c) | cycle_edges(d) == set(combinations(range(5), 2))
    for v in range(5):
        incident = [edge(v, w) for w in range(5) if w != v]
        corners = []
        for order in [c, c, d, d]:
            i = order.index(v)
            corners.append((edge(v, order[i - 1]), edge(v, order[(i + 1) % 5])))
        assert set(degrees(incident, corners).values()) == {2}
        assert sorted(map(len, components(incident, corners))) == [2, 2]
    print('3162: K5 cover has two link components at each vertex')


def petersen_data():
    edges = [edge(i, (i + 1) % 5) for i in range(5)]
    edges += [edge(i, i + 5) for i in range(5)]
    edges += [edge(i + 5, (i + 2) % 5 + 5) for i in range(5)]
    return edges


def even_mask(mask, edges):
    chosen = [e for i, e in enumerate(edges) if mask >> i & 1]
    return all(d % 2 == 0 for d in degrees(range(10), chosen).values())


def check_3163_and_3173():
    edges = petersen_data()
    matchings = []
    for indices in combinations(range(15), 5):
        chosen = {edges[i] for i in indices}
        if set(degrees(range(10), chosen).values()) == {1}:
            matchings.append(chosen)
            complement = set(edges) - chosen
            assert sorted(map(len, components(range(10), complement))) == [5, 5]
    assert len(matchings) == 6
    certificate = [
        {0, 1, 2, 3, 4}, {0, 2, 5, 6, 7, 8, 10, 11},
        {3, 8, 9, 10, 12, 13}, {1, 6, 7, 12, 14},
        {4, 5, 9, 11, 13, 14},
    ]
    for indices in certificate:
        ds = degrees(range(10), [edges[i] for i in indices])
        assert set(ds.values()) <= {0, 2}
    assert all(sum(i in indices for indices in certificate) == 2 for i in range(15))
    assert certificate[0] == set(range(5))
    binary_cycles = [mask for mask in range(1 << 15) if even_mask(mask, edges)]
    assert len(binary_cycles) == 64
    first = (1 << 5) - 1
    found = None
    for a, b, c in combinations_with_replacement(binary_cycles, 3):
        counts = [sum(mask >> i & 1 for mask in [first, a, b, c]) for i in range(15)]
        if min(counts) < 1 or max(counts) > 2:
            continue
        last = sum(1 << i for i, count in enumerate(counts) if count == 1)
        if even_mask(last, edges):
            found = [first, a, b, c, last]
            break
    assert found == [sum(1 << i for i in indices) for indices in certificate]
    print('3163/3173: six Petersen matchings, all complements 5+5; five-cover reproduced')


def check_3166():
    for m in range(2, 9):
        length = 2 * m
        vertices = list(range(2 * length))
        top, bottom = list(range(length)), list(range(length, 2 * length))
        edges = cycle_edges(top) | cycle_edges(bottom)
        edges |= {edge(i, i + length) for i in range(length)}
        verify_cycle(vertices, edges, top + bottom[::-1])
    top, bottom = list(range(4)), list(range(4, 8))
    factor = cycle_edges(top) | cycle_edges(bottom)
    matching = {edge(i, i + 4) for i in range(4)}
    square = cycle_edges([0, 1, 5, 4])
    new_factor, new_matching = factor ^ square, matching ^ square
    assert set(degrees(range(8), new_matching).values()) == {1}
    assert set(degrees(range(8), new_factor).values()) == {2}
    assert len(components(range(8), new_factor)) == 1
    print('3166: seven prism certificates and the cube merging switch passed')


def check_3167():
    for n, expected in [(4, 2), (6, 24)]:
        cycles = hamilton_cycles(range(n), combinations(range(n), 2))
        assert sum((0, 1) in c for c in cycles) == expected
    print('3167: fixed-edge Hamilton counts are 2 in K4 and 24 in K6')


def check_3168():
    root_edges = [(0, i) for i in range(1, 6)]
    line_edges = {edge(i, j) for i, j in combinations(range(5), 2)
                  if set(root_edges[i]) & set(root_edges[j])}
    assert line_edges == set(combinations(range(5), 2))
    for r in range(4):
        for removed in combinations(range(5), r):
            assert len(components(set(range(5)) - set(removed), line_edges)) == 1
    verify_cycle(range(5), line_edges, list(range(5)))
    print('3168: line graph of K1,5 is four-connected Hamiltonian K5')


def cycle_vertex_masks(n, edges):
    edges = set(edges)
    masks = set()
    for length in range(3, n + 1):
        for vertices in combinations(range(n), length):
            for tail in permutations(vertices[1:]):
                order = [vertices[0], *tail]
                if tail[0] < tail[-1] and cycle_edges(order) <= edges:
                    masks.add(sum(1 << v for v in vertices))
                    break
    return sorted(masks)


def packing_feedback(n, edges):
    cycles = cycle_vertex_masks(n, edges)
    reachable = {0: 0}
    for cycle in cycles:
        for used, count in list(reachable.items()):
            if not cycle & used:
                reachable[used | cycle] = max(reachable.get(used | cycle, 0), count + 1)
    packing = max(reachable.values())
    for size in range(n + 1):
        for subset in combinations(range(n), size):
            deleted = sum(1 << v for v in subset)
            if all(deleted & cycle for cycle in cycles):
                return packing, size
    raise AssertionError('unreachable')


def check_3170():
    k4 = set(combinations(range(4), 2))
    flower = set().union(*(cycle_edges([0, 2 * i + 1, 2 * i + 2]) for i in range(3)))
    two = cycle_edges([0, 1, 2]) | cycle_edges([3, 4, 5]) | {(2, 3)}
    values = [packing_feedback(4, k4), packing_feedback(7, flower), packing_feedback(6, two)]
    assert values == [(1, 2), (1, 1), (2, 2)]
    print(f'3170: exact (cp,cc) values {values}')


def check_3171():
    for m in range(2, 9):
        vertices = list(range(2 * m + 2))
        u, v = 2 * m, 2 * m + 1
        edges = cycle_edges(list(range(2 * m)))
        edges |= {edge(u, 2 * i) for i in range(m)}
        edges |= {edge(v, 2 * i + 1) for i in range(m)}
        order = [0, u, 2, 1, v, 3] + list(range(4, 2 * m))
        verify_cycle(vertices, edges, order)
    print('3171: seven alternating two-hub Hamilton certificates passed')


def check_3172():
    for m in range(3, 21):
        def multiply(x, y):
            a, b = x
            c, d = y
            return ((a + (-1 if b else 1) * c) % m, (b + d) % 2)
        vertices = list(product(range(m), range(2)))
        generators = [(1, 0), (m - 1, 0), (0, 1)]
        edges = {edge(x, multiply(x, s)) for x in vertices for s in generators}
        order = [(i, 0) for i in range(m)] + [(i, 1) for i in range(m - 1, -1, -1)]
        verify_cycle(vertices, edges, order)
    lifted = [(3 * t + i) % 12 for t in range(4) for i in range(3)]
    verify_cycle(range(12), cycle_edges(list(range(12))), lifted)
    print('3172: 18 dihedral words and the Z12 quotient lift passed')


def check_3177():
    k44 = {edge(a, b) for a in range(4) for b in range(4, 8)}
    assert len(hamilton_cycles(range(8), k44)) == 72
    square = {edge(i, (i + step) % 8) for i in range(8) for step in [1, 2]}
    assert set(degrees(range(8), square).values()) == {4}
    for r in range(4):
        for removed in combinations(range(8), r):
            assert len(components(set(range(8)) - set(removed), square)) == 1
    c, d = list(range(8)), [0, 2, 1, 3, 4, 5, 6, 7]
    verify_cycle(range(8), square, c)
    verify_cycle(range(8), square, d)
    assert cycle_edges(c) != cycle_edges(d)
    print('3177: K4,4 has 72 Hamilton cycles; C8-square is four-connected with two certificates')


if __name__ == '__main__':
    for check in [check_3159, check_3160, check_3162, check_3163_and_3173,
                  check_3166, check_3167, check_3168, check_3170,
                  check_3171, check_3172, check_3177]:
        check()
    print('All finite certificates passed. No unrestricted conjecture is certified.')
