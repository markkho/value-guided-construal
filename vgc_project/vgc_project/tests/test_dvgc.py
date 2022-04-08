import numpy as np
from types import SimpleNamespace
from vgc_project.dynamic_vgc import dynamic_vgc

tile_array=(
    'S0...2G3',
    '.0.1...3',
    '...1....',
)
default_dynamic_vgc_params = dict(
    tile_array=tile_array,
    ground_policy_inv_temp=None,
    ground_policy_rand_choose=0.,
    ground_discount_rate=1.0-1e-10,
    action_deviation_reward=0,
    wall_bias=0.,
    wall_bump_cost=0.,
    added_obs_cost=1,
    removed_obs_cost=0,
    continuing_obs_cost=0,
    construal_switch_cost=0,
    switching_inv_temp=100,
    switching_rand_choose=0.,
    switching_discount_rate=1-1e-10,
    max_construal_size=3,
    n_simulations=1000,
    seed=12947
)

def test_dynamic_vgc():
    res = dynamic_vgc(**default_dynamic_vgc_params)
    res = SimpleNamespace(**res)
    expected_steps = 12
    assert sum(res.loc_occ.values()) == expected_steps
    assert res.loc_occ[(7, 0)] == 0
    assert res.loc_occ[(0, 1)] == 1
    assert res.obs_occ['0'] > res.obs_occ.get('3', 0.0) == 0
    assert np.isclose(res.initial_value, -expected_steps - len("012"))
    assert np.isclose(
        res.no_aux_cost_ground_initial_value,
        res.no_aux_cost_switch_mdp_initial_value
    )
    
def test_dynamic_vgc_with_sticky_action_cost():
    res = dynamic_vgc(**{
        **default_dynamic_vgc_params,
        "action_deviation_reward": -.1
    })
    res = SimpleNamespace(**res)
    expected_steps = 12
    expected_turns = 7
    assert sum(res.loc_occ.values()) == expected_steps
    assert res.loc_occ[(7, 0)] == 0
    assert res.loc_occ[(0, 1)] == 1
    assert res.obs_occ['0'] > res.obs_occ.get('3', 0.0) == 0
    assert np.isclose(res.initial_value, -expected_steps - len("012")- expected_turns*.1)
    assert np.isclose(
        res.no_aux_cost_ground_initial_value,
        res.no_aux_cost_switch_mdp_initial_value
    )
