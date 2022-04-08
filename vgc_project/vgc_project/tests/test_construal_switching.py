import numpy as np 

from msdm.algorithms import PolicyIteration, ValueIteration

from vgc_project.sparse import SparsePolicyIteration
from vgc_project.dynamic_vgc import ConstrualSwitchingMDP
from vgc_project.stickyaction_maze import StickyActionMaze
from vgc_project.maze import Maze

def test_construal_switching_mdp():
    ground_mdp_params = dict(
        tile_array=(
            '.2..G',
            '.##.3',
            'S.1..',
            '..1..',
            '0....',
        ),
        feature_rewards=(("G", 0), ),
        absorbing_features=("G",),
        wall_features="#0123456789",
        default_features=(".",),
        initial_features=("S",),
        step_cost=-1,
        discount_rate=1.0-1e-5,
        success_prob=1-1e-5
    )
    cs_mdp_params = dict(
        construals=("", "0123", "013"), 
        initial_construal="",
        eval_ground_mdp_params=ground_mdp_params,
        policy_ground_mdp_params=ground_mdp_params,
        ground_policy_inv_temp=None,
        ground_policy_rand_choose=0.,
        added_obs_cost=1,
        removed_obs_cost=0,
        continuing_obs_cost=0,
        construal_switch_cost=0,
        discount_rate=1-1e-5,
    )
    maze = Maze(**ground_mdp_params)
    cs_mdp = ConstrualSwitchingMDP(**cs_mdp_params)
    maze_res = PolicyIteration().plan_on(maze)
    cs_mdp_res = SparsePolicyIteration().plan_on(cs_mdp)

    # We expect the switching mdp cost to be the ground cost minus the cost of the construal
    assert np.isclose(cs_mdp_res.initial_value, maze_res.initial_value - len("0123"))

    cs_mdp._compare_to_base_implementations()

def test_construal_switching_mdp_with_stickyactions():
    ground_mdp_params = dict(
        tile_array=(
            '.2..G',
            '.##.3',
            'S.1..',
            '..1..',
            '0....',
        ),
        feature_rewards=(("G", 0), ),
        absorbing_features=("G",),
        wall_features="#0123456789",
        default_features=(".",),
        initial_features=("S",),
        step_cost=-1,
        discount_rate=1.0-1e-5,
        success_prob=1-1e-5,
        action_deviation_reward=-1,
    )
    cs_mdp_params = dict(
        construals=("", "0123", "013"), 
        initial_construal="",
        eval_ground_mdp_params=ground_mdp_params,
        policy_ground_mdp_params=ground_mdp_params,
        ground_policy_inv_temp=None,
        ground_policy_rand_choose=0.,
        added_obs_cost=1,
        removed_obs_cost=0,
        continuing_obs_cost=0,
        construal_switch_cost=0,
        discount_rate=1-1e-5,
    )
    maze = StickyActionMaze(**ground_mdp_params)
    cs_mdp = ConstrualSwitchingMDP(**cs_mdp_params)
    maze_res = PolicyIteration().plan_on(maze)
    cs_mdp_res = SparsePolicyIteration().plan_on(cs_mdp)

    # We expect the switching mdp cost to be the ground cost minus the cost of the construal
    assert np.isclose(cs_mdp_res.initial_value, maze_res.initial_value - len("0123"))

    cs_mdp._compare_to_base_implementations()