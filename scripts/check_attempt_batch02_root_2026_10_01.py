#!/usr/bin/env python3
"""Exact finite certificates for the second 50 Ultra attempts (root group).

Run from any directory with Python 3; standard library only. These checks
verify the specified finite constructions, not the open universal targets.
The 14-vertex partial-list instance is prior work of Jonathan A. Noel,
arXiv:2609.23291v1, Section 2. Its choice number is not inferred by search.
"""
from itertools import combinations, product
from fractions import Fraction


def edge(u, v):
    return tuple(sorted((u, v)))


def walk_residues(q, length):
    residues = {0}
    for _ in range(length):
        residues = {(x + s) % q for x in residues for s in (-1, 1)}
    return residues


def check_walks():
    for length in range(3, 41):
        assert (0 in walk_residues(5, length)) == (length % 2 == 0 or length >= 5)
    for k in range(1, 9):
        q = 2 * k + 1
        assert walk_residues(q, q - 2) == set(range(1, q))
        for length in range(q - 1, q + 12):
            assert walk_residues(q, length) == set(range(q))
    for length in range(4, 41):
        plus = length // 2 if length % 2 == 0 else (length + 5) // 2
        steps = [1] * plus + [-1] * (length - plus)
        colours = [0]
        for step in steps[:-1]:
            colours.append((colours[-1] + step) % 5)
        assert (colours[0] - colours[-1]) % 5 in (1, 4)
        mapping = {(i, layer): (colours[i] + layer) % 5
                   for i in range(length) for layer in (0, 1)}
        edges = [((i, layer), ((i + 1) % length, layer))
                 for i in range(length) for layer in (0, 1)]
        edges += [((i, 0), (i, 1)) for i in range(length)]
        assert all((mapping[u] - mapping[v]) % 5 in (1, 4) for u, v in edges)
    print('3207/3208: cycle residues, path thresholds and 37 cubic prism mappings passed')


def check_graceful():
    for m in range(41):
        labels = [i // 2 if i % 2 == 0 else m - i // 2 for i in range(m + 1)]
        assert set(labels) == set(range(m + 1))
        assert sorted(abs(x - y) for x, y in zip(labels, labels[1:])) == list(range(1, m + 1))
        if 1 <= m <= 12:
            n = 2 * m + 1
            copies = [edge((x + s) % n, (y + s) % n)
                      for s in range(n) for x, y in zip(labels, labels[1:])]
            assert len(copies) == len(set(copies)) == n * (n - 1) // 2
            assert set(copies) == set(combinations(range(n), 2))
    for a, b in product(range(13), repeat=2):
        m = a + b + 1
        labels = [0, b + 1] + list(range(1, b + 1)) + list(range(b + 2, m + 1))
        differences = [b + 1] + [b + 1 - x for x in range(1, b + 1)] + list(range(b + 2, m + 1))
        assert sorted(labels) == list(range(m + 1))
        assert sorted(differences) == list(range(1, m + 1))
    assert [abs(x-y) for x,y in zip([0,2,1,3], [2,1,3])] == [2,1,2]
    print('3212: 41 paths, 169 double-stars, 12 cyclic decompositions and failed extension passed')


def circulation(vertices, edges, cycle):
    values = {e: 0 for e in edges}
    for u, v in zip(cycle, cycle[1:] + cycle[:1]):
        values[edge(u, v)] += 1 if u < v else -1
    assert balances(vertices, values) == [0] * vertices
    return values


def balances(n, values):
    result = [0] * n
    for (u, v), value in values.items():
        result[u] -= value
        result[v] += value
    return result


def check_flows():
    edges = list(combinations(range(4), 2))
    x = circulation(4, edges, [0, 1, 3, 2])
    y = circulation(4, edges, [0, 2, 1, 3])
    f = {e: x[e] + 2*y[e] for e in edges}
    assert all(1 <= abs(value) <= 3 for value in f.values())
    assert balances(4, f) == [0] * 4
    assert not any(all(b % 3 == 0 for b in balances(4, dict(zip(edges, signs))))
                   for signs in product((-1, 1), repeat=6))
    for k in range(1, 11):
        m = 2*k + 1
        for n in range(4*k, 4*k + 26):
            a = n//2 if n % 2 == 0 else (n-m)//2
            assert 0 <= a <= n and (n-2*a) % m == 0
    for length in range(1, 21):
        b = [0] * (length + 1)
        b[0] += 1 + 1  # two incoming loop incidences, value 1
        b[-1] -= 1 + 1  # two outgoing loop incidences, value 1
        for i in range(length):
            b[i] -= 2
            b[i+1] += 2
        assert b == [0] * (length + 1)
    print('3214/3217/3218: K4 four-flow, 64 modular orientations, 260 parallel-edge instances, 20 signed handcuffs passed')


def check_petersen():
    edges = sorted({edge(i, (i+1) % 5) for i in range(5)} |
                   {edge(5+i, 5+(i+2) % 5) for i in range(5)} |
                   {(i, i+5) for i in range(5)})
    matchings = []
    for chosen in combinations(edges, 5):
        if sorted(v for e in chosen for v in e) != list(range(10)):
            continue
        matchings.append(chosen)
        adj = {v: set() for v in range(10)}
        for u, v in set(edges) - set(chosen):
            adj[u].add(v)
            adj[v].add(u)
        assert all(len(neighbours) == 2 for neighbours in adj.values())
        remaining, sizes = set(range(10)), []
        while remaining:
            pending, component = [next(iter(remaining))], set()
            while pending:
                v = pending.pop()
                if v not in component:
                    component.add(v)
                    pending.extend(adj[v] - component)
            remaining -= component
            sizes.append(len(component))
        assert sorted(sizes) == [5, 5]
    assert len(matchings) == 6
    print('3219: all 3003 five-edge subsets checked; exactly six perfect matchings, each with 5+5 complement')


def check_strong_and_reed():
    # u=0, v=1, x=2, y=3; transversal {x,y} leaves adjacent u,v.
    parts = [{0,2}, {1,3}]
    bad, good = {2,3}, {0,3}
    assert all(len(part & bad) == 1 for part in parts)
    assert {0,1} <= (set(range(4)) - bad)
    colouring = {v: int(v not in good) for v in range(4)}
    assert colouring[0] != colouring[1]
    assert all(len({colouring[v] for v in part}) == 2 for part in parts)
    for t in range(1,21):
        classes = []
        for i in range(5):
            for _ in range(t//2):
                classes.append([i, (i+2) % 5])
        if t % 2:
            classes += [[0,2], [1,3], [4]]
        assert len(classes) == (5*t+1)//2
        assert all(sum(i in cls for cls in classes) == t for i in range(5))
        assert all(len(cls) == len(set(cls)) and all((i-j) % 5 not in (1,4)
                   for i,j in combinations(cls,2)) for cls in classes)
        # Give each occurrence a distinct vertex in its clique and check every edge.
        next_vertex, c = [0]*5, {}
        for colour, cls in enumerate(classes):
            for i in cls:
                c[i, next_vertex[i]] = colour
                next_vertex[i] += 1
        vertices = list(c)
        degrees = {v: 0 for v in vertices}
        for u,v in combinations(vertices,2):
            if u[0] == v[0] or (u[0]-v[0]) % 5 in (1,4):
                assert c[u] != c[v]
                degrees[u] += 1
                degrees[v] += 1
        assert set(degrees.values()) == {3*t-1}
        assert ((3*t-1)+1+2*t+1)//2 == len(classes)
    print('3225/3226: failed arbitrary transversal and 20 exact Reed equality certificates passed')


def check_partial_lists():
    # Terminals have disjoint 2-lists. Each triangle has one private vertex,
    # and two vertices adjacent to both terminals; no edges between triangles.
    triangle_lists = [(1,3),(1,4),(2,3),(2,4)]
    optimum = 0
    conditional_optima = []
    for s1,s2 in product((None,1,2),(None,3,4)):
        count = int(s1 is not None) + int(s2 is not None)
        for pair in triangle_lists:
            best = 0
            for private,a,b in product((None,)+pair, repeat=3):
                values = (private,a,b)
                coloured = [x for x in values if x is not None]
                if len(coloured) != len(set(coloured)):
                    continue
                if any(value is not None and value in (s1,s2) for value in (a,b)):
                    continue
                best = max(best,len(coloured))
            count += best
        conditional_optima.append(count)
        optimum = max(optimum,count)
    assert optimum == 9
    assert conditional_optima == [8,9,9,9,9,9,9,9,9]
    assert Fraction(9,2) < Fraction(14,3)
    families = 0
    for length in range(1,5):
        for sizes in product(range(1,7),repeat=length):
            q,n = max(sizes),sum(sizes)
            values = [sum(min(t,m) for m in sizes) for t in range(q+1)]
            for r in range(1,q+1):
                assert values[r]*q >= r*n
                for s in range(r,q+1):
                    assert values[r]*s >= values[s]*r
            families += 1
    toy = [0,3,4,7]
    assert all(toy[i] <= toy[i+1] for i in range(3))
    assert all(toy[a+b] <= toy[a]+toy[b] for a in range(4) for b in range(4-a))
    assert Fraction(toy[2],2) < Fraction(toy[3],3)
    print(f'3231/3232: prior 14-vertex bad lists have optimum 9; {families} clique-size sequences and subadditivity diagnostic passed')


if __name__ == '__main__':
    check_walks()
    check_graceful()
    check_flows()
    check_petersen()
    check_strong_and_reed()
    check_partial_lists()
    print('All root batch02 finite certificates passed.')
