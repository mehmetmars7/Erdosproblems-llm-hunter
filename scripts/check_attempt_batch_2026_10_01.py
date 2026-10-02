#!/usr/bin/env python3
"""Reproduce finite checks cited in the first 50 new Ultra notebooks.

These are exact checks of restricted examples, not proofs of the full targets.
Run from any directory with Python 3; no third-party packages are required.
"""
from functools import lru_cache
from itertools import combinations, product
import json
from math import prod


def packing_checks():
    checked = 0
    for a in range(1, 9):
        for b in range(1, a + 1):
            s = a + b
            rectangles = [(0, a, 0, b), (a, s, 0, a),
                          (b, s, a, s), (0, b, b, s)]
            for x0, x1, y0, y1 in rectangles:
                assert 0 <= x0 < x1 <= s and 0 <= y0 < y1 <= s
                assert sorted((x1 - x0, y1 - y0)) == [b, a]
            for p, q in combinations(rectangles, 2):
                assert min(p[1], q[1]) <= max(p[0], q[0]) or min(p[3], q[3]) <= max(p[2], q[2])
            assert s * s - 4 * a * b == (a - b) ** 2
            checked += 1
    for k in range(1, 9):
        assert 4 ** k * k ** (2 * k) == (2 * k) ** (2 * k)
    assert 4 ** 2 * (5 // 3) ** 2 * (5 // 2) ** 2 == 64 < 256
    return {'rectangle_pairs': checked, 'product_count_identities': 8}


def pentagon_product_checks():
    colours = (0, 1, 0, 1, 2)
    result = {}
    for r in range(1, 5):
        states = list(product(range(5), repeat=r))
        for state in states:
            c = sum(colours[t] for t in state) % 3
            for i in range(r):
                for delta in (-1, 1):
                    adjacent = list(state)
                    adjacent[i] = (adjacent[i] + delta) % 5
                    assert sum(colours[t] for t in adjacent) % 3 != c
        result[r] = len(states)
    return result


def simplex_product_checks():
    result = {}
    for k in range(3, 7):
        faces = [a for a in product(range(k), repeat=k - 1) if sum(a) == k]
        assert faces
        for a in faces:
            assert prod(d + 1 for d in a) > k + 1
            assert any(d >= 2 for d in a)
        result[k] = len(faces)
    return result


def pebbling_checks():
    # Coordinates are (0,0), (1,0), (0,1), (1,1); target is index 0.
    neighbours = ((1, 2), (0, 3), (0, 3), (1, 2))

    @lru_cache(None)
    def solvable(state):
        if state[0]:
            return True
        for i, count in enumerate(state):
            if count >= 2:
                for j in neighbours[i]:
                    nxt = list(state)
                    nxt[i] -= 2
                    nxt[j] += 1
                    if solvable(tuple(nxt)):
                        return True
        return False

    states = [s for s in product(range(5), repeat=4) if sum(s) == 4]
    assert len(states) == 35 and all(map(solvable, states))
    state = [0, 1, 1, 2]
    assert (state[0] + state[1]) // 2 + (state[2] + state[3]) // 2 == 1
    for i, j in ((3, 2), (2, 0)):
        assert state[i] >= 2 and j in neighbours[i]
        state[i] -= 2
        state[j] += 1
    assert state[0] == 1
    return {'four_pebble_configurations': len(states), 'residue_witness_moves': 2}


def regular_reconstruction_checks():
    totals = {}
    for n in range(3, 6):
        edges = list(combinations(range(n), 2))
        checked = 0
        for mask in range(1 << len(edges)):
            chosen = {e for i, e in enumerate(edges) if mask & (1 << i)}
            degrees = [sum(v in e for e in chosen) for v in range(n)]
            if len(set(degrees)) != 1:
                continue
            r = degrees[0]
            cards = [{e for e in chosen if v not in e} for v in range(n)]
            assert sum(map(len, cards)) == (n - 2) * len(chosen)
            assert [len(chosen) - len(card) for card in cards] == degrees
            for v, card in enumerate(cards):
                neighbours = {u for u in range(n) if u != v and sum(u in e for e in card) == r - 1}
                restored = card | {tuple(sorted((u, v))) for u in neighbours}
                assert restored == chosen
            checked += 1
        totals[n] = checked
    return totals


def run_checks():
    return {'3082': packing_checks(), '3092': pentagon_product_checks(),
            '3099': simplex_product_checks(), '3102': pebbling_checks(),
            '3103': regular_reconstruction_checks()}


if __name__ == '__main__':
    print(json.dumps(run_checks(), indent=2, sort_keys=True))
