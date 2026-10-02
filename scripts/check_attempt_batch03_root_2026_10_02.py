#!/usr/bin/env python3
"""Exact finite checks for twelve third-batch research attempts.

Standard library only. These validate the finite examples and algorithms
specified in the TeX files; they do not decide any unrestricted conjecture.
"""
from fractions import Fraction
from itertools import combinations, permutations, product
from math import comb, isqrt


def edge(u, v):
    return tuple(sorted((u, v)))


def adjacency(vertices, edges):
    result = {v: set() for v in vertices}
    for u, v in edges:
        result[u].add(v)
        result[v].add(u)
    return result


def connected(adj, removed=()):
    remaining = set(adj) - set(removed)
    if not remaining:
        return True
    seen = {next(iter(remaining))}
    queue = list(seen)
    for v in queue:
        for w in adj[v] & remaining - seen:
            seen.add(w)
            queue.append(w)
    return seen == remaining


def check_torus():
    for m, n in product(range(3, 13), repeat=2):
        vertices = list(product(range(m), range(n)))
        horizontal = {edge((i, j), (i, (j+1) % n)) for i, j in vertices}
        edges = horizontal | {edge((i, j), ((i+1) % m, j)) for i, j in vertices}
        cycle = horizontal.copy()
        for i in range(m-1):
            a, b = (0, 1) if i % 2 == 0 else (1, 2)
            cycle.remove(edge((i, a), (i, b)))
            cycle.remove(edge((i+1, a), (i+1, b)))
            cycle.update((edge((i, a), (i+1, a)), edge((i, b), (i+1, b))))
        assert cycle <= edges and len(cycle) == m*n
        adj = adjacency(vertices, cycle)
        assert all(len(a) == 2 for a in adj.values()) and connected(adj)
        if m <= 6 and n <= 6:
            adj = adjacency(vertices, edges)
            assert all(len(a) == 4 for a in adj.values())
            for size in range(4):
                assert all(connected(adj, deleted) for deleted in combinations(vertices, size))
    print('3313: 100 toroidal Hamilton cycles; all <=3-vertex deletions on 16 products passed')


def degeneracy(adj, vertices):
    remaining = set(vertices)
    result = 0
    while remaining:
        v = min(remaining, key=lambda x: len(adj[x] & remaining))
        result = max(result, len(adj[v] & remaining))
        remaining.remove(v)
    return result


def check_degenerate_colouring():
    edges = {edge(i, (i+1) % 3) for i in range(3)}
    edges |= {edge(i+3, (i+1) % 3+3) for i in range(3)}
    edges |= {edge(i, i+3) for i in range(3)}
    adj = adjacency(range(6), edges)
    colours = [0, 1, 2, 1, 2, 0]
    for pair in combinations(range(3), 2):
        vertices = {v for v in adj if colours[v] in pair}
        induced = {e for e in edges if set(e) <= vertices}
        assert len(induced) == 3
        assert connected(adjacency(vertices, induced))
        assert sorted(len(adj[v] & vertices) for v in vertices) == [1, 1, 2, 2]
    assert degeneracy(adj, range(6)) == 3
    edges = set(combinations(range(4), 2))
    faces = list(combinations(range(4), 3))
    for size in range(4, 45):
        if size > 4:
            v = size-1
            face = faces.pop((7*v) % len(faces))
            edges.update(edge(v, w) for w in face)
            faces.extend(tuple(sorted((v, x, y))) for x, y in combinations(face, 2))
        adj = adjacency(range(size), edges)
        order = list(range(size-1, 3, -1)) + list(range(4))
        colouring = {}
        for v in reversed(order):
            forbidden = {colouring[w] for w in adj[v] if w in colouring}
            colouring[v] = min(set(range(4)) - forbidden)
        for k in range(1, 5):
            for palette in combinations(range(5), k):
                vertices = {v for v in adj if colouring[v] in palette}
                assert degeneracy(adj, vertices) <= k-1
    print('3316: prism obstruction and all palette subsets on 41 stacked triangulations passed')


def check_circle_labels():
    counts = {}
    for m in (3, 4):
        colour = ({(0, 1): 0, (0, 2): 1, (1, 2): 2} if m == 3 else
                  {(0, 1): 0, (2, 3): 0, (0, 2): 1, (1, 3): 1, (0, 3): 2, (1, 2): 2})
        orders = [list(permutations([j for j in range(m) if j != i])) for i in range(m)]
        count = 0
        for local_orders in product(*orders):
            for i, order in enumerate(local_orders):
                labels = list(order) * 2
                values = [colour[edge(i, j)] for j in labels]
                assert all(x != y for x, y in zip(values, values[1:] + values[:1]))
            count += 1
        counts[m] = count
    assert counts == {3: 8, 4: 1296}
    print('3317: all 8 and 1296 local-order combinations passed')


def orient(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def crossings(points, edges):
    result = 0
    for (u, v), (x, y) in combinations(edges, 2):
        if len({u, v, x, y}) != 4:
            continue
        a, b, c, d = [points[z] for z in (u, v, x, y)]
        result += (orient(a, b, c)*orient(a, b, d) < 0
                   and orient(c, d, a)*orient(c, d, b) < 0)
    return result


def axial(m, n):
    def positions(size):
        return list(range(1, (size+1)//2+1)) + list(range(-1, -(size//2)-1, -1))
    points = [(x, 0) for x in positions(m)] + [(0, y) for y in positions(n)]
    return points, [(i, m+j) for i in range(m) for j in range(n)]


def check_crossings():
    for m, n in product(range(1, 13), repeat=2):
        points, edges = axial(m, n)
        z = (m//2)*((m-1)//2)*(n//2)*((n-1)//2)
        assert crossings(points, edges) == z
        if (m, n) in ((3, 3), (3, 4), (3, 5), (4, 4)):
            lower = Fraction(m*(m-1)*n*(n-1), 36)
            assert -(-lower.numerator//lower.denominator) == z
    k5 = [(0, 0), (10, 0), (5, 10), (4, 3), (6, 3)]
    assert crossings(k5, list(combinations(range(5), 2))) == 1
    for a, b, c in combinations(k5, 3):
        assert orient(a, b, c) != 0
    assert crossings(*axial(3, 3)) == 1
    for t in range(9, 101):
        threshold = Fraction(512*comb(t, 4), (t-1)**3)
        n = -(-threshold.numerator//threshold.denominator)
        assert Fraction((t-1)**3*n, 512) >= comb(t, 4)
        assert Fraction((t-1)**3*(n-1), 512) < comb(t, 4)
    print('3319/3323/3324: 144 axial pair counts, one-crossing K5/K3,3 and 92 critical thresholds passed')


def pruefer_tree(n, code):
    if n == 1:
        return []
    degrees = [1]*n
    for x in code:
        degrees[x] += 1
    result = []
    for x in code:
        leaf = next(i for i, d in enumerate(degrees) if d == 1)
        result.append(edge(leaf, x))
        degrees[leaf] -= 1
        degrees[x] -= 1
    result.append(tuple(i for i, d in enumerate(degrees) if d == 1))
    return result


def check_tree_points():
    count = 0
    for n in range(1, 7):
        for code in product(range(n), repeat=max(0, n-2)):
            edges = pruefer_tree(n, code)
            adj = adjacency(range(n), edges)
            order = []
            def visit(v, parent):
                order.append(v)
                for w in sorted(adj[v] - {parent}):
                    visit(w, v)
            visit(0, -1)
            points = {v: (i, i*i) for i, v in enumerate(order)}
            assert crossings(points, edges) == 0
            count += 1
    assert count == 1442
    edges = list(combinations(range(4), 2))
    assert crossings([(i, i*i) for i in range(4)], edges) == 1
    assert crossings([(0, 0), (10, 0), (5, 10), (5, 3)], edges) == 0
    print('3325: all 1442 labelled trees through order six and both K4 configurations passed')


def check_logic_examples():
    assert [n for n in range(1, 65) if 2**n <= n*n] == [2, 3, 4]
    for d in range(2, 7):
        base = 2*d*(d+1)
        for q, remainder in product(range(1, 4), range(6)):
            total = q*base + remainder
            gs, hs = set(), set()
            for start in range(0, q*base, d+1):
                gs.update(combinations(range(start, start+d+1), 2))
            for start in range(0, q*base, 2*d):
                hs.update((u, v) for u in range(start, start+d) for v in range(start+d, start+2*d))
            g, h = adjacency(range(total), gs), adjacency(range(total), hs)
            for adj in (g, h):
                assert [len(adj[v]) for v in range(total)] == [d]*(q*base) + [0]*remainder
            def triangle(adj):
                return any(adj[u] & adj[v] for u in adj for v in adj[u])
            assert triangle(g) and not triangle(h)
            assert Fraction(q*2*d*d, q*d*(d+1)) == 2-Fraction(2, d+1)
    print('3341/3343: finite balanced support and 90 counting-logic graph pairs passed')


def bsgs(p, g, h):
    n = p-1
    m = isqrt(n)
    m += m*m < n
    table, value = {}, 1
    for j in range(m):
        table.setdefault(value, j)
        value = value*g % p
    jump, target = pow(g, -m, p), h
    for i in range(m):
        if target in table:
            answer = (i*m+table[target]) % n
            assert pow(g, answer, p) == h
            return answer
        target = target*jump % p
    raise AssertionError('promised logarithm missing')


def binary_log(p, g, h):
    power, t = g, 0
    while power != 1:
        power = power*power % p
        t += 1
    assert t > 0 and pow(g, 2**(t-1), p) == p-1
    a = 0
    for j in range(t):
        z = pow(h*pow(g, -a, p) % p, 2**(t-j-1), p)
        assert z in (1, p-1)
        if z == p-1:
            a += 2**j
    assert 0 <= a < 2**t and pow(g, a, p) == h
    return a


def check_logs():
    count_general = count_binary = 0
    for p in (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43):
        for g in range(2, p):
            for h in {pow(g, a, p) for a in range(p-1)}:
                assert pow(g, bsgs(p, g, h), p) == h
                count_general += 1
    for p in (3, 5, 17, 257):
        for g in range(2, p):
            for h in {pow(g, a, p) for a in range(p-1)}:
                assert pow(g, binary_log(p, g, h), p) == h
                count_binary += 1
    print(f'3401: {count_general} general and {count_binary} binary logarithm cases passed')


def check_translate_covers():
    cases = 0
    for m in range(1, 4):
        size, k = 2**m, m+1
        full = set(range(size))
        for mask in range(2**size):
            accept = {i for i in full if mask >> i & 1}
            if 4*len(accept) >= 3*size:
                translates = [{x ^ a for x in accept} for a in full]
                assert any(set().union(*(translates[a] for a in shifts)) == full
                           for shifts in combinations(range(size), min(k, size)))
                cases += 1
            if 2*k*len(accept) < size:
                # Even the sum of all k cardinalities is strictly below the cube size.
                assert k*len(accept) < size
    print(f'3404: {cases} dense subsets of cubes through dimension three have translate covers')


def excursion_meeting(amplitude, first, second):
    # Piecewise affine global separation on the outward and return legs.
    previous_t, previous_gap = Fraction(0), Fraction(2)
    for end_t, displacement in ((amplitude, amplitude), (2*amplitude, Fraction(0))):
        gap = 2+(second-first)*displacement
        if gap == 0:
            return end_t
        if gap*previous_gap < 0:
            return previous_t + previous_gap*(end_t-previous_t)/(previous_gap-gap)
        previous_t, previous_gap = end_t, gap
    return None


def check_rendezvous():
    for amplitude in map(Fraction, (Fraction(1, 2), 1, Fraction(3, 2), 2)):
        results = [excursion_meeting(amplitude, a, b) for a, b in product((-1, 1), repeat=2)]
        assert results.count(Fraction(1)) == (1 if amplitude >= 1 else 0)
        assert results.count(None) == (3 if amplitude >= 1 else 4)
        if amplitude >= 1:
            for limit in (1, 2, 7, 20):
                rho = Fraction(3, 4)
                finite = sum((1+2*amplitude*j)*rho**j/4 for j in range(limit))
                tail = rho**limit*(1+2*amplitude*(limit+3))
                assert finite+tail == 1+6*amplitude
    print('3447: all excursion orientations at four rational amplitudes and exact geometric tails passed')


if __name__ == '__main__':
    for check in (check_torus, check_degenerate_colouring, check_circle_labels,
                  check_crossings, check_tree_points, check_logic_examples,
                  check_logs, check_translate_covers, check_rendezvous):
        check()
    print('All root-group finite checks passed; unrestricted statements are not certified.')
