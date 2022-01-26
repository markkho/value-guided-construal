from frozendict import frozendict

from msdm.domains import GridWorld
from msdm.algorithms import PolicyIteration

from vgc_project.utils import min_dist, mean_dist

def maze_obstacle_statistics(
    *,
    tile_array,
    n_simulations=100,
    feature_rewards=(("G", 0), ),
    absorbing_features=("G",),
    wall_features="#0123456789",
    default_features=(".",),
    initial_features=("S",),
    step_cost=-1,
    discount_rate=1.0
):
    gw = GridWorld(
        tile_array=tile_array,
        feature_rewards=feature_rewards,
        step_cost=step_cost,
        discount_rate=discount_rate,
        absorbing_features=absorbing_features,
        wall_features=wall_features,
        default_features=default_features,
        initial_features=initial_features,
    )
    center = frozendict(x=int(gw.width/2), y=int(gw.height/2))
    obstacles = set(list(''.join(tile_array))) & set(list("0123456789"))
    pi = PolicyIteration().plan_on(gw).policy
    sr = pi.evaluate_on(gw).occupancy
    optimal_policy_expected_distance = {}
    for o in obstacles:
        exp_occ = 0
        for s, occ in sr.items():
            dist = mean_dist([s], gw.feature_locations[o])
            exp_occ += dist*occ
        optimal_policy_expected_distance[o] = exp_occ
    optimal_policy_mindist = {o: list() for o in obstacles}
    for _ in range(n_simulations):
        traj = pi.run_on(gw).state_traj
        for o in obstacles:
            optimal_policy_mindist[o].append(min_dist(traj, gw.feature_locations[o]))
    optimal_policy_mindist = {o: sum(d)/len(d) for o, d in optimal_policy_mindist.items()}

    return dict({
        'goal_mindist': {o: min_dist(gw.absorbing_states, gw.feature_locations[o]) for o in obstacles},
        'start_mindist': {o: min_dist(gw.initial_states, gw.feature_locations[o]) for o in obstacles},
        'walls_mindist': {o: min_dist(gw.feature_locations['#'], gw.feature_locations[o]) for o in obstacles},
        'center_mindist': {o: min_dist([center], gw.feature_locations[o]) for o in obstacles},
        'optimal_policy_expected_distance': optimal_policy_expected_distance, #expected distance from the optimal policy
        'optimal_policy_minimum_distance': optimal_policy_mindist
    })