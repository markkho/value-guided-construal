import numpy as np
from itertools import product
from vgc_project.maze import Maze

def test_basic_maze_properties():
    pw=.94
    ps=.6

    m = Maze(
        tile_array=(
            ".j.",
            "x#3"
        ),
        absorbing_features=("j",),
        wall_features=("#","3"),
        default_features=(".",),
        initial_features=("x",),
        step_cost=-1,
        wall_bump_cost=0,
        wall_block_prob=pw,
        success_prob=ps,
        discount_rate=1.0,
        include_action_effect=True,
        include_wall_effect=True,
        include_terminal_state_effect=True,
        wall_bias=0.
    )

    # all locations are part of state space
    assert list(m.state_list) == list(product(range(3), range(2)))

    # fixed action ordering
    assert list(m.action_list) == [(1, 0), (-1, 0), (0, 0), (0, 1), (0, -1)] 
    right, left, wait, up, down = m.action_list

    # all non-terminal state-actions should have the step cost
    sa_rf = (m.reward_matrix*m.transition_matrix).sum(-1)
    non_term_sa_rf = sa_rf[m.nonterminal_state_vec]
    assert (non_term_sa_rf == m.step_cost).all()

    # transition function
    tf = m.transition_matrix
    nss = tf.shape[0]
    aa = m.action_list
    ss = m.state_list

    # wait action
    assert (tf[np.arange(nss), 2, np.arange(nss)] == 1).all()

    # going off edge of grid leads you to stay in place
    assert tf[ss.index((0, 0)), aa.index(left), ss.index((0, 0))] == 1
    assert tf[ss.index((2, 0)), aa.index(right), ss.index((2, 0))] == 1
    
    # dynamics of goign from nonwall to nonwall
    assert tf[ss.index((0, 0)), aa.index(up), ss.index((0, 1))] == ps

    # exiting a wall into a non-wall or wall has the same probability
    # namely, we ignore the wall dynamics
    assert tf[ss.index((1, 0)), aa.index(left), ss.index((0, 0))] == ps
    assert tf[ss.index((1, 0)), aa.index(right), ss.index((2, 0))] == ps

    # dynamics of crashing into a wall
    assert np.isclose(
        tf[ss.index((0, 0)), aa.index(right), ss.index((1, 0))], 
        (ps*(1 - pw))/(ps*(1 - pw) + pw*(1 - ps))
    )

    # terminal state leads to itself with probability 1
    # and being in it always gives reward 0
    assert not m.nonterminal_state_vec[ss.index((1, 1))]
    assert m.nonterminal_state_vec.sum() == 5
    assert (tf[ss.index((1, 1)), :, ss.index((1, 1))] == 1).all()
    assert (sa_rf[ss.index((1, 1))] == 0).all()