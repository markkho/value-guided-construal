from itertools import product
import numpy as np
import matplotlib.pyplot as plt
from collections import namedtuple, defaultdict
from msdm.core.problemclasses.mdp import TabularMarkovDecisionProcess
from msdm.core.distributions import DictDistribution

from vgc_project.gridmdp import GridMDP, Location, GridAction
from vgc_project.gridmdp.plotting import GridMDPPlotter

class Maze(GridMDP, TabularMarkovDecisionProcess):
    def __init__(
        self,
        tile_array,
        feature_rewards=None,
        absorbing_features=("g",),
        wall_features=("#",),
        default_features=(".",),
        initial_features=("s",),
        step_cost=-1,
        wall_bump_cost=0,
        wall_block_prob=1.0,
        success_prob=1.0,
        discount_rate=1.0,
        include_action_effect=True,
        include_wall_effect=True,
        include_terminal_state_effect=True
    ):
        """
        An optimized gridworld implementation with additional parameters
        """

        assert step_cost <= 0
        assert wall_bump_cost <= 0
        assert 0 <= wall_block_prob <= 1.0
        assert 0 <= success_prob <= 1.0
        assert 0 <= discount_rate <= 1.0

        if isinstance(tile_array, (tuple, list)):
            grid = '\n'.join(tile_array)
        else:
            grid = tile_array
        super().__init__(grid)

        self.absorbing_features = absorbing_features
        self.wall_features = wall_features
        self.default_features = default_features
        self.initial_features = initial_features
        self.discount_rate = discount_rate
        self.step_cost = step_cost
        self.wall_bump_cost = wall_bump_cost

        if feature_rewards is None:
            feature_rewards = {}
        if isinstance(feature_rewards, tuple):
            feature_rewards = dict(feature_rewards)

        self._set_up_states()
        self._set_up_actions()
        self._set_up_transition_reward_matrices(
            move_prob=success_prob,
            wall_block_prob=wall_block_prob,
            feature_rewards=feature_rewards,
            step_cost=step_cost,
            wall_bump_cost=wall_bump_cost,
            include_action_effect=include_action_effect,
            include_wall_effect=include_wall_effect,
            include_terminal_state_effect=include_terminal_state_effect
        )

    def next_state_dist(self, s, a):
        ns_probs = self.transition_matrix[self._state_index[s], self._action_index[a], :]
        return DictDistribution({ns: p for ns, p in zip(self.state_list, ns_probs) if p > 0})

    def initial_state_dist(self):
        return DictDistribution.uniform(self._initial_states)

    def reward(self, s, a, ns):
        return self.reward_matrix[
            self._state_index[s],
            self._action_index[a],
            self._state_index[ns]
        ]

    def actions(self, s):
        return self.action_list

    def is_terminal(self, s):
        return self.feature_at(s) in self.absorbing_features

    @property
    def state_list(self):
        return self._state_list

    @property
    def action_list(self):
        return self._action_list

    @property
    def initial_state_vec(self):
        return self._initial_state_vec

    @property
    def transition_matrix(self):
        return self._transition_matrix

    @property
    def reward_matrix(self):
        return self._reward_matrix

    @property
    def nonterminal_state_vec(self):
        return self._nonterminal_state_vec

    def is_wall(self, s):
        return self.feature_at(s) in self.wall_features

    def on_board(self, s):
        return (0 <= s.x < self._width) and (0 <= s.y < self._height)

    def _set_up_transition_reward_matrices(
        self,
        move_prob,
        wall_block_prob,
        feature_rewards,
        step_cost,
        wall_bump_cost,
        include_action_effect,
        include_wall_effect,
        include_terminal_state_effect
    ):
        ss = self.state_list
        aa = self.action_list

        # default transition potential
        tf_logits = np.ones((len(ss), len(aa), len(ss)))
        tf_logits = np.log(tf_logits/tf_logits.sum(-1, keepdims=True))
        rf = np.zeros((len(ss), len(aa), len(ss)))

        for (si, s), (ai, a) in product(enumerate(ss), enumerate(aa)):
            ns = Location(s.x + a.dx, s.y + a.dy)
            if not self.on_board(ns):
                ns = s
            nsi = self._state_index[ns]
            if include_action_effect:
                tf_logits[si, ai, :] = -float('inf')
                tf_logits[si, ai, si] = np.log(1 - move_prob)
                tf_logits[si, ai, nsi] = np.log(move_prob)
                rf[si, ai, si] += step_cost
                rf[si, ai, nsi] += step_cost

            if include_wall_effect and not self.is_wall(s) and self.is_wall(ns):
                tf_logits[si, ai, si] += np.log(wall_block_prob)
                tf_logits[si, ai, nsi] += np.log(1 - wall_block_prob)
                rf[si, ai, si] += wall_bump_cost
        assert not np.isnan(tf_logits).any()

        nt = self.nonterminal_state_vec.astype(bool)
        if include_terminal_state_effect:
            tf_logits[~nt,:,:] = -float('inf')
            tf_logits[~nt,:,~nt] = np.log(1/(~nt).sum())
            rf[~nt,:,:] = 0
        assert not np.isnan(tf_logits).any()

        tf = np.exp(tf_logits)
        assert not np.isnan(tf).any()
        tf[nt,:,:] = tf[nt,:,:]/tf[nt,:,:].sum(-1, keepdims=True)
        assert np.isclose(tf[nt,:,:].sum(-1), 1).all()
        # assert (tf[nt,:,:].sum(-1) == 1).all()
        self._transition_matrix = tf
        self._reward_matrix = rf

    def _set_up_states(self):
        ss = self.location_list
        self._state_list = ss
        self._state_index = {s: i for i, s in enumerate(ss)}
        terminal_state_vec = \
            np.array([self.feature_at(s) in self.absorbing_features for s in ss]).astype(bool)
        self._nonterminal_state_vec = ~terminal_state_vec
        self._initial_states = \
            sorted([s for s in ss if self.feature_at(s) in self.initial_features])
        self._initial_state_vec = \
            np.array([self.feature_at(s) in self.initial_features for s in self._state_list])
        self._initial_state_vec = self._initial_state_vec/self._initial_state_vec.sum()

    def _set_up_actions(self):
        self._action_list = (
            GridAction(1, 0),
            GridAction(-1, 0),
            GridAction(0, 0),
            GridAction(0, 1),
            GridAction(0, -1),
        )
        self._action_index = {a: i for i, a in enumerate(self._action_list)}

    def plot(
        self,
        feature_colors=None,
        mark_initial_states=True,
        mark_terminal_states=True,
        ax=None
    ):
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(8, 8))
        plotter = MazePlotter(self, ax=ax)
        if feature_colors is None:
            feature_colors = {
                **{d: 'mediumblue' for d in '0123456789'},
                '#': 'k',
                'G': 'yellow'
            }
        plotter.fill_features(
            feature_colors=feature_colors,
            default_color='w',
            Rectangle_kwargs=dict(
                zorder=-2
            )
        )
        if mark_initial_states:
            plotter.mark_features(
                feature_markers={f: 'o' for f in self.initial_features},
                plot_kwargs=dict(
                    markeredgecolor='cornflowerblue',
                    markersize=15,
                    markeredgewidth=2,
                    fillstyle='none',
                    zorder=-1
                )
            )
        if mark_terminal_states:
            plotter.mark_features(
                feature_markers={f: 'x' for f in self.absorbing_features},
                plot_kwargs=dict(
                    markeredgecolor='cornflowerblue',
                    markersize=15,
                    markeredgewidth=2,
                    # color='green',
                    fillstyle='none',
                    zorder=-1
                )
            )
        plotter.plot_outer_box()
        return plotter

class MazePlotter(GridMDPPlotter):
    def plot_policy(self, policy, arrow_width=.1):
        return self.plot_location_action_map(
            location_action_map=policy,
            vmin=0,
            vmax=1,
            arrow_width=arrow_width,
            visualization_type='arrow',
            color_value_func=lambda v: 'k'
        )
