#!/usr/bin/env python3
"""Exact finite checks cited in the second 2026-10-01 graph-attempt batch.

Standard library only. Run from the repository root with Python 3.
The finite certificates do not establish any unrestricted catalogue conjecture.
For 3195 only the ordinary total colouring is checked, not the bad-list proof.
For 3196 no published counterexample is independently certified here.
"""
from collections import Counter
from itertools import combinations, product


def edge(u, v):
    assert u != v
    return frozenset((u, v))


def adjacency(vertices, edges):
    result = {v: set() for v in vertices}
    for e in edges:
        assert len(e) == 2
        u, v = tuple(e)
        result[u].add(v)
        result[v].add(u)
    return result


def components(vertices, edges):
    adj = adjacency(vertices, edges)
    unseen = set(vertices)
    result = []
    while unseen:
        start = next(iter(unseen))
        found, stack = {start}, [start]
        unseen.remove(start)
        while stack:
            v = stack.pop()
            for w in adj[v] & unseen:
                unseen.remove(w)
                found.add(w)
                stack.append(w)
        result.append(found)
    return result


def cycle_edges(order):
    assert len(order) == len(set(order)) >= 3
    return {edge(order[i], order[(i + 1) % len(order)]) for i in range(len(order))}


def perfect(vertices, matching):
    counts = Counter(v for e in matching for v in e)
    return set(counts) == set(vertices) and all(counts[v] == 1 for v in vertices)


def prism(vertices, edges):
    verts = {(v, b) for v in vertices for b in range(2)}
    result = {edge((v, 0), (v, 1)) for v in vertices}
    for e in edges:
        u, v = tuple(e)
        result.update(edge((u, b), (v, b)) for b in range(2))
    return verts, result


def check_prisms():
    verts = set(range(4))
    base = {edge(u, v) for u, v in combinations(verts, 2)}
    pv, pe = prism(verts, base)
    c1 = cycle_edges([(0, 0), (3, 0), (2, 0), (1, 0), (1, 1), (2, 1), (3, 1), (0, 1)])
    c2 = cycle_edges([(0, 0), (1, 0), (3, 0), (3, 1), (1, 1), (0, 1), (2, 1), (2, 0)])
    assert not c1 & c2 and c1 | c2 == pe
    for m in range(3, 13):
        v = set(range(2 * m))
        e = {edge(i, (i + 1) % m) for i in range(m)}
        e |= {edge(m + i, m + (i + 1) % m) for i in range(m)}
        e |= {edge(i, m + i) for i in range(m)}
        order = list(range(m)) + list(range(2 * m - 1, m - 1, -1))
        h = cycle_edges(order)
        assert h <= e and perfect(v, e - h)
        pv, pe = prism(v, e)
        c = set()
        for he in h:
            x, y = tuple(he)
            c |= {edge((x, b), (y, b)) for b in range(2)}
        c -= {edge((0, b), (1, b)) for b in range(2)}
        c |= {edge((u, 0), (u, 1)) for u in (0, 1)}
        assert len(components(pv, c)) == 1
        assert all(len(n) == 2 for n in adjacency(pv, c).values())
        complement = pe - c
        assert all(len(n) == 2 for n in adjacency(pv, complement).values())
        assert len(components(pv, complement)) == m - 1
    print('3178: K4 prism decomposition and 10 circular-ladder splice counts verified')


def petersen():
    vertices = set(range(10))
    edges = {edge(i, (i + 1) % 5) for i in range(5)}
    edges |= {edge(i, i + 5) for i in range(5)}
    edges |= {edge(i + 5, (i + 2) % 5 + 5) for i in range(5)}
    matches = [{edge(i, i + 5) for i in range(5)}]
    for i in range(5):
        a = lambda j: (i + j) % 5
        b = lambda j: (i + j) % 5 + 5
        matches.append({edge(a(0), b(0)), edge(a(1), a(2)), edge(a(3), a(4)),
                        edge(b(2), b(4)), edge(b(1), b(3))})
    return vertices, edges, matches


def check_matching_claims():
    vertices, edges, matches = petersen()
    assert len(edges) == 15 and all(len(ns) == 3 for ns in adjacency(vertices, edges).values())
    assert all(m <= edges and perfect(vertices, m) for m in matches)
    assert Counter(e for m in matches for e in m) == Counter({e: 2 for e in edges})
    intersection = matches[0] & matches[1]
    assert intersection == {edge(0, 5)}
    checked = 0
    for bits in range(1, (1 << 10) - 1):
        shore = {v for v in vertices if bits & (1 << v)}
        cut = {e for e in edges if len(e & shore) == 1}
        assert len(cut) != 1  # bridgelessness, checked for every shore
        assert (len(cut) - len(shore)) % 2 == 0
        if len(cut) % 2:
            assert not cut <= intersection
            assert all(len(m & cut) % 2 for m in matches)
        checked += 1
    assert all(len(c) % 2 == 0 for c in components(vertices, edges - intersection))
    print(f'3179/3180: six Petersen matchings, double cover, and {checked} cut shores verified')


def check_hypercubes():
    for d in range(2, 9):
        n = 1 << (d - 1)
        gray = [i ^ (i >> 1) for i in range(n)]
        order = []
        for i, x in enumerate(gray):
            order.extend((2 * x + b) for b in ((0, 1) if i % 2 == 0 else (1, 0)))
        cycle = cycle_edges(order)
        assert set(order) == set(range(1 << d))
        assert all((u ^ v).bit_count() == 1 for u, v in map(tuple, cycle))
        assert {edge(2 * x, 2 * x + 1) for x in range(n)} <= cycle
    required = {edge(1, 3), edge(2, 6), edge(4, 5)}
    assert len(set().union(*required)) == 6
    remaining = set(range(8)) - set().union(*required)
    assert remaining == {0, 7} and (0 ^ 7).bit_count() != 1
    order = [0, 1, 3, 2, 6, 7, 5, 4]
    assert required <= cycle_edges(order)
    assert all((u ^ v).bit_count() == 1 for u, v in map(tuple, cycle_edges(order)))
    print('3181: coordinate cycles in dimensions 2..8 and Q3 completion obstruction verified')


def check_minor_and_seagulls():
    vertices = set(range(8))
    # Part i consists of i and i+4. All cross-part edges are present.
    edges = {edge(u, v) for u, v in combinations(vertices, 2) if u % 4 != v % 4}
    branches = [{i} for i in range(4)] + [{4, 5}, {6, 7}]
    assert set().union(*branches) == vertices
    for b in branches:
        assert len(components(b, {e for e in edges if e <= b})) == 1
    for b, c in combinations(branches, 2):
        assert not b & c and any(edge(u, v) in edges for u in b for v in c)
    for t in range(1, 7):
        vertices = set(range(3 * t))
        missing = {edge(3 * i, 3 * i + 2) for i in range(t)}
        edges = {edge(u, v) for u, v in combinations(vertices, 2)} - missing
        assert missing
        assert all(any(edge(u, v) in edges for u, v in combinations(s, 2))
                   for s in combinations(vertices, 3))
        for i in range(t):
            triple = {3 * i, 3 * i + 1, 3 * i + 2}
            assert len({e for e in edges if e <= triple}) == 2
        clique = {3 * i + j for i in range(t) for j in (0, 1)}
        assert len(clique) == 2 * t
        assert all(edge(u, v) in edges for u, v in combinations(clique, 2))
    print('3184/3185: six-branch minor and six seagull-accounting examples verified')


def triangle_expansion(vertices, edges):
    adj = adjacency(vertices, edges)
    ports = {(v, w) for v in vertices for w in adj[v]}
    expanded = {edge((u, v), (v, u)) for u, v in map(tuple, edges)}
    paths = []
    for v in sorted(vertices):
        triple = [(v, w) for w in sorted(adj[v])]
        assert len(triple) == 3
        expanded |= {edge(u, w) for u, w in combinations(triple, 2)}
        paths.append(triple)
    return ports, expanded, paths


def check_expansions():
    pv, pe, _ = petersen()
    examples = [(set(range(4)), {edge(u, v) for u, v in combinations(range(4), 2)}), (pv, pe)]
    deletions = 0
    for vertices, edges in examples:
        v, e, paths = triangle_expansion(vertices, edges)
        assert all(len(n) == 3 for n in adjacency(v, e).values())
        covered = [x for p in paths for x in p]
        assert len(covered) == len(set(covered)) == len(v)
        assert set(covered) == v
        assert all(edge(p[i], p[i + 1]) in e for p in paths for i in (0, 1))
        for k in range(3):
            for removed in combinations(sorted(v), k):
                rest = v - set(removed)
                assert len(components(rest, {x for x in e if x <= rest})) == 1
                deletions += 1
    print(f'3189: K4/Petersen triangle expansions, factors, and {deletions} vertex deletions verified')


def check_chvatal():
    data = {0: [1, 4, 6, 9], 1: [2, 5, 7], 2: [3, 6, 8], 3: [4, 7, 9],
            4: [5, 8], 5: [10, 11], 6: [10, 11], 7: [8, 11], 8: [10], 9: [10, 11]}
    vertices = set(range(12))
    edges = {edge(u, v) for u, vs in data.items() for v in vs}
    assert len(edges) == 24 and all(len(n) == 4 for n in adjacency(vertices, edges).values())
    assert not any(all(edge(u, v) in edges for u, v in combinations(s, 2))
                   for s in combinations(vertices, 3))
    assert cycle_edges([0, 1, 5, 4]) <= edges
    colouring = [0, 1, 0, 1, 2, 0, 1, 0, 1, 2, 3, 3]
    assert all(colouring[u] != colouring[v] for u, v in map(tuple, edges))
    independent = lambda s: all(edge(u, v) not in edges for u, v in combinations(s, 2))
    assert not any(independent(s) for s in combinations(vertices, 5))
    fours = [set(s) for s in combinations(vertices, 4) if independent(s)]
    assert len(fours) == 20
    pairs = [(a, b) for a, b in combinations(fours, 2) if not a & b]
    assert len(pairs) == 64
    assert all(not independent(vertices - a - b) for a, b in pairs)
    print('3193: Chvatal girth 4, 4-colouring, 792 five-sets, 20 independent four-sets, 64 pairs verified')


def check_degeneracy():
    v = set(range(5))
    forest = {edge(i, i + 1) for i in range(4)}
    h = {edge(*p) for p in [(0, 2), (0, 3), (0, 4), (1, 3), (1, 4), (2, 4)]}
    assert not forest & h
    assert forest | h == {edge(u, w) for u, w in combinations(v, 2)}
    degrees = []
    for x in [1, 3, 0, 2, 4]:
        degrees.append(sum(x in e and e <= v for e in h))
        v.remove(x)
    assert degrees == [2, 1, 2, 1, 0]
    print('3194: K5 forest/2-degenerate partition and exact removal degrees verified')


def ve(v):
    return ('v', v)


def ee(e):
    return ('e', tuple(sorted(e)))


def total_graph(vertices, edges):
    elements = {ve(v) for v in vertices} | {ee(e) for e in edges}
    conflicts = set()
    for e in edges:
        u, v = tuple(e)
        conflicts |= {edge(ve(u), ve(v)), edge(ve(u), ee(e)), edge(ve(v), ee(e))}
    for e, f in combinations(edges, 2):
        if e & f:
            conflicts.add(edge(ee(e), ee(f)))
    return elements, conflicts


def prufer_tree(code, n):
    degrees = [1] * n
    for x in code:
        degrees[x] += 1
    edges = set()
    for x in code:
        leaf = next(i for i in range(n) if degrees[i] == 1)
        edges.add(edge(leaf, x))
        degrees[leaf] -= 1
        degrees[x] -= 1
    leaves = [i for i in range(n) if degrees[i] == 1]
    edges.add(edge(*leaves))
    return edges


def check_total_forests():
    count = 0
    for n in range(1, 6):
        codes = [()] if n <= 2 else product(range(n), repeat=n - 2)
        for code in codes:
            vertices = set(range(n))
            edges = set() if n == 1 else prufer_tree(code, n)
            adj = adjacency(vertices, edges)
            delta = max(map(len, adj.values()))
            q = max(delta + 1, 3) if edges else 1
            elements, conflicts = total_graph(vertices, edges)
            work = {v: set(ns) for v, ns in adj.items()}
            deletion = []
            while work:
                v = min(v for v in work if len(work[v]) <= 1)
                deletion.append(ve(v))
                if work[v]:
                    u = next(iter(work[v]))
                    deletion.append(ee(edge(u, v)))
                    work[u].remove(v)
                del work[v]
            assert set(deletion) == elements and len(deletion) == len(elements)
            live = set(elements)
            total_adj = adjacency(elements, conflicts)
            for x in deletion:
                neighbours = total_adj[x] & live
                assert len(neighbours) <= q - 1
                assert all(edge(a, b) in conflicts for a, b in combinations(neighbours, 2))
                live.remove(x)
            count += 1
    print(f'3195: leaf-pair total-graph deletion proof checked on {count} labelled trees through order 5')


def check_noel_ordinary_colouring():
    # Noel, arXiv:2609.38417v1, Section 2. This is NOT the four-list obstruction check.
    terminal_colours = {1: {2: 2, 3: 3, 4: 1}, 2: {1: 1, 3: 3, 4: 2},
                        3: {1: 1, 2: 2, 4: 3}, 4: {1: 2, 2: 3, 3: 1}}
    vertices, edges, colours = set(), set(), {}
    for i in range(1, 5):
        a, b = (0, i), (1, i)
        vertices |= {a, b}
        colours[ve(a)] = colours[ve(b)] = 4
        for j in range(1, 5):
            if i == j:
                continue
            t = (2, i, j)
            vertices.add(t)
            c = terminal_colours[i][j]
            colours[ve(t)] = c
            ea, eb = edge(a, t), edge(b, t)
            edges |= {ea, eb}
            colours[ee(ea)] = c % 3 + 1
            colours[ee(eb)] = (c + 1) % 3 + 1
    for i, j in combinations(range(1, 5), 2):
        cross = edge((2, i, j), (2, j, i))
        edges.add(cross)
        colours[ee(cross)] = 4
    assert len(vertices) == 20 and len(edges) == 30
    assert all(len(ns) == 3 for ns in adjacency(vertices, edges).values())
    elements, conflicts = total_graph(vertices, edges)
    assert set(colours) == elements and len(elements) == 50
    assert all(colours[x] != colours[y] for x, y in map(tuple, conflicts))
    print(f'3195: Noel example ordinary 4-total-colouring checked on 50 elements and {len(conflicts)} conflicts')


def check_petersen_pullback():
    pverts, pedges, matches = petersen()
    vertices = set(range(4))
    edges = {edge(u, v) for u, v in combinations(vertices, 2)}
    classes = [{edge(0, 1), edge(2, 3)}, {edge(0, 2), edge(1, 3)}, {edge(0, 3), edge(1, 2)}]
    target = [edge(0, 1), edge(0, 4), edge(0, 5)]
    mapping = {e: target[i] for i, cls in enumerate(classes) for e in cls}
    assert set(mapping) == edges
    for v in vertices:
        assert {mapping[e] for e in edges if v in e} == set(target)
    pulled = [{e for e in edges if mapping[e] in m} for m in matches]
    assert all(perfect(vertices, m) for m in pulled)
    assert Counter(e for m in pulled for e in m) == Counter({e: 2 for e in edges})
    print('3196: K4 Petersen-star labelling and all six matching pullbacks verified')


def proper_edge_colouring(edges, colouring):
    return all(colouring[e] != colouring[f] for e, f in combinations(edges, 2) if e & f)


def is_acyclic_edge_colouring(vertices, edges, colouring):
    if not proper_edge_colouring(edges, colouring):
        return False
    for a, b in combinations(set(colouring.values()), 2):
        selected = {e for e in edges if colouring[e] in (a, b)}
        # Properness makes two-colour components paths/cycles/isolates.
        for comp in components(vertices, selected):
            if sum(e <= comp for e in selected) >= len(comp):
                return False
    return True


def check_acyclic():
    vertices = set(range(1, 5))
    edges = {edge(u, v) for u, v in combinations(vertices, 2)}
    explicit = {edge(1, 2): 0, edge(3, 4): 0, edge(1, 3): 1,
                edge(1, 4): 2, edge(2, 3): 3, edge(2, 4): 4}
    assert is_acyclic_edge_colouring(vertices, edges, explicit)
    es = sorted(edges, key=lambda e: tuple(sorted(e)))
    proper_count = 0
    for assignment in product(range(4), repeat=6):
        colouring = dict(zip(es, assignment))
        if proper_edge_colouring(edges, colouring):
            proper_count += 1
            assert not is_acyclic_edge_colouring(vertices, edges, colouring)
    extension_count = 0
    for q in range(4, 9):
        for length in range(3, 13):
            for a, b in product(range(q), repeat=2):
                if a == b:
                    continue
                colours = [None] * length
                colours[0], colours[-1] = a, b
                colours[1] = next(c for c in range(q) if c not in (a, b))
                if length >= 4:
                    for i in range(2, length - 2):
                        colours[i] = next(c for c in range(q) if c != colours[i - 1])
                    colours[-2] = next(c for c in range(q) if c not in (colours[-3], b))
                assert all(colours[i] != colours[(i + 1) % length] for i in range(length))
                assert len(set(colours)) >= 3
                extension_count += 1
    print(f'3198: all 4096 K4 four-colour assignments ({proper_count} proper) and {extension_count} cycle extensions checked')


def main():
    check_prisms()
    check_matching_claims()
    check_hypercubes()
    check_minor_and_seagulls()
    check_expansions()
    check_chvatal()
    check_degeneracy()
    check_total_forests()
    check_noel_ordinary_colouring()
    check_petersen_pullback()
    check_acyclic()
    print('All second-batch graph checks passed.')


if __name__ == '__main__':
    main()
