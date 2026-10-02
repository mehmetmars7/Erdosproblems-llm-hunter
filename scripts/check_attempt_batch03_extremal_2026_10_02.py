#!/usr/bin/env python3
"""Finite certificates for the third Ultra catalogue batch, 2 October 2026.

Standard library only. These exhaustions verify the finite assertions in the
corresponding TeX attempts; they do not resolve the unrestricted conjectures.
Run from any directory with Python 3.10+.
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations, permutations, product
from math import comb, factorial, isqrt


def edge(a, b):
    return tuple(sorted((a, b)))


def adjacency(n, edges):
    out = [set() for _ in range(n)]
    for u, v in edges:
        out[u].add(v)
        out[v].add(u)
    return out


def is_forest(n, edges):
    parent = list(range(n))
    def find(x):
        while x != parent[x]:
            x = parent[x]
        return x
    for u, v in edges:
        a, b = find(u), find(v)
        if a == b:
            return False
        parent[a] = b
    return True


def chromatic(n, edges):
    adj = adjacency(n, edges)
    if n == 0:
        return 0
    for limit in range(1, n + 1):
        colours = [-1] * n
        def search(done, used):
            if done == n:
                return True
            uncoloured = [v for v in range(n) if colours[v] < 0]
            v = max(uncoloured, key=lambda x: (
                len({colours[y] for y in adj[x] if colours[y] >= 0}), len(adj[x])))
            forbidden = {colours[y] for y in adj[v] if colours[y] >= 0}
            for c in range(min(limit, used + 1)):
                if c in forbidden:
                    continue
                colours[v] = c
                if search(done + 1, max(used, c + 1)):
                    return True
            colours[v] = -1
            return False
        if search(0, 0):
            return limit
    raise AssertionError("No colouring found")


def check_packing():
    blue = {edge(a, b) for a in range(3) for b in range(3, 6)}
    red = [(0, 1), (2, 3), (4, 5)]
    for p in permutations(range(6)):
        assert any(edge(p[a], p[b]) in blue for a, b in red)
    print("3287: all 720 placements of the K3,3/matching obstruction checked")


def check_cube():
    edges = list(combinations(range(8), 2))
    index = {e: i for i, e in enumerate(edges)}
    cube = [e for e in edges if (e[0] ^ e[1]).bit_count() == 1]
    def mask(es):
        return sum(1 << index[edge(a, b)] for a, b in es)
    cubes = sorted({mask(edge(p[a], p[b]) for a, b in cube)
                    for p in permutations(range(8))})
    assert len(cubes) == 840
    full = (1 << len(edges)) - 1
    base = mask(e for e in cube if e != (0, 1))
    assert base.bit_count() == 11
    def closure(current):
        while True:
            old = current
            for q in cubes:
                missing = q & ~current
                if missing and missing & (missing - 1) == 0:
                    current |= missing
            if current == old:
                return current
    outside = [i for i in range(28) if not (base >> i) & 1]
    count = 0
    for size in range(4):
        for extras in combinations(outside, size):
            seed = base | sum(1 << i for i in extras)
            assert closure(seed) != full
            count += 1
    assert count == 834
    seed = base | mask([(0, 3), (0, 5), (0, 6), (1, 2)])
    assert seed.bit_count() == 15
    trace = [(2, 4), (2, 7), (1, 6), (3, 4), (0, 7), (1, 7),
             (3, 5), (3, 6), (2, 5), (1, 4), (0, 1), (4, 7), (5, 6)]
    current = seed
    certificates = []
    for e in trace:
        bit = 1 << index[e]
        assert not current & bit
        witness = next(q for q in cubes if q & ~current == bit)
        certificates.append((e, [edges[i] for i in range(28) if witness >> i & 1]))
        current |= bit
    assert current == full and closure(seed) == full
    print("3288: 840 cube copies; all 834 seeds of size <=14 fail; 15-edge seed succeeds")
    for e, witness in certificates:
        print("  inserted", e, "cube", witness)


def check_hypergraphs():
    checked = 0
    for r in (2, 3, 4):
        p = Fraction(factorial(r), r ** r)
        for overlap in range(r):
            e = tuple(range(r))
            f = tuple(range(overlap)) + tuple(range(r, 2 * r - overlap))
            vertices = 2 * r - overlap
            both = sum(len({c[v] for v in e}) == r and
                       len({c[v] for v in f}) == r
                       for c in product(range(r), repeat=vertices))
            exact = Fraction(both, r ** vertices)
            assert exact == Fraction(factorial(r) * factorial(r - overlap),
                                     r ** (2 * r - overlap))
            if overlap <= 1:
                assert exact == p * p
            checked += 1
    # Three-uniform sunflower: common core 0,1 and four petals.
    zeros_on_repeat = 0
    for c in product(range(3), repeat=6):
        total = sum(len({c[0], c[1], c[v]}) == 3 for v in range(2, 6))
        if c[0] == c[1]:
            assert total == 0
            zeros_on_repeat += 1
    assert Fraction(zeros_on_repeat, 3 ** 6) == Fraction(1, 3)
    print("3295:", checked, "exact overlap probabilities and sunflower checked")


def expectation_chi(n, edges):
    total = 0
    for m in range(1 << len(edges)):
        total += chromatic(n, [e for i, e in enumerate(edges) if m >> i & 1])
    return Fraction(total, 1 << len(edges))


def check_random_colouring():
    for q in range(2, 6):
        expected = expectation_chi(q, list(combinations(range(q), 2)))
        assert expected * expected >= q
    for length in (3, 5, 7, 9):
        cycle = sorted({edge(i, (i + 1) % length) for i in range(length)})
        assert expectation_chi(length, cycle) == 2
    for leaves in range(1, 7):
        star = [(0, v) for v in range(1, leaves + 1)]
        assert expectation_chi(leaves + 1, star) == 2 - Fraction(1, 2 ** leaves)
    print("3308: exact expectations for cliques through K5, odd cycles through C9, stars")


def forest_masks(n, edges):
    return [mask for mask in range(1 << len(edges))
            if is_forest(n, [e for i, e in enumerate(edges) if mask >> i & 1])]


def check_forests():
    cases = [
        (4, [(0, 1), (1, 2), (2, 0), (2, 3)], [{0, 1, 2}]),
        (7, [(0, 1), (1, 2), (2, 0), (0, 3), (3, 4), (4, 5), (5, 0), (5, 6)],
         [{0, 1, 2}, {3, 4, 5, 6}]),
        (5, [(0, 1), (1, 2), (2, 3), (3, 4)], []),
    ]
    for n, edges, blocks in cases:
        forests = forest_masks(n, edges)
        N = len(forests)
        for e, f in combinations(range(len(edges)), 2):
            Ne = sum(bool(mask >> e & 1) for mask in forests)
            Nf = sum(bool(mask >> f & 1) for mask in forests)
            Nef = sum(bool(mask >> e & 1) and bool(mask >> f & 1) for mask in forests)
            cov = Fraction(Nef, N) - Fraction(Ne * Nf, N * N)
            common = next((b for b in blocks if e in b and f in b), None)
            if common is None:
                assert cov == 0
            else:
                length = len(common)
                assert cov == -Fraction(2 ** (length - 2), (2 ** length - 1) ** 2)
    first = [(0, 2), (1, 2)]
    second = [(0, 1), (2, 3)]
    assert is_forest(4, first) and is_forest(4, second)
    assert not is_forest(4, first + [(0, 1)])
    weights = []
    for mask in range(4):
        chosen = [e for i, e in enumerate([(0, 1), (1, 2)]) if mask >> i & 1]
        adj = adjacency(3, chosen)
        unseen = set(range(3))
        weight = 1
        while unseen:
            stack = [unseen.pop()]
            size = 0
            while stack:
                v = stack.pop()
                size += 1
                for w in adj[v] & unseen:
                    unseen.remove(w)
                    stack.append(w)
            weight *= size
        weights.append(weight)
    assert weights == [1, 2, 2, 3]
    assert Fraction(weights[1] + weights[3], sum(weights)) == Fraction(5, 8)
    print("3309: cactus covariances, failed exchange, and rooted/unrooted path measures checked")


def all_even_cycles(p):
    unseen = set(range(len(p)))
    while unseen:
        v = unseen.pop()
        length = 1
        w = p[v]
        while w != v:
            unseen.remove(w)
            length += 1
            w = p[w]
        if length % 2:
            return False
    return True


def check_lifts():
    for h in range(1, 9):
        good = sum(all_even_cycles(p) for p in permutations(range(h)))
        expected = Fraction(0) if h % 2 else Fraction(comb(h, h // 2), 2 ** h)
        assert Fraction(good, factorial(h)) == expected
    base = list(combinations(range(5), 2))
    counts = Counter()
    for flips in product(range(2), repeat=10):
        edges = [edge(2 * a + t, 2 * b + (t ^ flips[j]))
                 for j, (a, b) in enumerate(base) for t in range(2)]
        assert all(len(ns) == 4 for ns in adjacency(10, edges))
        counts[chromatic(10, edges)] += 1
    assert sum(counts.values()) == 1024
    assert counts[5] == 16  # h^-5 = 1/32 bounds this probability.
    assert counts.get(1, 0) == 0
    assert counts.get(2, 0) <= 512
    print("3310: even-cycle permutations through degree 8; all two-lift colour counts", dict(counts))


def domination_number(n, edges):
    adj = adjacency(n, edges)
    closed = [{v} | adj[v] for v in range(n)]
    for size in range(n + 1):
        for subset in combinations(range(n), size):
            if set().union(*(closed[v] for v in subset)) == set(range(n)):
                return size
    raise AssertionError


def check_domination():
    faces = [(0, 1, 2), (0, 1, 3), (1, 2, 3), (2, 0, 3)]
    private = [3]
    blocks = [{0, 1, 2, 3}]
    for count in range(1, 11):
        n = 4 * count
        edges = {edge(a, b) for f in faces for a, b in combinations(f, 2)}
        occurrences = Counter(edge(a, b) for f in faces for a, b in combinations(f, 2))
        assert len(edges) == 3 * n - 6
        assert len(faces) == 2 * n - 4
        assert set(occurrences.values()) == {2}
        adj = adjacency(n, edges)
        for z, block in zip(private, blocks):
            assert adj[z] | {z} == block
        dominators = [4 * i for i in range(count)]
        assert set().union(*(adj[v] | {v} for v in dominators)) == set(range(n))
        if count <= 3:
            assert domination_number(n, edges) == count
        if count == 10:
            break
        old = next(f for f in faces if not set(f) & set(private))
        faces.remove(old)
        a, b, c = old
        A, B, C, D = range(n, n + 4)
        faces.extend([(a, b, B), (b, c, C), (c, a, A), (a, A, B),
                      (b, B, C), (c, C, A), (A, B, D), (B, C, D), (C, A, D)])
        private.append(D)
        blocks.append({A, B, C, D})
    for m in range(4, 13):
        edges = {edge(i, (i + 1) % m) for i in range(m)}
        edges |= {edge(i, pole) for i in range(m) for pole in (m, m + 1)}
        assert len(edges) == 3 * (m + 2) - 6
        assert domination_number(m + 2, edges) == 2
    print("3311: ten exact-quarter triangulations and bipyramids with 6..14 vertices checked")


def degeneracy_order(n, edges, degree):
    adj = adjacency(n, edges)
    remaining = set(range(n))
    order = []
    while remaining:
        choices = [v for v in remaining if len(adj[v] & remaining) <= degree]
        if not choices:
            return None
        v = choices[0]
        order.append(v)
        remaining.remove(v)
    return order


def max_induced_forest(n, edges):
    best = 0
    for mask in range(1 << n):
        chosen = [e for e in edges if all(mask >> v & 1 for v in e)]
        if is_forest(n, chosen):
            best = max(best, mask.bit_count())
    return best


def check_induced_forests():
    checked = 0
    for n in range(1, 6):
        all_edges = list(combinations(range(n), 2))
        for mask in range(1 << len(all_edges)):
            edges = [e for i, e in enumerate(all_edges) if mask >> i & 1]
            order = degeneracy_order(n, edges, 3)
            if order is None:
                continue
            adj = adjacency(n, edges)
            classes = [set(), set()]
            for v in reversed(order):
                c = next(j for j in range(2) if len(adj[v] & classes[j]) <= 1)
                classes[c].add(v)
            for vertices in classes:
                assert is_forest(n, [e for e in edges if set(e) <= vertices])
            assert max(map(len, classes)) >= (n + 1) // 2
            checked += 1
    assert max_induced_forest(4, list(combinations(range(4), 2))) == 2
    octahedron = [e for e in combinations(range(6), 2) if e[0] // 2 != e[1] // 2]
    assert max_induced_forest(6, octahedron) == 3
    print("3312:", checked, "3-degenerate graphs and K4/octahedron induced-forest maxima checked")


def brute_sums(values):
    return {sum(a for j, a in enumerate(values) if mask >> j & 1)
            for mask in range(1 << len(values))}


def chunks(m):
    result = []
    step = 1
    while m:
        take = min(step, m)
        result.append(take)
        m -= take
        step *= 2
    return result


def check_subset_sum():
    for m in range(1, 26):
        cs = chunks(m)
        assert len(cs) == m.bit_length()
        assert brute_sums(cs) == set(range(m + 1))
    checked = 0
    for n in range(6):
        for values in product(range(-2, 3), repeat=n):
            sums = brute_sums(values)
            compressed = [v * c for v, m in Counter(values).items() if v != 0 for c in chunks(m)]
            assert brute_sums(compressed) == sums
            reachable = {0}
            for a in values:
                reachable = reachable | {s + a for s in reachable}
            assert reachable == sums
            split = n // 2
            assert {a + b for a in brute_sums(values[:split])
                    for b in brute_sums(values[split:])} == sums
            checked += 1
    print("3396:", checked, "signed lists and multiplicities 1..25 checked")


def sqrt_sum_interval(radicals, k):
    n = len(radicals)
    if not n:
        return True
    ceilings = [isqrt(a) + (isqrt(a) ** 2 != a) for a in radicals]
    B = max(1, k + sum(ceilings))
    C = B.bit_length()
    q = C * ((1 << n) - 1)
    p = q + n.bit_length() + 2  # ceil(log2(n+1)) = bit_length(n)
    scale = 1 << p
    A = sum(isqrt(a << (2 * p)) for a in radicals)
    assert n * (1 << q) < scale
    if A > k * scale:
        return False
    if A + n <= k * scale:
        return True
    return True  # Separation certificate forces equality.


def check_square_roots():
    checked = 0
    for a, b, k in product(range(31), range(31), range(16)):
        d = k * k - a - b
        expected = d >= 0 and d * d >= 4 * a * b
        assert sqrt_sum_interval([a, b], k) == expected
        checked += 1
    for n in range(5):
        for roots in product(range(4), repeat=n):
            for k in range(13):
                assert sqrt_sum_interval([r * r for r in roots], k) == (sum(roots) <= k)
    print("3399:", checked, "two-radical comparisons plus perfect-square lists checked")


def reduce_word(word):
    result = []
    for letter in word:
        if result and result[-1] == -letter:
            result.pop()
        else:
            result.append(letter)
    return result


def check_words():
    checked = 0
    for length in range(7):
        for w in product((-2, -1, 1, 2), repeat=length):
            reduced = reduce_word(w)
            if reduced:
                for power in range(1, 6):
                    assert reduce_word(list(w) * power)
            checked += 1
    for length in range(11):
        for w in product((-1, 1), repeat=length):
            assert (not reduce_word(w)) == (sum(w) == 0)
    print("3415/3419:", checked, "two-generator words and cyclic exponent tests checked")


def main():
    check_packing()
    check_cube()
    check_hypergraphs()
    check_random_colouring()
    check_forests()
    check_lifts()
    check_domination()
    check_induced_forests()
    check_subset_sum()
    check_square_roots()
    check_words()
    print("All finite checks passed. General targets are not inferred from finite tests.")


if __name__ == '__main__':
    main()
