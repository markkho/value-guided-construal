import json
import random
import logging
import datetime
import time
import pprint
from itertools import product

import numpy as np
import pandas as pd
import fire
from scipy import stats
from joblib import Parallel, delayed

from vgc_project import utils
from vgc_project.dynamic_vgc import dynamic_vgc
from vgc_project.dynamic_vgc.dynamic_vgc import solve_construal_switching_mdp


def start_logger_if_necessary(log_file):
    logger = logging.getLogger("mylogger")
    if len(logger.handlers) == 0:
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(log_file, mode='a')
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s"))
        logger.addHandler(fh)
    return logger

def run_maze(maze_name, tile_array, dvgc_params):
    logger = start_logger_if_necessary('gridsearch.log')
    logger.debug(f"Calculating {maze_name}")
    eval_stats = dynamic_vgc(
        tile_array=tuple(tile_array),
        **dvgc_params
    )
    dvgc_preds = []
    obstacles = set(''.join(tile_array)) & set("0123456789")
    for o in obstacles:
        dvgc_preds.append(dict(
            grid=maze_name,
            obstacle=f"obs-{o}",
            dvgc_occ=eval_stats['obs_occ'].get(o, 0),
            dvgc_occ_prob=eval_stats['obs_prob'].get(o, 0)
        ))
    return {
        'grid': maze_name,
        'eval_stats': eval_stats,
        'dvgc_preds': dvgc_preds
    }

def calculate_maze_predictions(dvgc_params, mazes_to_run, parallel=None):
    if parallel:
        maze_predictions = parallel(
            delayed(run_maze)(maze_name, tile_array, dvgc_params)
            for maze_name, tile_array in mazes_to_run.items()
        )
    else:
        maze_predictions = [
            run_maze(maze_name, tile_array, dvgc_params)
            for maze_name, tile_array in mazes_to_run.items()
        ]
    return maze_predictions

def main(n_jobs=2, seed=21912491, run_name=None):
    if run_name is None:
        nowstr = datetime.datetime.now().strftime("%m-%d-%Y_%H-%M")
        run_name = f"gridsearch-{nowstr}"
    start = time.time()
    open('gridsearch.log', 'a').close()
    logger = start_logger_if_necessary('gridsearch.log')

    mazes = json.load(open("./mazes.json", 'r'))

    default_dvgc_params = dict(
        ground_policy_inv_temp=5,
        ground_policy_rand_choose=0.,
        ground_discount_rate=1.0-1e-5,
        action_deviation_reward=0,
        wall_bias=0.,
        wall_bump_cost=0,
        added_obs_cost=1,
        removed_obs_cost=0,
        continuing_obs_cost=0,
        construal_switch_cost=0.,
        switching_inv_temp=5,
        switching_rand_choose=0.,
        switching_discount_rate=1-1e-5,
        max_construal_size=3,
        n_simulations=100,
        seed=seed
    )

    ground_param_space = [
        ('wall_bias', [0, .01, .1, 1]),
        ('wall_bump_cost', [0, -.1, -1]),
        ('ground_policy_inv_temp', [1, 3, 5, 7]),
        ('ground_policy_rand_choose', [0, .1, .2]),
    ]
    switch_param_space = [
        ('switching_inv_temp', [1, 3, 5, 7, 9]),
        ('switching_rand_choose', [0, .05, .1, .2, .3]),
    ]
    ground_param_names, ground_param_vals = zip(*ground_param_space)
    switch_param_names, switch_param_vals = zip(*switch_param_space)

    all_maze_preds = []
    with Parallel(n_jobs=n_jobs, backend="loky") as parallel:
        param_iter = list(product(
            enumerate(product(*ground_param_vals)),
            enumerate(product(*switch_param_vals))
        ))
        logger.debug(f"Parameter sets: {len(param_iter)}")
        for (ground_i, ground_params), (switch_i, switch_params) in param_iter:
            ground_params = dict(zip(ground_param_names, ground_params))
            switch_params = dict(zip(switch_param_names, switch_params))
            if switch_i == 0:
                with open(f"./results/{run_name}.json", "w") as file:
                    file.write(json.dumps(all_maze_preds))
                logger.debug(f"Time elapsed: {time.time() - start}")
                logger.debug(f"Construal Switching Solver Cache")
                logger.debug(pprint.pformat(dict(solve_construal_switching_mdp.cache_info()._asdict())))
                logger.debug("Ground Params:")
                logger.debug(pprint.pformat(ground_params))
            logger.debug("Switch Params:")
            logger.debug(pprint.pformat(switch_params))

            # calculate maze predictions
            params = {
                **default_dvgc_params,
                **ground_params,
                **switch_params
            }
            if switch_i == 0:
                maze_preds = calculate_maze_predictions(params, mazes, parallel=None)
            else:
                maze_preds = calculate_maze_predictions(params, mazes, parallel=parallel)

            # save results
            maze_obs_preds = sum([r['dvgc_preds'] for r in maze_preds], [])
            maze_obs_preds = [{**params, **r}for r in maze_obs_preds]
            all_maze_preds.extend(maze_obs_preds)

    with open(f"./results/{run_name}.json", "w") as file:
        file.write(json.dumps(all_maze_preds))

    run_summary = dict(
        param_sets_evaluated=len(param_iter),
        total_time=time.time() - start,
        cache_stats=dict(solve_construal_switching_mdp.cache_info()._asdict()),
        seed=seed,
        n_jobs=n_jobs
    )
    with open(f"./results/{run_name}-summary.json", "w") as file:
        file.write(json.dumps(run_summary))

    logger.debug(pprint.pformat(run_summary))
    logger.debug("Done")

if __name__ == "__main__":
    fire.Fire(main)
