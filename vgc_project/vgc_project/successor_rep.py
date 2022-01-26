from collections import defaultdict
import numpy as np

from msdm.domains import GridWorld
from msdm.algorithms import PolicyIteration

from vgc_project.utils import min_dist, mean_dist

def successor_representation(
    tile_array,
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
        wall_features=("#",),
        default_features=default_features,
        initial_features=initial_features,
        success_prob=1 - 1e-5
    )
    noobs = GridWorld(**gw_params)
    noobs_plan = PolicyIteration().plan_on(noobs)
    occ = noobs_plan.policy.evaluate_on(noobs).occupancy
    focc = defaultdict(float)
    for loc, f in noobs.location_features.items():
        focc[f] += occ[loc]
    return {
        'obstacle_occupancy': dict(focc)
    }

def compute_eigenvector_partition(mdp, degmat, adjmat, eigen_idx):
    laplacian = degmat - adjmat
    eigvals_lap, eigvecs_lap = np.linalg.eig(laplacian)
    eigvecs_lap = eigvecs_lap[:,eigvals_lap.argsort()]
    eigvals_lap = eigvals_lap[eigvals_lap.argsort()]
    #remove 0 eigenvalues
    eigvecs_lap = eigvecs_lap[:, eigvals_lap != 0]
    eigvals_lap = eigvals_lap[eigvals_lap != 0]
    eig_partition = dict(zip(mdp.state_list, eigvecs_lap[:,eigen_idx]))
    return eig_partition

def optimal_bottleneck(
    *,
    tile_array,
    feature_rewards=(("G", 0), ),
    absorbing_features=("G",),
    wall_features="#0123456789",
    default_features=(".",),
    initial_features=("S",),
    step_cost=-1,
    discount_rate=1.0
):
    bottleneck_gw = GridWorld(
        tile_array=tile_array,
        wall_features=wall_features,
        initial_features=initial_features
    )

    # compute bottleneck cut
    eigen_idx = 1
    P = np.einsum("san->sn", bottleneck_gw.transition_matrix)
    adjmat = (P > 0).astype(np.int64)
    degmat = np.diag(adjmat.sum(axis=1))
    eig_partition = compute_eigenvector_partition(bottleneck_gw, degmat, adjmat, eigen_idx)
    cut = set([])
    for s in bottleneck_gw.reachable_states():
        for a in bottleneck_gw.actions(s):
            for ns in bottleneck_gw.next_state_dist(s, a).support:
                if np.sign(eig_partition[s]) != np.sign(eig_partition[ns]):
                    cut.add(frozenset([s, ns]))

    bottlenecks = set.union(*[set(pair) for pair in cut])
    gw = GridWorld(
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
    res = PolicyIteration().plan_on(gw)
    visited = {s for s, o in res.policy.evaluate_on(gw).occupancy.items() if o > 0}
    visited_bottlenecks=visited & bottlenecks
    res = dict(
        mean_visited_bottleneck_distances={o: mean_dist(visited_bottlenecks, locs) for o, locs in gw.feature_locations.items()},
        min_visited_bottleneck_distances={o: min_dist(visited_bottlenecks, locs) for o, locs in gw.feature_locations.items()},
        mean_general_bottleneck_distances={o: mean_dist(bottlenecks, locs) for o, locs in gw.feature_locations.items()},
        min_general_bottleneck_distances={o: min_dist(bottlenecks, locs) for o, locs in gw.feature_locations.items()},
        bottlenecks=bottlenecks,
        visited_bottlenecks=visited_bottlenecks,
    )
    return res