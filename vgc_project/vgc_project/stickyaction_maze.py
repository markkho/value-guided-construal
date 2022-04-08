from collections import namedtuple
from itertools import product
from vgc_project.maze import Maze, Location
from msdm.core.problemclasses.mdp import TabularMarkovDecisionProcess
from msdm.core.utils.funcutils import cached_property
from msdm.core.distributions import DictDistribution

StickyActionState = namedtuple("StickyActionState", "last_dx_nonzero last_dy_nonzero x y")

class StickyActionMaze(TabularMarkovDecisionProcess):
    def __init__(
        self,
        action_deviation_reward=-1,
        **kwargs
    ):
        self.maze= Maze(**kwargs)
        self.action_deviation_reward = action_deviation_reward
        self.discount_rate = self.maze.discount_rate
    
    @cached_property
    def state_list(self):
        last_dxdy_nonzero_vals = [
            (False, False),
            (True, False),
            (False, True),
        ]
        ss = []
        for joint in product(last_dxdy_nonzero_vals, self.maze.state_list):
            (last_dx_nonzero, last_dy_nonzero), loc = joint
            ss.append(StickyActionState(last_dx_nonzero, last_dy_nonzero, *loc))
        return tuple(ss)
    
    def next_state_dist(self, s, a):
        if self.is_terminal(s):
            return DictDistribution({})
        dx_nonzero = a.dx != 0
        dy_nonzero = a.dy != 0
        ns_dist = {}
        for loc, loc_prob in self.maze.next_state_dist((s.x, s.y), a).items():
            ns_dist[StickyActionState(dx_nonzero, dy_nonzero, *loc)] = loc_prob
        return DictDistribution(ns_dist)

    def initial_state_dist(self):
        s0_dist = self.maze.initial_state_dist().marginalize(
            lambda loc: StickyActionState(False, False, *loc)
        )
        return s0_dist

    def sticky_action_reward(self, s, a):
        dx_nonzero = a.dx != 0
        dy_nonzero = a.dy != 0
        if s.last_dx_nonzero != dx_nonzero:
            return self.action_deviation_reward
        elif s.last_dy_nonzero != dy_nonzero:
            return self.action_deviation_reward
        return 0

    def reward(self, s, a, ns):
        g_reward = self.maze.reward((s.x, s.y), a, (ns.x, ns.y))
        sticky_action_reward = self.sticky_action_reward(s, a)
        return g_reward + sticky_action_reward
            
    def actions(self, s):
        return self.maze.actions((s.x, s.y))

    def is_terminal(self, s):
        return self.maze.is_terminal((s.x, s.y))
    