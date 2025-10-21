#!/usr/bin/env python3
"""
Countdown Numbers Game Solver
-----------------------------
Provides a callable function `solve_numbers(target, numbers)`
that returns all closest solutions to the Countdown numbers puzzle.

Usage (example):
    from numbers_solver import solve_numbers
    result = solve_numbers(952, [100, 75, 50, 25, 6, 3])
"""

from itertools import combinations, product, zip_longest
from functools import lru_cache


class Solutions:
    def __init__(self, numbers):
        self.all_numbers = numbers
        self.size = len(numbers)
        self.all_groups = self._unique_groups()

    def _unique_groups(self):
        all_groups = {}
        for m in range(1, self.size + 1):
            for nums in combinations(self.all_numbers, m):
                if nums in all_groups:
                    continue
                all_groups[nums] = Group(nums, all_groups)
        return all_groups

    def walk(self):
        for group in self.all_groups.values():
            yield from group.calculations


class Group:
    def __init__(self, numbers, all_groups):
        self.numbers = numbers
        self.size = len(numbers)
        self.partitions = list(self._partition_unique_pairs(all_groups))
        self.calculations = list(self._perform_calculations())

    def _partition_unique_pairs(self, all_groups):
        if self.size == 1:
            return
        limits = (self._halfbinom(self.size, self.size // 2),)
        seen = set()
        for m, limit in zip_longest(range((self.size + 1) // 2, self.size), limits):
            for a, b in self._paired_combinations(self.numbers, m, limit):
                if a in seen:
                    continue
                seen.add(a)
                yield (all_groups[a], all_groups[b])

    def _perform_calculations(self):
        if self.size == 1:
            yield Calculation.singleton(self.numbers[0])
            return
        for g1, g2 in self.partitions:
            for c1, c2 in product(g1.calculations, g2.calculations):
                yield from Calculation.generate(c1, c2)

    @classmethod
    def _paired_combinations(cls, numbers, m, limit):
        for cnt, n1 in enumerate(combinations(numbers, m), 1):
            n2 = tuple(cls._filter(numbers, n1))
            yield (n1, n2)
            if cnt == limit:
                return

    @staticmethod
    def _filter(iterable, elements):
        elems = iter(elements)
        k = next(elems, None)
        for n in iterable:
            if n == k:
                k = next(elems, None)
            else:
                yield n

    @staticmethod
    @lru_cache()
    def _halfbinom(n, k):
        if n % 2 == 1:
            return None
        prod = 1
        for m, l in zip(reversed(range(n + 1 - k, n + 1)), range(1, k + 1)):
            prod = (prod * m) // l
        return prod // 2


class Calculation:
    def __init__(self, expr, result, is_singleton=False):
        self.expr = expr
        self.result = result
        self.is_singleton = is_singleton

    @classmethod
    def singleton(cls, n):
        return cls(f"{n}", n, True)

    @classmethod
    def generate(cls, a, b):
        if a.result < b.result:
            a, b = b, a
        for res, op in cls.operations(a.result, b.result):
            expr1 = f"{a.expr}" if a.is_singleton else f"({a.expr})"
            expr2 = f"{b.expr}" if b.is_singleton else f"({b.expr})"
            yield cls(f"{expr1} {op} {expr2}", res)

    @staticmethod
    def operations(x, y):
        yield (x + y, '+')
        if x > y:
            yield (x - y, '-')
        if y > 1 and x > 1:
            yield (x * y, '×')
        if y > 1 and x % y == 0:
            yield (x // y, '/')


def solve_numbers(target, numbers):
    """
    Solve a Countdown numbers puzzle.
    Returns dict: { target, difference, results: [(value, expression), ...] }
    """
    numbers = tuple(sorted(numbers, reverse=True))
    solutions = Solutions(numbers)
    smallest_diff = abs(target)
    best = []

    for calc in solutions.walk():
        diff = abs(calc.result - target)
        if diff <= smallest_diff:
            if diff < smallest_diff:
                best = [calc]
                smallest_diff = diff
            else:
                best.append(calc)

    return {
        "target": target,
        "difference": smallest_diff,
        "results": [(c.result, c.expr) for c in best]
    }


# Optional: run standalone for testing
if __name__ == "__main__":
    target = 952
    numbers = [100, 75, 50, 25, 6, 3]
    result = solve_numbers(target, numbers)
    print(f"Closest results differ from {result['target']} by {result['difference']}:\n")
    for val, expr in result["results"]:
        print(f"{val} = {expr}")
