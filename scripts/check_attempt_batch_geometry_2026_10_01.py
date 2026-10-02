#!/usr/bin/env python3
"""Reproduce finite checks for the 2026-10-01 Ultra attempts.

Standard library only. These checks certify the stated finite examples,
not any general conjecture or the correctness of cited research papers.
"""

from fractions import Fraction
from itertools import combinations, product
from math import gcd


def covering_and_row_counts():
    blocks = [{(a + x) % 7 for x in (0, 1, 3)} for a in range(7)]
    for pair in combinations(range(7), 2):
        assert sum(set(pair) <= block for block in blocks) == 1
    for q in (3, 5, 7):
        for s in range(1, 5):
            count = sum(sum(xs) % q == 0 for xs in product(range(1, q), repeat=s))
            assert count == ((q - 1) ** s + (q - 1) * (-1) ** s) // q
    print('3058: all 21 pairs covered once; 3059: row counts q=3,5,7, s=1..4')


def height(family):
    values = {}
    for item in sorted(family, key=int.bit_count):
        values[item] = 1 + max(
            (values[other] for other in values if other & item == other),
            default=0,
        )
    return max(values.values(), default=0)


def saturated_families():
    for k in (2, 3, 4):
        n = k + 1
        y_mask = (1 << (k - 2)) - 1
        r_mask = ((1 << n) - 1) ^ y_mask
        family = set(range(1 << (k - 2)))
        family |= {a | r_mask for a in tuple(family)}
        assert len(family) == 2 ** (k - 1)
        assert height(family) == k
        for missing in set(range(1 << n)) - family:
            assert height(family | {missing}) == k + 1
    print('3068: saturated constructions verified for k=2,3,4 and n=k+1')


def prime_power_factors(m):
    factors = []
    p = 2
    while p * p <= m:
        if m % p == 0:
            power = 1
            while m % p == 0:
                power *= p
                m //= p
            factors.append((p, power))
        p += 1
    if m > 1:
        factors.append((m, m))
    return factors


def periodic_colourings():
    for m in range(2, 41):
        factors = prime_power_factors(m)
        colours = [sum((x % power) // (power // p) for p, power in factors) % 2
                   for x in range(m)]
        for d in range(1, m):
            order = m // gcd(d, m)
            for start in range(m):
                assert {colours[(start + i * d) % m] for i in range(order)} == {0, 1}
    print('3070: every nontrivial subgroup coset is bichromatic for moduli 2..40')


def antipodal_colourings():
    for d in (2, 3, 4):
        vertex_count = 1 << d
        antipode_mask = vertex_count - 1
        pairs = []
        for u in range(vertex_count):
            for coordinate in range(d):
                v = u ^ (1 << coordinate)
                if u > v:
                    continue
                edge = (u, v)
                opposite = tuple(sorted((u ^ antipode_mask, v ^ antipode_mask)))
                if edge < opposite:
                    pairs.append((edge, opposite))
        assert len(pairs) == d * 2 ** (d - 2)
        checked = 0
        for choices in range(1 << len(pairs)):
            parent = list(range(vertex_count))

            def find(vertex):
                while parent[vertex] != vertex:
                    parent[vertex] = parent[parent[vertex]]
                    vertex = parent[vertex]
                return vertex

            for index, pair in enumerate(pairs):
                u, v = pair[(choices >> index) & 1]
                parent[find(u)] = find(v)
            assert any(find(v) == find(v ^ antipode_mask)
                       for v in range(vertex_count // 2))
            checked += 1
        print(f'3072: all {checked} antipodal colourings in dimension {d} passed')


def visible_grid():
    grid = set(product(range(3), repeat=2))
    corners = list(product((0, 2), repeat=2))
    for a, b in combinations(corners, 2):
        midpoint = tuple((x + y) // 2 for x, y in zip(a, b))
        assert midpoint in grid and midpoint not in (a, b)
    print('3074: all six corner-pair segments have a grid blocker')


def determinant3(matrix):
    a, b, c = matrix
    return (a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0]))


def tetrahedron_volumes():
    even = [v for v in product((0, 1), repeat=3) if sum(v) % 2 == 0]
    odd = [v for v in product((0, 1), repeat=3) if sum(v) % 2 == 1]
    tetrahedra = [even]
    for corner in odd:
        tetrahedra.append([corner] + [v for v in even
                                     if sum(x != y for x, y in zip(v, corner)) == 1])
    volumes = []
    for tetrahedron in tetrahedra:
        edges = [[v[j] - tetrahedron[0][j] for j in range(3)]
                 for v in tetrahedron[1:]]
        volumes.append(Fraction(abs(determinant3(edges)), 6))
    assert volumes == [Fraction(1, 3)] + [Fraction(1, 6)] * 4
    assert sum(volumes) == 1
    print('3078: exact tetrahedron volumes are 1/3,1/6,1/6,1/6,1/6')


if __name__ == '__main__':
    covering_and_row_counts()
    saturated_families()
    periodic_colourings()
    antipodal_colourings()
    visible_grid()
    tetrahedron_volumes()
