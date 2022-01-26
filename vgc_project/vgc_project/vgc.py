"""
Value-guided construal with product of experts.

Note: This uses a custom Maze MDP implementation rather than
the GridWorld MDP implementation that comes with msdm
in order to make it easier to calculate/combine effects.
"""
from itertools import combinations
from types import SimpleNamespace
import numpy as np
from msdm.algorithms import PolicyIteration, ValueIteration
from msdm.core.distributions import SoftmaxDistribution

from vgc_project.utils import powerset
from vgc_project.maze import Maze

def generate_task_effects(true_maze_params):
    obstacle_effects = {}
    effect_chars = set(''.join(true_maze_params['tile_array'])) & set('0123456789')
    for wall_char in effect_chars:
        effect_maze = Maze(
            **{
                **true_maze_params,
                **dict(
                    wall_features=(wall_char,),
                    include_action_effect=False,
                    include_wall_effect=True,
                    include_terminal_state_effect=False
                )
            }
        )
        obstacle_effects[wall_char] = effect_maze.transition_matrix
    action_effect = Maze(**{
        **true_maze_params,
        **dict(
            wall_features=(),
            include_action_effect=True,
            include_wall_effect=False,
            include_terminal_state_effect=False
        )
    }).transition_matrix
    goal_effect = Maze(**{
        **true_maze_params,
        **dict(
            wall_features=(),
            include_action_effect=False,
            include_wall_effect=False,
            include_terminal_state_effect=True
        )
    }).transition_matrix
    center_wall_effect = Maze(**{
        **true_maze_params,
        **dict(
            wall_features=('#',),
            include_action_effect=False,
            include_wall_effect=True,
            include_terminal_state_effect=False
        )
    }).transition_matrix
    return SimpleNamespace(
        obstacle_effects=obstacle_effects,
        action_effect=action_effect,
        goal_effect=goal_effect,
        center_wall_effect=center_wall_effect
    )

def create_construed_transition_matrix(task_effects, construal):
    tf = np.zeros_like(task_effects.center_wall_effect)
    tf += np.log(task_effects.center_wall_effect)
    tf += np.log(task_effects.action_effect)
    tf += np.log(task_effects.goal_effect)
    for obstacle in construal:
        obstacle_effect = task_effects.obstacle_effects[obstacle]
        tf += np.log(obstacle_effect)
    tf = np.exp(tf)
    tf /= tf.sum(-1, keepdims=True)
    return tf

class ConstruedMaze(Maze):
    def __init__(
        self,
        true_maze_params,
        construal
    ):
        super().__init__(**true_maze_params)
        task_effects = generate_task_effects(true_maze_params)
        self._transition_matrix = create_construed_transition_matrix(task_effects, construal)
        self.wall_features = "#"+str(sorted(construal))
        self.construal = construal
        
    def plot(
        self,
        feature_colors=None,
        mark_initial_states=True,
        mark_terminal_states=True,
        ax=None
    ):
        if feature_colors is None:
            feature_colors = {
                **{o: "mediumblue" for o in self.construal},
                **{o: "gainsboro" for o in "0123456789" if o not in self.construal},
                "#": 'k',
                'G': 'yellow'
            }
        return super().plot(
            feature_colors=feature_colors,
            mark_initial_states=mark_initial_states,
            mark_terminal_states=mark_terminal_states,
            ax=ax
        )
    
def value_guided_construal(
    *,
    tile_array,
    construal_inverse_temp,
    feature_rewards=(("G", 0), ),
    absorbing_features=("G",),
    wall_features="#0123456789",
    default_features=(".",),
    initial_features=("S",),
    step_cost=-1,
    discount_rate=1.0-1e-5,
    planning_alg="policy_iteration"
):
    assert planning_alg in ("policy_iteration", "value_iteration")
    true_maze_params = dict(
        tile_array=tile_array,
        feature_rewards=feature_rewards,
        absorbing_features=absorbing_features,
        wall_features=wall_features,
        default_features=default_features,
        initial_features=initial_features,
        step_cost=step_cost,
        discount_rate=discount_rate,
        wall_bump_cost=0,
        wall_block_prob=1.0,
        success_prob=1-1e-5,
        include_action_effect=True,
        include_wall_effect=True,
        include_terminal_state_effect=True
    )
    true_maze = Maze(**true_maze_params)
    obstacle_chars = set(''.join(tile_array)) & set('0123456789')
    vor = {}
    for construal in powerset(obstacle_chars):
        construal = ''.join(sorted(construal))
        construed_maze = ConstruedMaze(true_maze_params, construal)
        if planning_alg == "policy_iteration":
            plan_res = PolicyIteration().plan_on(construed_maze)
        elif planning_alg == "value_iteration":
            plan_res = ValueIteration().plan_on(construed_maze)
        assert plan_res.converged
        policy_utility = plan_res.policy.evaluate_on(true_maze).initial_value
        vor[construal] = policy_utility - len(construal)
    c_dist = SoftmaxDistribution({c: v*construal_inverse_temp for c, v in vor.items()})
    obstacle_probs = {o: c_dist.expectation(lambda c: o in c) for o in obstacle_chars}
    return dict(
        obstacle_probs=obstacle_probs,
        value_of_representation=vor
    )