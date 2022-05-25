import numpy as np
from vgc_project.sparse import \
    SparsePolicyIteration, SparseValueIteration, SparseTabularMDP
from msdm.core.distributions import DictDistribution
from msdm.algorithms import PolicyIteration, ValueIteration
from msdm.domains import GridWorld as OriginalGridWorld

class GridWorld(OriginalGridWorld):
    def next_state_dist(self, s, a):
        if self.is_terminal(s): # in case gridworld is not handling terminal states properly itself
            return DictDistribution({})
        return super(GridWorld, self).next_state_dist(s, a)

class SparseGridWorld(SparseTabularMDP, GridWorld):
    pass

gw_params = dict(
    tile_array=(
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
    ),
    absorbing_features='G',
    wall_features="#0123456789",
    initial_features='S',
    step_cost=-1,
    discount_rate=.99,
)

def test_sparsemdp_matrix_equivalence():
    gw_sp = SparseGridWorld(**gw_params)
    gw = GridWorld(**gw_params)
    assert (gw_sp.transition_matrix.A.reshape(len(gw.state_list), len(gw.action_list), len(gw.state_list)) == gw.transition_matrix).all()
    assert (gw_sp.reward_matrix.A.reshape(len(gw.state_list), len(gw.action_list), len(gw.state_list)) == gw.reward_matrix).all()
    assert (gw_sp.state_action_reward_matrix.A == gw.state_action_reward_matrix).all()

def test_sparse_nonsparse_solvers():
    gw_sp = SparseGridWorld(**gw_params)
    gw = GridWorld(**gw_params)
    re = gw.reachable_state_vec

    sppi_res = SparsePolicyIteration(iterations=200).plan_on(gw_sp)
    pi_res = PolicyIteration(iterations=200).plan_on(gw)
    assert np.isclose(sppi_res.initial_value, pi_res.initial_value)
    assert np.isclose(sppi_res._valuevec*re, pi_res._valuevec*re).all()

    spvi_res = SparseValueIteration(iterations=2000).plan_on(gw_sp)
    vi_res = ValueIteration(iterations=2000).plan_on(gw)
    assert np.isclose(spvi_res.initial_value, vi_res.initial_value)
    assert np.isclose(spvi_res._valuevec*re, vi_res._valuevec*re).all()