import joblib
import numpy as np
import random
import functools
from types import SimpleNamespace

from vgc_project.vgc import value_guided_construal
from vgc_project.heuristic_search import trajectory_based_heuristic_search, graph_based_heuristic_search
from vgc_project.successor_rep import optimal_bottleneck, successor_representation
from vgc_project.maze_stats import maze_obstacle_statistics

def create_modeling_interface(
    *,
    use_cache=True,
    lru_cache_maxsize=None,
    joblib_cache_location=None
):
    joblibmemory = joblib.Memory(joblib_cache_location, verbose=0)
    model_functions = [
        value_guided_construal,
        trajectory_based_heuristic_search,
        graph_based_heuristic_search,
        optimal_bottleneck,
        maze_obstacle_statistics,
        successor_representation
    ]
    mods = SimpleNamespace()
    for mod in model_functions:
        if use_cache:
            joblib_func = joblibmemory.cache()(mod)
            mod = functools.wraps(mod)(joblib_func)
            mod = functools.lru_cache(maxsize=lru_cache_maxsize)(mod)
        setattr(mods, mod.__name__, mod)

    def predictions(tile_array, obstacle, seed=None):
        random.seed(seed)
        traj_seed, graph_seed = [random.randint(0, int(1e20)), random.randint(0, int(1e20))]
        bottleneck       = mods.optimal_bottleneck(tile_array=tile_array)
        maze_stats       = mods.maze_obstacle_statistics(tile_array=tile_array, n_simulations=100)
        sr               = mods.successor_representation(tile_array=tile_array)

        vgc              = mods.value_guided_construal(tile_array=tile_array, construal_inverse_temp=10, discount_rate=1.0 - 1e-5)
        traj_based       = mods.trajectory_based_heuristic_search(tile_array=tile_array, seed=traj_seed, heuristic_type="no_obstacles", n_simulations=200)
        graph_based      = mods.graph_based_heuristic_search(tile_array=tile_array, seed=graph_seed, heuristic_type="no_obstacles", n_simulations=200)
        preds = {
            "vgc_weight": vgc['obstacle_probs'][obstacle],
            "log_traj_based_hitcount": np.log(1 + traj_based['mean_hit_counts'][obstacle]),
            "graph_based_hitcount": graph_based['mean_hit_counts'][obstacle],
            "goal_dist": maze_stats['goal_mindist'][obstacle],
            "start_dist": maze_stats['start_mindist'][obstacle],
            "optpolicy_dist": maze_stats['optimal_policy_minimum_distance'][obstacle],
            "walls_dist": maze_stats['walls_mindist'][obstacle],
            "center_dist": maze_stats['center_mindist'][obstacle],
            "bottleneck_dist": bottleneck['min_visited_bottleneck_distances'][obstacle],
            "sr_occ": sr['obstacle_occupancy'][obstacle]
        }
        return preds
    mods.predictions = predictions
    return mods
