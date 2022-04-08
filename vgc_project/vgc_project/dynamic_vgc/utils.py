from collections import namedtuple, defaultdict
from types import SimpleNamespace
from functools import lru_cache
from itertools import combinations, product
import numpy as np 
from frozendict import frozendict

from msdm.algorithms import PolicyIteration, ValueIteration
from msdm.core.distributions import DictDistribution

from vgc_project.maze import Maze
from vgc_project.stickyaction_maze import StickyActionMaze

##
## These functions cache computations for reuse
## across simulations.
##
@lru_cache(maxsize=int(1e7))
def _create_maze(gw_params):
    if 'action_deviation_reward' in gw_params:
        return StickyActionMaze(**gw_params)
    return Maze(**gw_params)
def create_maze(gw_params):
    if not isinstance(gw_params['tile_array'], tuple):
        gw_params = {**gw_params, 'tile_array': tuple(gw_params['tile_array'])}
    return _create_maze(frozendict(gw_params))

@lru_cache(maxsize=int(1e7))
def _solve_maze(gw_params, planning_alg="policy_iteration"):
    gw = _create_maze(gw_params)
    if planning_alg == "policy_iteration":
        res = PolicyIteration().plan_on(gw)
    elif planning_alg == "value_iteration":
        res = ValueIteration().plan_on(gw)
    else:
        raise ValueError("Unknown planning alg")
    assert res.converged
    return res
def solve_maze(gw_params, planning_alg = "policy_iteration"):
    if not isinstance(gw_params['tile_array'], tuple):
        gw_params = {**gw_params, 'tile_array': tuple(gw_params['tile_array'])}
    return _solve_maze(frozendict(gw_params), planning_alg=planning_alg)

@lru_cache(maxsize=int(1e7))
def _evaluate_construal(c, gw_params, planning_alg="policy_iteration"):
    if not isinstance(gw_params['tile_array'], tuple):
        gw_params = {**gw_params, 'tile_array': tuple(gw_params['tile_array'])}
    cgw_params = {**gw_params, 'wall_features':"#"+''.join(c)}
    cpi = _solve_maze(frozendict(cgw_params), planning_alg=planning_alg)
    gw = _create_maze(gw_params)
    c_eval = cpi.policy.evaluate_on(gw)
    return c_eval
def evaluate_construal(c, gw_params):
    return _evaluate_construal(frozenset(c), frozendict(gw_params))

def powerset(S, maxsize=float('inf'), minsize=0):
    for n in range(minsize, len(S) + 1):
        if n > maxsize:
            break
        for c in combinations(S, n):
            yield frozenset(c)

def softmax_epsilon_policy_matrix(qvals, inv_temp, rand_choose):
    if inv_temp is not None:
        cplan = np.exp((qvals - qvals.max(-1, keepdims=True))*inv_temp)
    else:
        cplan = np.isclose(qvals, qvals.max(-1, keepdims=True), atol=1e-5)
    cplan = cplan/cplan.sum(-1, keepdims=True)
    cplan = cplan*(1 - rand_choose) + rand_choose/cplan.shape[1]
    return cplan