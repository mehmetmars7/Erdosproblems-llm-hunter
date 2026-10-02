#!/usr/bin/env python3
"""Exact finite checks cited by the 2026-10-01 algebra/combinatorics attempts.

These verify restricted examples and certificates, not the full conjectures.
Run with Python 3 from any directory; only the standard library is used.
"""

from fractions import Fraction
from functools import lru_cache
from itertools import permutations, product
import json


def permutation_sign(values):
    return (-1) ** sum(
        values[i] > values[j]
        for i in range(len(values))
        for j in range(i + 1, len(values))
    )


def latin_square_check():
    """Enumerate all labelled order-four Latin squares, not reduced ones."""
    n = 4
    candidates = list(permutations(range(n)))
    counts = {-1: 0, 1: 0}

    def extend(rows):
        if len(rows) == n:
            sign = 1
            for row in rows:
                sign *= permutation_sign(row)
            for j in range(n):
                sign *= permutation_sign([rows[i][j] for i in range(n)])
            counts[sign] += 1
            return
        for row in candidates:
            if all(all(row[j] != old[j] for old in rows) for j in range(n)):
                extend(rows + [row])

    extend([])
    assert counts == {-1: 0, 1: 576}
    return {"even": counts[1], "odd": counts[-1]}


def square_game_check():
    n = 3
    squares = [
        frozenset((i * n + j, (i + t) * n + j,
                   i * n + j + t, (i + t) * n + j + t))
        for t in range(1, n)
        for i in range(n - t)
        for j in range(n - t)
    ]
    pairs = [(1, 2), (3, 4), (5, 7), (6, 8)]
    assert len({v for pair in pairs for v in pair}) == 8
    assert all(any(set(pair) <= square for pair in pairs) for square in squares)
    winning_masks = [sum(1 << v for v in square) for square in squares]
    full = (1 << (n * n)) - 1

    @lru_cache(None)
    def minimax(us, them):
        empty = full ^ (us | them)
        if not empty:
            return 0
        best = -1
        while empty:
            move = empty & -empty
            empty -= move
            moved = us | move
            if any(moved & square == square for square in winning_masks):
                return 1
            best = max(best, -minimax(them, moved))
            if best == 1:
                return 1
        return best

    value = minimax(0, 0)
    assert value == 0
    return {"winning_sets": len(squares), "initial_minimax": value,
            "states_evaluated": minimax.cache_info().currsize}


def signed_partition_check():
    signs = {
        1: [1, -1, 1, 1, -1, 1, -1, 1, 1],
        2: [1, 1, 1, -1], 3: [-1, 1, 1], 4: [1, 1],
        5: [-1], 6: [-1], 7: [1], 8: [-1], 9: [1],
    }
    degree = 10
    coefficients = [1] + [0] * degree
    for j, row in signs.items():
        updated = coefficients.copy()
        for m, sign in enumerate(row, 1):
            for k in range(j * m, degree + 1):
                updated[k] += sign * coefficients[k - j * m]
        coefficients = updated
    assert coefficients == [1, 1, 0, 1, 1, 1, -1, 1, 0, 0, 6]
    extensions = [coefficients[10] + sum(values)
                  for values in product((-1, 1), repeat=4)]
    assert all(abs(value) > 1 for value in extensions)
    return {"old_coefficients": coefficients,
            "degree_10_possible_values": sorted(set(extensions))}


def cube_bootstrap_check():
    dimension = 5
    infected = {v for v in range(32) if v.bit_count() % 2 == 0} - {0, 15}
    assert len(infected) == 14
    initial = sorted(infected)
    layers = []
    while True:
        new = {
            v for v in range(32)
            if v not in infected
            and sum((v ^ (1 << j)) in infected for j in range(dimension)) >= 4
        }
        if not new:
            break
        layers.append(sorted(new))
        infected |= new
    assert len(infected) == 32
    assert [len(layer) for layer in layers] == [16, 2]
    assert layers[-1] == [0, 15]
    return {"initial_vertices": initial, "new_layer_sizes": [16, 2]}


def multiply(left, right):
    return [[sum(left[i][k] * right[k][j] for k in range(len(right)))
             for j in range(len(right[0]))] for i in range(len(left))]


def switching_check():
    """Rational conjugation for the seven-vertex nonisomorphic pair."""
    adjacency = [[0 for _ in range(7)] for _ in range(7)]
    for outside, neighbours in enumerate(((0, 1), (0, 2), (0, 3)), 4):
        for inside in neighbours:
            adjacency[outside][inside] = adjacency[inside][outside] = 1
    conjugator = [[Fraction(int(i == j)) for j in range(7)] for i in range(7)]
    for i in range(4):
        for j in range(4):
            conjugator[i][j] = Fraction(1, 2) - int(i == j)
    identity = [[int(i == j) for j in range(7)] for i in range(7)]
    assert multiply(conjugator, conjugator) == identity
    switched = multiply(multiply(conjugator, adjacency), conjugator)
    expected = [[0 for _ in range(7)] for _ in range(7)]
    for outside, neighbours in enumerate(((2, 3), (1, 3), (1, 2)), 4):
        for inside in neighbours:
            expected[outside][inside] = expected[inside][outside] = 1
    assert switched == expected
    before = sorted(map(sum, adjacency))
    after = sorted(map(sum, expected))
    assert before == [1, 1, 1, 2, 2, 2, 3]
    assert after == [0, 2, 2, 2, 2, 2, 2]
    assert before != after
    return {"degrees_before": before, "degrees_after": after,
            "exact_orthogonal_similarity": True}


def main():
    results = {
        "3041_latin_squares": latin_square_check(),
        "3047_partition_dead_end": signed_partition_check(),
        "3049_square_game": square_game_check(),
        "3055_cube_percolation": cube_bootstrap_check(),
        "3131_cospectral_switching": switching_check(),
    }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
