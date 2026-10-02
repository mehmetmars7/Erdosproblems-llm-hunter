#!/usr/bin/env python3
"""Exact certificates for the 2026-10-02 digraph/3398 Ultra attempts.

Run from any directory with Python 3. No third-party packages, network,
randomness, or generated repository outputs. These bounded checks certify
only the examples and finite ranges explicitly stated in the TeX attempts.
"""
from collections import deque
from functools import lru_cache
from itertools import combinations, permutations, product
from math import ceil, gcd


def adjacency(n, arcs):
    out = [set() for _ in range(n)]
    for u, v in arcs:
        assert 0 <= u < n and 0 <= v < n and u != v
        out[u].add(v)
    return out


def reachable(n, arcs, source):
    out = adjacency(n, arcs)
    seen, queue = {source}, [source]
    for u in queue:
        for v in out[u] - seen:
            seen.add(v)
            queue.append(v)
    return seen


def strong(n, arcs):
    return all(len(reachable(n, arcs, v)) == n for v in range(n))


def acyclic(n, arcs, vertices=None):
    vertices = set(range(n)) if vertices is None else set(vertices)
    out = adjacency(n, arcs)
    indeg = {v: 0 for v in vertices}
    for u in vertices:
        for v in out[u] & vertices:
            indeg[v] += 1
    queue = [v for v in vertices if indeg[v] == 0]
    for u in queue:
        for v in out[u] & vertices:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return len(queue) == len(vertices)


def girth(n, arcs):
    out = adjacency(n, arcs)
    best = n + 1
    for start in range(n):
        distance = {start: 0}
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for v in out[u]:
                if v == start:
                    best = min(best, distance[u] + 1)
                elif v not in distance:
                    distance[v] = distance[u] + 1
                    queue.append(v)
    return best


def cycles(n, arcs):
    out = adjacency(n, arcs)
    answer = []
    for start in range(n):
        def visit(path):
            u = path[-1]
            if start in out[u] and len(path) >= 2:
                answer.append(tuple(path))
            for v in out[u]:
                if v > start and v not in path:
                    visit(path + [v])
        visit([start])
    return answer


def cycle_arcs(cycle):
    return {(cycle[i], cycle[(i + 1) % len(cycle)]) for i in range(len(cycle))}


def circulant(n, r):
    return {(x, (x + step) % n) for x in range(n) for step in range(1, r + 1)}


def degrees(n, arcs):
    return ([sum(u == x for u, _ in arcs) for x in range(n)],
            [sum(v == x for _, v in arcs) for x in range(n)])


def check_3259():
    for q in range(1, 5):
        n = 4 * q
        vertex = lambda block, index: block * q + index
        arcs = {(vertex(b, i), vertex(b, j)) for b in range(4)
                for i in range(q) for j in range(i + 1, q)}
        arcs |= {(vertex(b, i), vertex((b + 1) % 4, j))
                 for b in range(4) for i in range(q) for j in range(q)}
        missing = sum((u, v) not in arcs and (v, u) not in arcs
                      for u, v in combinations(range(n), 2))
        assert missing == 2 * q * q
        assert all(not {(a, b), (b, c), (c, a)} <= arcs
                   for a, b, c in permutations(range(n), 3))
        used = set()
        for i, j in product(range(q), repeat=2):
            cert = cycle_arcs((vertex(0, i), vertex(1, j), vertex(2, i), vertex(3, j)))
            assert cert <= arcs and used.isdisjoint(cert)
            used |= cert
        deleted = {(vertex(0, i), vertex(1, j)) for i, j in product(range(q), repeat=2)}
        assert len(deleted) == q * q and acyclic(n, arcs - deleted)
    print('3259: sharp blow-ups q=1..4, triangle restrictions and deletion certificates passed')


def check_3260():
    for k in range(2, 11):
        n = 2 * k - 3
        arcs = circulant(n, k - 2)
        out, inc = degrees(n, arcs)
        assert out == inc == [k - 2] * n
        assert len(arcs) == n * (n - 1) // 2
    for n in range(1, 8):
        arcs = {(i, j) for i in range(n) for j in range(i + 1, n)}
        for mask in range(1, 1 << n):
            vertices = {i for i in range(n) if mask >> i & 1}
            assert not any(v == min(vertices) and u in vertices for u, v in arcs)
            assert not any(u == max(vertices) and v in vertices for u, v in arcs)
    print('3260: regular star obstruction and all nonempty transitive subtournaments through n=7 passed')


def check_3262():
    tested = 0
    for n in range(1, 5):
        pairs = list(combinations(range(n), 2))
        for states in product(range(3), repeat=len(pairs)):
            arcs = {(u, v) if state == 1 else (v, u)
                    for (u, v), state in zip(pairs, states) if state}
            k = min(degrees(n, arcs)[0])
            if k:
                assert max(map(len, cycles(n, arcs))) >= k + 2
                tested += 1
    for n in range(1, 6):
        pairs = list(combinations(range(n), 2))
        for states in product(range(2), repeat=len(pairs)):
            arcs = {(v, u) if state else (u, v) for (u, v), state in zip(pairs, states)}
            path = []
            for x in range(n):
                i = next((i for i, v in enumerate(path) if (x, v) in arcs), len(path))
                path.insert(i, x)
            assert len(set(path)) == n
            assert all((u, v) in arcs for u, v in zip(path, path[1:]))
            k = min(degrees(n, arcs)[0])
            assert len(path) - 1 >= 2 * k
    print(f'3262: {tested} positive-outdegree oriented graphs through n=4 and all tournaments through n=5 passed')


def check_3263():
    for n in range(2, 31):
        for r in range(1, n):
            assert girth(n, circulant(n, r)) == ceil(n / r)
    arcs = circulant(5, 2) - {(0, 2)} | {(0, 3)}
    assert strong(5, arcs)
    assert degrees(5, arcs) == ([2] * 5, [2, 2, 1, 3, 2])
    out = adjacency(10, circulant(10, 2))
    assert out[0] & out[1] == {2} and girth(10, circulant(10, 2)) == 5
    print('3263: 435 circulant girths and outregular imbalance/branch-merging examples passed')


def check_3266():
    for d in range(1, 4):
        order = 2 * d + 1
        arcs = circulant(order, d)
        mapped = lambda x: 0 if x == 0 else x + 2 * d
        arcs |= {(mapped(u), mapped(v)) for u, v in circulant(order, d)}
        n = 4 * d + 1
        out, inc = degrees(n, arcs)
        assert out == inc == [2 * d] + [d] * (n - 1)
        assert strong(n, arcs)
        assert max(map(len, cycles(n, arcs))) == 2 * d + 1
    print('3266: strong sharp examples d=1,2,3 and their longest cycles passed')


def check_3267():
    for n in range(3, 13):
        for u, v in product(range(n), repeat=2):
            if u == v:
                plus = {(u, x) for x in range(n) if x != u}
                minus = {(x, u) for x in range(n) if x != u}
            else:
                w = next(x for x in range(n) if x not in (u, v))
                plus = {(u, x) for x in range(n) if x not in (u, w)} | {(v, w)}
                minus = {(x, v) for x in range(n) if x not in (v, u)} | {(u, w)}
            assert len(plus) == len(minus) == n - 1 and plus.isdisjoint(minus)
            assert degrees(n, plus)[1] == [int(x != u) for x in range(n)]
            assert degrees(n, minus)[0] == [int(x != v) for x in range(n)]
            assert len(reachable(n, plus, u)) == n
            assert all(v in reachable(n, minus, x) for x in range(n))
    print('3267: complete symmetric branchings n=3..12 for every ordered root pair passed')


def check_3270():
    certificate = [(0, 3, 1), (1, 4, 2), (2, 5, 0)]
    assert all(len(set(a) & set(b)) == 1 for a, b in combinations(certificate, 2))
    assert all(len(set(order[2]) & (set(order[0]) | set(order[1]))) == 2
               for order in permutations(certificate))
    for k in range(1, 9):
        used_vertices, used_arcs = set(), set()
        for i in range(1, k + 1):
            cert = (0, i)
            assert len(set(cert) & used_vertices) <= 1
            assert cycle_arcs(cert).isdisjoint(used_arcs)
            used_vertices |= set(cert)
            used_arcs |= cycle_arcs(cert)
    for n in range(2, 101):
        for k in range(1, n):
            assert (n - 1) // k + 1 == ceil(n / k)
    print('3270: six overlap-order obstructions, symmetric certificates and ceiling identity passed')


def check_3271():
    arcs = circulant(5, 2)
    packing = [(0, 1, 3), (0, 2, 4), (1, 2, 3, 4)]
    used = set()
    for cert in packing:
        edges = cycle_arcs(cert)
        assert edges <= arcs and used.isdisjoint(edges)
        used |= edges
    assert used == arcs
    for k in range(1, 13):
        n = k + 1
        arcs = {(u, v) for u in range(n) for v in range(n) if u != v}
        certs = [cycle_arcs((u, v)) for u, v in combinations(range(n), 2)]
        assert len(certs) == k * (k + 1) // 2
        assert sum(map(len, certs)) == len(set.union(*certs)) == len(arcs)
    print('3271: degree-two nonsymmetric packing and sharp symmetric counts passed')


def check_3273():
    n = 7
    arcs = {(0, 1), (1, 2), (2, 0), (3, 4), (0, 3), (1, 3), (4, 0), (4, 1),
            (5, 6), (3, 5), (4, 5), (6, 3), (6, 4)}
    assert not any((v, u) in arcs for u, v in arcs)
    edges = {frozenset((u, v)) for u, v in arcs}
    faces = {frozenset((0, 1, 2))}
    planar_supergraph = {frozenset(p) for p in combinations(range(3), 2)}
    for vertex, face in [(4, (0, 1, 2)), (3, (0, 1, 4)),
                         (6, (0, 3, 4)), (5, (3, 4, 6))]:
        face = frozenset(face)
        assert face in faces
        faces.remove(face)
        planar_supergraph |= {frozenset((vertex, u)) for u in face}
        faces |= {frozenset((vertex, u, v)) for u, v in combinations(face, 2)}
    assert planar_supergraph - edges == {frozenset((2, 4)), frozenset((0, 6))}
    triangles = [(0, 1, 2), (0, 3, 4), (1, 3, 4), (3, 5, 6), (4, 5, 6)]
    assert all(cycle_arcs(c) <= arcs for c in triangles)
    assert all(any(not (set(pair) & set(c)) for c in triangles)
               for pair in combinations(range(n), 2))
    maximum = max(mask.bit_count() for mask in range(1 << n)
                  if acyclic(n, arcs, (v for v in range(n) if mask >> v & 1)))
    assert maximum == 4 < ceil(3 * n / 5)
    assert acyclic(n, arcs, {1, 2, 4, 6})
    print('3273: face-insertion planarity certificate and all 128 induced subsets; maximum acyclic size=4 passed')


def check_3276():
    counts = []
    for n in range(1, 5):
        pairs = list(combinations(range(n), 2))
        eligible = 0
        for states in product(range(6), repeat=len(pairs)):
            colours = {(v, u) if state // 3 else (u, v): state % 3
                       for (u, v), state in zip(pairs, states)}
            rainbow = False
            for a, b, c in combinations(range(n), 3):
                for trip in [((a, b), (b, c), (c, a)), ((a, c), (c, b), (b, a))]:
                    if all(edge in colours for edge in trip) and len({colours[e] for e in trip}) == 3:
                        rainbow = True
            if rainbow:
                continue
            eligible += 1
            monochrome = [{e for e, col in colours.items() if col == i} for i in range(3)]
            assert any(set.union(*(reachable(n, arcs, v) for arcs in monochrome)) == set(range(n))
                       for v in range(n))
        counts.append(eligible)
    # Admissible red/blue triangle: union of colour reachability is not transitive.
    red, blue = {(0, 1), (2, 0)}, {(1, 2)}
    assert 1 in reachable(3, red, 0) and 2 in reachable(3, blue, 1)
    assert 2 not in reachable(3, red, 0) | reachable(3, blue, 0)
    print(f'3276: exhaustive admissible counts by n=1..4: {counts}; all roots verified')


def excess(n, arcs):
    out, inc = degrees(n, arcs)
    return sum(max(0, a - b) for a, b in zip(out, inc))


def paired_dag_paths(n, arcs):
    successor, predecessor = {}, {}
    for v in range(n):
        incoming = sorted(e for e in arcs if e[1] == v)
        outgoing = sorted(e for e in arcs if e[0] == v)
        for incoming_edge, outgoing_edge in zip(incoming, outgoing):
            successor[incoming_edge] = outgoing_edge
            predecessor[outgoing_edge] = incoming_edge
    paths, used = [], set()
    for arc in sorted(arcs - predecessor.keys()):
        path = [arc[0]]
        while True:
            assert arc not in used
            used.add(arc)
            path.append(arc[1])
            if arc not in successor:
                break
            arc = successor[arc]
        assert len(set(path)) == len(path)
        paths.append(path)
    assert used == arcs
    return paths


def minimum_path_partition(n, arcs):
    index = {arc: i for i, arc in enumerate(sorted(arcs))}
    out = adjacency(n, arcs)
    masks = set()
    def extend(path, mask):
        if mask:
            masks.add(mask)
        for v in out[path[-1]]:
            if v not in path:
                extend(path + [v], mask | (1 << index[path[-1], v]))
    for v in range(n):
        extend([v], 0)
    @lru_cache(None)
    def solve(remaining):
        if not remaining:
            return 0
        first = remaining & -remaining
        return 1 + min(solve(remaining ^ mask) for mask in masks
                       if mask & first and mask & remaining == mask)
    return solve((1 << len(arcs)) - 1)


def check_3277():
    for n in range(2, 21, 2):
        arcs = {(u, v) for u, v in combinations(range(n), 2)}
        paths = paired_dag_paths(n, arcs)
        assert len(paths) == excess(n, arcs) == (n // 2) ** 2
    pairs = list(combinations(range(4), 2))
    for states in product(range(2), repeat=len(pairs)):
        arcs = {(v, u) if state else (u, v) for (u, v), state in zip(pairs, states)}
        assert minimum_path_partition(4, arcs) == excess(4, arcs)
    arcs = {(0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3)}
    paths = [(0, 1, 2, 3), (1, 3), (2, 0, 3)]
    used = [(u, v) for path in paths for u, v in zip(path, path[1:])]
    assert len(used) == len(set(used)) and set(used) == arcs and excess(4, arcs) == 3
    assert cycle_arcs((0, 1, 2)) <= arcs
    print('3277: acyclic pairing through n=20, all 64 tournaments of order four, and repair certificate passed')


def check_3280():
    for n in [3, 5, 7, 11, 13]:
        k = (n - 1) // 2
        arcs = circulant(n, k)
        used = set()
        for step in range(1, k + 1):
            part = {(x, (x + step) % n) for x in range(n)}
            assert len(part) == n and strong(n, part) and part.isdisjoint(used)
            used |= part
        assert used == arcs
        for mask in range(1, (1 << n) - 1):
            s = mask.bit_count()
            crossing = sum(bool(mask >> u & 1) and not (mask >> v & 1) for u, v in arcs)
            assert crossing == s * (n - s) // 2 >= k
    step_three = {(x, (x + 3) % 9) for x in range(9)}
    assert not strong(9, step_three)
    assert len(cycles(9, step_three)) == gcd(9, 3) == 3
    print('3280: five prime Hamilton partitions, every cut, and composite-order factor obstruction passed')


def equal_sums(values):
    table = {0: 0}
    for i, a in enumerate(values):
        snapshot = list(table.items())
        added = {}
        for total, mask in snapshot:
            shifted, witness = total + a, mask | (1 << i)
            if shifted in table:
                other = table[shifted]
                return witness & ~other, other & ~witness
            added[shifted] = witness
        table.update(added)
    return None


def check_3398():
    count = 0
    def verify(values):
        nonlocal count
        assert sum(values) < (1 << len(values)) - 1
        first, second = equal_sums(values)
        assert first and second and not first & second
        assert first < (1 << len(values)) and second < (1 << len(values))
        assert sum(a for i, a in enumerate(values) if first >> i & 1) == sum(
            a for i, a in enumerate(values) if second >> i & 1)
        count += 1
    for n in range(1, 6):
        for values in product(range(1, 7), repeat=n):
            if sum(values) < (1 << n) - 1:
                verify(values)
    for n in range(3, 17):
        verify([1 << i for i in range(n - 1)] + [(1 << (n - 2)) - 1])
    verify([3, 5, 6, 7, 8])
    assert equal_sums([3, 5, 6]) is None
    assert sorted(sum(a for i, a in enumerate([3, 5, 6]) if mask >> i & 1)
                  for mask in range(8)) == [0, 3, 5, 6, 8, 9, 11, 14]
    assert sum([1, 2, 3, 4]) < 15 and 1 % 3 == 4 % 3 and 1 != 4
    print(f'3398: {count} promised inputs with disjoint, nonempty exact witnesses passed')


if __name__ == '__main__':
    for check in [check_3259, check_3260, check_3262, check_3263, check_3266,
                  check_3267, check_3270, check_3271, check_3273, check_3276,
                  check_3277, check_3280, check_3398]:
        check()
    print('All 13 exact-check groups passed. No unrestricted conjecture is certified by these finite checks.')
