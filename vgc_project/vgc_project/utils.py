from itertools import combinations, product
import numpy as np

def normalize(vals, minval=None, maxval=None):
    if minval is None:
        minval = np.min(vals)
    if maxval is None:
        maxval = np.max(vals)
    return (vals - minval)/(maxval - minval)

def zscore(vals):
    mu = np.mean(vals)
    sd = np.std(vals)
    return (vals - mu)/sd
    
def min_dist(a, b):
    mindist = float('inf')
    for ai, bi in product(a, b):
        dist = abs(ai['x'] - bi['x']) + abs(ai['y'] - bi['y'])
        if dist < mindist:
            mindist = dist
    return mindist

def mean_dist(a, b):
    tot = []
    for ai, bi in product(a, b):
        dist = abs(ai['x'] - bi['x']) + abs(ai['y'] - bi['y'])
        tot.append(dist)
    return sum(tot)/len(tot)

def powerset(s):
    for n in range(0, len(s) + 1):
        yield from combinations(s, n)
