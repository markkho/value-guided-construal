from functools import lru_cache
from itertools import combinations
from frozendict import frozendict
from msdm.domains import GridWorld
from msdm.algorithms import PolicyIteration

##
## These functions cache computations for reuse
## across simulations.
##
@lru_cache(maxsize=int(1e7))
def _create_gridworld(gw_params):
    return GridWorld(**gw_params)
def create_gridworld(gw_params):
    if not isinstance(gw_params['tile_array'], tuple):
        gw_params = {**gw_params, 'tile_array': tuple(gw_params['tile_array'])}
    return _create_gridworld(frozendict(gw_params))

@lru_cache(maxsize=int(1e7))
def _solve_gridworld(gw_params):
    gw = GridWorld(**gw_params)
    res = PolicyIteration().plan_on(gw)
    return res
def solve_gridworld(gw_params):
    if not isinstance(gw_params['tile_array'], tuple):
        gw_params = {**gw_params, 'tile_array': tuple(gw_params['tile_array'])}
    return _solve_gridworld(frozendict(gw_params))

@lru_cache(maxsize=int(1e7))
def _evaluate_construal(c, gw_params):
    if not isinstance(gw_params['tile_array'], tuple):
        gw_params = {**gw_params, 'tile_array': tuple(gw_params['tile_array'])}
    cgw_params = {**gw_params, 'wall_features':"#"+''.join(c)}
    cpi = _solve_gridworld(frozendict(cgw_params))
    gw = _create_gridworld(gw_params)
    c_eval = cpi.policy.evaluate_on(gw)
    return c_eval
def evaluate_construal(c, gw_params):
    return _evaluate_construal(frozenset(c), frozendict(gw_params))

def powerset(S):
    for n in range(0, len(S) + 1):
        for c in combinations(S, n):
            yield frozenset(c)
            