"""
Utility for sampling stochastic functions that satisfy
certain constraints.

Example:

from vgc_project import sampsat
import random

def func():
    i = random.randint(0, 10)
    sampsat.condition(i % 3 != 0)
    return i
unique = set([sampsat.rejection(func) for _ in range(100)])
# {1, 2, 4, 5, 7, 8, 10}
"""
import random
from collections import Counter

class Invalid(Exception):
    pass
def condition(cond):
    if not cond:
        raise Invalid
def rejection(func, n=int(1e5), debug=False):
    res = None
    for _i in range(n):
        try:
            res = func()
            break
        except Invalid:
            continue
    if debug:
        print(f"{_i} runs")
    return res
def has_close_frequencies(items, max_diff):
    c = Counter(items)
    vals = set(c.values())
    return max(abs(a - b) for a in vals for b in vals) <= max_diff
def no_repeat(items, repeat_size=2):
    for i in range(len(items) - repeat_size):
        if len(set(items[i:i+repeat_size])) == 1:
            return False
    return True
def differentness(a, b):
    aidx = {ai: i for i, ai in enumerate(a)}
    bidx = {bi: i for i, bi in enumerate(b)}
    sqdiff = 0
    for abi in (set(a) | set(b)):
        sqdiff += (aidx[abi] - bidx[abi])**2
    return sqdiff/len(set(a) | set(b))