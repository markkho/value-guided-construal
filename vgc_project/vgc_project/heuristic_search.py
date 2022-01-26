import random
from frozendict import frozendict
from collections import defaultdict
import numpy as np

from msdm.domains import GridWorld
from msdm.algorithms import PolicyIteration, LAOStar, LRTDP

def graph_based_heuristic_search(
    *,
    tile_array,
    seed,
    heuristic_type, #no_obstacles or no_walls
    n_simulations=1000,
    feature_rewards=(("G", 0), ),
    absorbing_features=("G",),
    wall_features="#0123456789",
    default_features=(".",),
    initial_features=("S",),
    step_cost=-1,
    discount_rate=1.0
):
    gw_params = dict(
        tile_array=tile_array,
        feature_rewards=feature_rewards,
        step_cost=step_cost,
        discount_rate=discount_rate,
        absorbing_features=absorbing_features,
        wall_features=wall_features,
        default_features=default_features,
        initial_features=initial_features,
        success_prob=1 - 1e-5
    )
    gw = GridWorld(**gw_params)
    if heuristic_type == "no_obstacles":
        heuristic_gw = GridWorld(**{
            **gw_params,
            "wall_features": "#"
        })
    elif heuristic_type == "no_walls":
        heuristic_gw = GridWorld(**{
            **gw_params,
            "wall_features": ""
        })
    heuristic_value = PolicyIteration().plan_on(heuristic_gw).V
    def heuristic(s):
        return heuristic_value[s]
    empty_gw = GridWorld(**{**gw_params, "wall_features": ""})
    all_hit_counts = {o: list() for o in "0123456789"}
    random.seed(seed)
    sim_seeds = [random.randint(0, int(1e20)) for _ in range(n_simulations)]
    for sim_seed, sim in list(zip(sim_seeds, range(n_simulations))):
        lao_res = LAOStar(heuristic=heuristic, seed=sim_seed, show_progress=False).plan_on(gw)
        hit_counts = defaultdict(int)
        g = gw.feature_locations[absorbing_features[0]][0]
        for node in lao_res.egraph.values():
            if node['expandedorder'] < 0:
                continue
            s = node['state']
            dgx, dgy = (g['x'] - s['x'], g['y'] - s['y'])
            if dgx != 0:
                dgx = dgx // abs(dgx)
            if dgy != 0:
                dgy = dgy // abs(dgy)
            f = empty_gw.location_features.get(frozendict(x=s['x']+dgx, y=s['y']), '.')
            hit_counts[f] += 1
            f = empty_gw.location_features.get(frozendict(x=s['x'], y=s['y']+dgy), '.')
            hit_counts[f] += 1
        for o in all_hit_counts.keys():
            all_hit_counts[o].append(hit_counts.get(o, 0))
    mean_hit_counts = {o: np.mean(cs) for o, cs in all_hit_counts.items()}
    res = dict(
        mean_hit_counts=mean_hit_counts,
        all_hit_counts=all_hit_counts,
        heuristic_type=heuristic_type,
        n_simulations=n_simulations,
        seed=seed
    )
    return res


def trajectory_based_heuristic_search(
    *,
    tile_array,
    seed,
    heuristic_type, #no_obstacles or no_walls
    randomize_action_order=True,
    n_simulations=1000,
    feature_rewards=(("G", 0), ),
    absorbing_features=("G",),
    wall_features="#0123456789",
    default_features=(".",),
    initial_features=("S",),
    step_cost=-1,
    discount_rate=1.0
):
    gw_params = dict(
        tile_array=tile_array,
        feature_rewards=feature_rewards,
        step_cost=step_cost,
        discount_rate=discount_rate,
        absorbing_features=absorbing_features,
        wall_features=wall_features,
        default_features=default_features,
        initial_features=initial_features,
        success_prob=1 - 1e-5
    )
    gw = GridWorld(**gw_params)
    if heuristic_type == "no_obstacles":
        heuristic_gw = GridWorld(**{
            **gw_params,
            "wall_features": "#"
        })
    elif heuristic_type == "no_walls":
        heuristic_gw = GridWorld(**{
            **gw_params,
            "wall_features": "#"
        })
    heuristic_value = PolicyIteration().plan_on(heuristic_gw).V
    def heuristic(s):
        return heuristic_value[s]
    empty_gw = GridWorld(**{**gw_params, "wall_features": ""})
    all_hit_counts = {o: list() for o in "0123456789"}
    random.seed(seed)
    sim_seeds = [random.randint(0, int(1e20)) for _ in range(n_simulations)]
    for sim_seed, sim in list(zip(sim_seeds, range(n_simulations))):
        lrtdp_res = LRTDP(heuristic=heuristic, seed=sim_seed, randomize_action_order=randomize_action_order).plan_on(gw)
        hit_counts = defaultdict(int)
        g = gw.feature_locations[absorbing_features[0]][0]
        visited = sum(lrtdp_res.trials, [])
        for s in visited:
            dgx, dgy = (g['x'] - s['x'], g['y'] - s['y'])
            if dgx != 0:
                dgx = dgx // abs(dgx)
            if dgy != 0:
                dgy = dgy // abs(dgy)
            f = empty_gw.location_features.get(frozendict(x=s['x']+dgx, y=s['y']), '.')
            hit_counts[f] += 1
            f = empty_gw.location_features.get(frozendict(x=s['x'], y=s['y']+dgy), '.')
            hit_counts[f] += 1
        for o in all_hit_counts.keys():
            all_hit_counts[o].append(hit_counts.get(o, 0))
    mean_hit_counts = {o: np.mean(cs) for o, cs in all_hit_counts.items()}
    res = dict(
        mean_hit_counts=mean_hit_counts,
        all_hit_counts=all_hit_counts,
        heuristic_type=heuristic_type,
        n_simulations=n_simulations,
        seed=seed
    )
    return res
