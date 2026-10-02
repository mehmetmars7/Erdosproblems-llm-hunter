#!/usr/bin/env python3
"""Exact finite certificates for third-batch Ultra attempts, 2 October 2026.

Run with Python 3; standard library only. These checks reproduce the finite
claims cited by the attempts. They are not proofs of the unrestricted open
problems. The 3248 online potential argument has no finite-search claim.
"""
from fractions import Fraction
from itertools import combinations, permutations, product
from math import factorial
from random import Random


def graph(n, edges):
    adj = [set() for _ in range(n)]
    for a, b in edges:
        assert 0 <= a < n and 0 <= b < n and a != b
        adj[a].add(b)
        adj[b].add(a)
    return adj


def square(adj):
    result = []
    for v, neighbours in enumerate(adj):
        reached = set(neighbours)
        for w in neighbours:
            reached.update(adj[w])
        reached.discard(v)
        result.append(reached)
    return result


def is_clique(adj, vertices):
    return all(b in adj[a] for a, b in combinations(vertices, 2))


def clique_number(adj, vertices=None):
    vertices = list(range(len(adj))) if vertices is None else list(vertices)
    for size in range(len(vertices), 0, -1):
        if any(is_clique(adj, choice) for choice in combinations(vertices, size)):
            return size
    return 0


def proper(adj, colours):
    return all(colours[v] != colours[w] for v in range(len(adj)) for w in adj[v])


def check_3237():
    adj = graph(5, [(i, (i + 1) % 5) for i in range(5)])
    colours = [0, 1, 0, 1, 2]
    records = []
    for t in range(4):
        n = len(adj)
        delta = max(map(len, adj))
        assert n == 6 * 2**t - 1
        assert delta == (2 if t == 0 else 3 * 2**t - 1)
        assert not any(is_clique(adj, x) for x in combinations(range(n), 3))
        assert proper(adj, colours)
        assert len(set(colours)) == t + 3
        assert t + 3 <= (delta + 1) // 2 + 2
        records.append((n, delta, len(set(colours))))
        edges = [(v, w) for v in range(n) for w in adj[v] if v < w]
        edges += [(n + v, w) for v in range(n) for w in adj[v]]
        edges += [(2 * n, n + v) for v in range(n)]
        adj = graph(2 * n + 1, edges)
        colours = colours + colours + [t + 3]
    print('3237: Mycielski (order, maximum degree, supplied colours):', records)


def check_3245():
    for q in (2, 3):
        palette = set(range(2 * q - 1))
        lists = [set(x) for x in combinations(palette, q)]
        valid_partitions = 0
        for mask in range(1 << len(palette)):
            left = {c for c in palette if mask >> c & 1}
            right = palette - left
            valid_partitions += all(s & left for s in lists) and all(s & right for s in lists)
        assert valid_partitions == 0
        print(f'3245: q={q}, K_{{{len(lists)},{len(lists)}}} has no valid palette partition')


def tree_colouring(adj):
    if not adj:
        return []
    delta = max(map(len, adj))
    colours = [-1] * len(adj)
    colours[0] = 0
    parent = [-1] * len(adj)
    order = [0]
    for v in order:
        children = sorted(w for w in adj[v] if w != parent[v])
        excluded = {colours[v]}
        if parent[v] >= 0:
            excluded.add(colours[parent[v]])
        available = [c for c in range(delta + 1) if c not in excluded]
        assert len(children) <= len(available)
        for w, c in zip(children, available):
            assert colours[w] == -1
            colours[w] = c
            parent[w] = v
            order.append(w)
    assert len(order) == len(adj)
    return colours


def check_3246():
    for r in range(1, 11):
        edges = [(0, 1), (1, 2), (2, 0)]
        for j, (a, b) in enumerate([(0, 1), (1, 2), (2, 0)]):
            for i in range(r):
                v = 3 + j * r + i
                edges += [(a, v), (b, v)]
        adj = graph(3 * r + 3, edges)
        assert max(map(len, adj)) == 2 * r + 2
        assert all(len(neighbours) == len(adj) - 1 for neighbours in square(adj))
    tree_count = 0
    rng = Random(20261002)
    for n in range(1, 41):
        parent_lists = [list(range(n - 1)), [0] * (n - 1), [(v - 1) // 2 for v in range(1, n)]]
        parent_lists += [[rng.randrange(v) for v in range(1, n)] for _ in range(3)]
        for parents in parent_lists:
            adj = graph(n, [(v, p) for v, p in enumerate(parents, 1)])
            colours = tree_colouring(adj)
            assert proper(square(adj), colours)
            assert len(set(colours)) == max(map(len, adj)) + 1
            tree_count += 1
    print(f'3246: 10 complete-square examples and {tree_count} rooted-tree colourings verified')


def degeneracy_order(adj):
    remaining = set(range(len(adj)))
    order, d = [], 0
    while remaining:
        v = min(remaining, key=lambda w: (len(adj[w] & remaining), w))
        d = max(d, len(adj[v] & remaining))
        order.append(v)
        remaining.remove(v)
    return order, d


def check_3249():
    checked = 0
    for n in range(1, 6):
        potential = list(combinations(range(n), 2))
        for mask in range(1 << len(potential)):
            adj = graph(n, [e for i, e in enumerate(potential) if mask >> i & 1])
            order, d = degeneracy_order(adj)
            delta = max(map(len, adj))
            sq = square(adj)
            later = set(range(n))
            for v in order:
                later.remove(v)
                if d == 0:
                    assert not sq[v]
                    continue
                bound = (2 * d - 1) * delta - d * (d - 1)
                assert len(sq[v] & later) <= bound
            checked += 1
    assert checked == 1099
    print('3249: degeneracy square-neighbour inequality verified on all 1099 graphs of orders 1–5')


def check_3251():
    records = []
    for n in range(7, 16, 2):
        m = (n - 1) // 2
        adj = graph(n, [(a, b) for a, b in combinations(range(n), 2) if (b - a) not in (1, n - 1)])
        omega = clique_number(adj)
        block1, block2 = clique_number(adj, range(m)), clique_number(adj, range(m, n))
        assert omega == m and block1 < m and block2 < m
        assert block1 == (m + 1) // 2 and block2 == (m + 2) // 2
        records.append((n, omega, block1, block2))
    print('3251: (antihole order, clique number, two block clique numbers):', records)


def check_3252():
    examples = [
        (2, [(1, 2), (3, 4), (1, 3), (1, 4), (2, 3), (2, 4)]),
        (3, [(1, 2), (1, 3), (2, 3)] * 2),
    ]
    for a, lists in examples:
        n = len(lists)
        adj = graph(n, [(i, j) for i in range(a) for j in range(a, n)])
        assert not any(proper(adj, colours) for colours in product(*lists))
    print('3252: both explicit 2-list obstructions verified by all 64 permitted colour assignments')


def count_cycles(adj, length):
    count = 0
    for vertices in combinations(range(len(adj)), length):
        first = vertices[0]
        for tail in permutations(vertices[1:]):
            if tail[0] > tail[-1]:
                continue
            cycle = (first,) + tail
            if all(cycle[(i + 1) % length] in adj[cycle[i]] for i in range(length)):
                count += 1
    return count


def check_3254():
    records = []
    for k, ell in [(3, 5), (4, 5), (5, 7), (6, 7)]:
        h = k - 2
        n = h + ell
        edges = list(combinations(range(h), 2))
        edges += [(v, h + i) for v in range(h) for i in range(ell)]
        edges += [(h + i, h + (i + 1) % ell) for i in range(ell)]
        adj = graph(n, edges)
        assert clique_number(adj) == k
        cycles = count_cycles(adj, k)
        witnessed = ell * factorial(k - 1) // 2
        target = (k + 1) * factorial(k - 1) // 2
        assert cycles >= witnessed >= target
        records.append((k, ell, cycles, witnessed, target))
    print('3254: (k, rim length, all k-cycles, constructed lower count, target):', records)


def acyclic(arcs, vertices):
    remaining = set(vertices)
    while remaining:
        source = next((v for v in remaining if all((w, v) not in arcs for w in remaining)), None)
        if source is None:
            return False
        remaining.remove(source)
    return True


def check_3255():
    edges = list(combinations(range(4), 2))
    for mask in range(64):
        arcs = {edge if mask >> i & 1 else edge[::-1] for i, edge in enumerate(edges)}
        assert any(
            acyclic(arcs, [v for v in range(4) if colours >> v & 1])
            and acyclic(arcs, [v for v in range(4) if not (colours >> v & 1)])
            for colours in range(16)
        )
    print('3255: all 64 orientations of K4 have an acyclic vertex bipartition')


def check_3257():
    arcs = {(i, (i + j) % 7) for i in range(7) for j in (1, 2, 3)}
    assert all(sum(u == i for u, _ in arcs) == 3 for i in range(7))
    assert not any((b, a) in arcs for a, b in arcs)
    cycles = [(0, 1, 4), (2, 3, 6)]
    assert set(cycles[0]).isdisjoint(cycles[1])
    assert all((c[i], c[(i + 1) % 3]) in arcs for c in cycles for i in range(3))
    for k in range(1, 11):
        for n in (2 * k - 1, 2 * k):
            symmetric = {(i, j) for i in range(n) for j in range(n) if i != j}
            assert all(sum(u == i for u, _ in symmetric) == n - 1 for i in range(n))
            assert (n // 2 >= k) == (n == 2 * k)
            if n == 2 * k:
                assert all((2 * i, 2 * i + 1) in symmetric and (2 * i + 1, 2 * i) in symmetric for i in range(k))
    print('3257: regular tournament triangles and complete symmetric sharpness examples k=1–10 verified')


def multiply(a, b):
    result = [Fraction(0)] * (len(a) + len(b) - 1)
    for i, av in enumerate(a):
        for j, bv in enumerate(b):
            result[i + j] += av * bv
    return result


def check_3347():
    roots = [Fraction(-11, 7), Fraction(-2, 7), Fraction(13, 7)]
    derivative_quarter = [Fraction(1)]
    for r in roots:
        derivative_quarter = multiply(derivative_quarter, [-r, Fraction(1)])
    assert derivative_quarter == [Fraction(-286, 343), -3, 0, 1]
    p = [Fraction(0), Fraction(-1144, 343), -6, 0, 1]
    assert [i * p[i] for i in range(1, 5)] == [4 * c for c in derivative_quarter]
    assert [Fraction(2401) * c / 7**i for i, c in enumerate(p)] == [0, -1144, -294, 0, 1]
    residues = [(z**3 - 294 * z - 1144) % 5 for z in range(5)]
    assert residues == [1, 3, 1, 1, 4]
    values = [z**3 - 294 * z - 1144 for z in (-20, -10, 0, 20)]
    assert values[0] < 0 < values[1] and values[2] < 0 < values[3]
    assert roots[0]**2 + roots[0] * roots[1] + roots[1]**2 == 3
    print('3347: derivative factorization, scaling, modulo-5 residues and cubic signs verified:', values)


def repetition_distances(bits, m, n):
    row_errors = sum(min(sum(bits[i * n:(i + 1) * n]), n - sum(bits[i * n:(i + 1) * n])) for i in range(m))
    col_errors = sum(min(sum(bits[i * n + j] for i in range(m)), m - sum(bits[i * n + j] for i in range(m))) for j in range(n))
    total = sum(bits)
    distance = Fraction(min(total, m * n - total), m * n)
    rho = Fraction(row_errors + col_errors, 2 * m * n)
    return rho, distance


def check_3397():
    checked = 0
    for m in range(1, 4):
        for n in range(1, 4):
            for bits in product((0, 1), repeat=m * n):
                rho, distance = repetition_distances(bits, m, n)
                assert 3 * rho >= distance
                checked += 1
    rho, distance = repetition_distances([0] * 6 + [1] * 6, 4, 3)
    assert rho == Fraction(1, 4) and distance == Fraction(1, 2)
    assert checked == 682
    print('3397: all 682 binary matrices with dimensions 1–3 and the striped ratio 1/2 verified')


def adjacent_gates(a, b):
    # Counts the specified basis gates; every OR/AND below has fan-in two.
    count = 0
    def neg(x):
        nonlocal count
        count += 1
        return 1 - x
    def both(x, y):
        nonlocal count
        count += 1
        return x & y
    def either(x, y):
        nonlocal count
        count += 1
        return x | y
    aa, bb = (a >> 1, a & 1), (b >> 1, b & 1)
    flag = both(aa[0], neg(bb[0]))
    noflag = neg(flag)
    output = [either(both(noflag, u), both(flag, v)) for u, v in zip(aa + bb, bb + aa)]
    assert count == 15
    return (2 * output[0] + output[1], 2 * output[2] + output[3]), count


def check_3400():
    for a, b in product(range(3), repeat=2):
        out, count = adjacent_gates(a, b)
        assert out == ((b, a) if a == 2 and b != 2 else (a, b))
        assert count == 15
    checked = 0
    for n in range(1, 9):
        for word in product(range(3), repeat=n):
            result, gates = list(word), 0
            for length in range(n, 1, -1):
                for i in range(length - 1):
                    pair, count = adjacent_gates(result[i], result[i + 1])
                    result[i:i + 2] = pair
                    gates += count
            expected = [v for v in word if v != 2] + [2] * word.count(2)
            assert result == expected
            assert gates == 15 * n * (n - 1) // 2
            checked += 1
    assert checked == 9840
    print('3400: all 9 adjacent inputs and all 9840 ternary words of lengths 1–8 verified at the claimed gate count')


def main():
    for check in [check_3237, check_3245, check_3246, check_3249, check_3251,
                  check_3252, check_3254, check_3255, check_3257, check_3347,
                  check_3397, check_3400]:
        check()
    print('All third-batch colouring/algebra certificates passed.')


if __name__ == '__main__':
    main()
