import json
import random
from itertools import product

import tqdm
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from vgc_project.construal_search import \
    ConstrualSearch, ExhaustiveSearch, BreadthFirstSearch, DepthFirstSearch, \
    EventListener, BoundedDepthFirstSearch

def test_construal_search():
    mazes = {
        'grid-0-0': [
            '...3.0....G',
            '.333.0.....',
            '.....00.444',
            '6....#..4..',
            '6....#.....',
            '6..#####...',
            '6....#.....',
            '..1..#.2...',
            '111..222...',
            '..........5',
            'S.......555'
        ]
    }
    maze_name = "grid-0-0"
    rng = random.Random(1294)
    sims = []
    class BDFS3(BoundedDepthFirstSearch):
        bound = 3
    for construal_value_threshold, \
        Strategy in \
        product([0, -35],
                [ExhaustiveSearch, BreadthFirstSearch, DepthFirstSearch, BDFS3]):
        gw_params = dict(
            tile_array=tuple(mazes[maze_name]),
            feature_rewards=(("G", 0), ),
            absorbing_features=("G",),
            wall_features="#0123456789",
            default_features=(".",),
            initial_features=("S",),
            step_cost=-1,
            discount_rate=.99
        )
        event_listener = EventListener()
        strategy = Strategy(
            gw_params=gw_params,
            max_iterations=1000,
            construal_value_threshold=construal_value_threshold,
        )
        res = strategy.search(event_listener, rng=rng)
        sims.append(dict(
            **strategy.params(),
            construal_size=np.mean([len(c) for c in res.max_construals]),
            max_construal_size=max([len(c) for c in res.construal_values]),
            construal_utility=np.mean(list(res.max_construals_utilities.values())),
            maze_name=maze_name,
            construals_evaluated=len(res.construal_values),
            value=res.max_value
        ))
    sims = pd.DataFrame(sims)

    # these should all evaluate all construals when the threshold is 0
    assert (sims[sims['construal_value_threshold'] == 0]['construals_evaluated'] == 2**7).all()

    # with threshold, different algs have different number evaluated
    with_threshold = sims[sims['construal_value_threshold'] == -35]
    with_threshold = dict(zip(with_threshold['search_class'], with_threshold['construals_evaluated']))
    print(with_threshold)
    assert \
        with_threshold['ExhaustiveSearch'] > \
        with_threshold['BreadthFirstSearch'] > \
        with_threshold['BDFS3'] > \
        with_threshold['DepthFirstSearch']