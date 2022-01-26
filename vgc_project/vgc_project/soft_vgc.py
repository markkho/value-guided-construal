"""
Version of VGC for doing parameter fitting.
"""
from functools import lru_cache
import numpy as np
from frozendict import frozendict

from msdm.domains import GridWorld
from msdm.core.distributions import SoftmaxDistribution, DictDistribution, DeterministicDistribution
from msdm.core.utils.funcutils import cached_property

from vgc_project.construal_utils import create_gridworld, solve_gridworld, evaluate_construal, powerset


def epsilon_softmax_policy_matrix(q, am, softmax_temp, rand_choose):
    pi = q/softmax_temp
    pi = pi - pi.max(axis=-1, keepdims=True)
    pi = np.exp(pi)
    pi = pi/pi.sum(axis=-1, keepdims=True)
    eps = np.ones_like(pi)
    pi = rand_choose * am/am.sum(axis=-1, keepdims=True) + (1 - rand_choose)*pi
    assert np.isclose(pi.sum(axis=-1), 1).all(), pi
    return pi

def evaluate_policy_matrix(pi, tf, rf, discount_rate, nt, s0):
    mp = np.einsum("sa,san->sn", pi, tf)
    assert np.isclose(mp.sum(-1), 1).all()
    s_rf = np.einsum("sa,san,san->s", pi, tf, rf)
    v = np.linalg.solve(np.eye(len(s0)) - discount_rate*mp, s_rf)
    v0 = v@s0
    return v0

class SoftValueGuidedConstrualModel:
    def __init__(
        self,
        vor,
        construal_inverse_temp,
        construal_rand_choose,
        obs_awareness_prior
    ):
        self.vor = vor
        self.construal_inverse_temp = construal_inverse_temp
        self.construal_rand_choose = construal_rand_choose
        self.obs_awareness_prior = obs_awareness_prior
        
    @cached_property
    def construal_prob(self):
        construal_prob = SoftmaxDistribution({c: self.construal_inverse_temp*v for c, v in self.vor.items()})
        rand_construal = DictDistribution.uniform(construal_prob.support)
        construal_prob = rand_construal*self.construal_rand_choose | construal_prob*(1 - self.construal_rand_choose)
        return construal_prob
    
    @cached_property
    def obstacle_probs(self):
        obstacles = set.union(*[set(c) for c in self.vor.keys()])
        construal_obs_probs = {o: self.construal_prob.marginalize(lambda c: o in c)[True] for o in obstacles}
        obs_probs = {}
        for o, p in construal_obs_probs.items():
            logit = np.log(p/(1-p)) + np.log(self.obs_awareness_prior/(1-self.obs_awareness_prior))
            obs_probs[o] = 1/(1 + np.exp(-logit))
        return obs_probs
    
    def nll_binomial(self, obstacle, count, total):
        assert count <= total
        p = self.obstacle_probs[obstacle]
        return -(np.log(p)*count + np.log(1 - p)*(total - count))
    
    def nll_logodds(self, obstacle, val):
        p = self.obstacle_probs[obstacle]
        logodds = np.log(p/(1-p))
        return (logodds - val)**2
    
@lru_cache(maxsize=int(1e7))
def soft_value_guided_construal(
    *,
    tile_array,
    construal_inverse_temp,
    construal_rand_choose,
    policy_inverse_temp,
    policy_rand_choose,
    construal_weight,
    obs_awareness_prior=.5,
    success_prob=1-1e-5,
    
    feature_rewards=(("G", 0), ),
    absorbing_features=("G",),
    wall_features="#0123456789",
    default_features=(".",),
    initial_features=("S",),
    step_cost=-1,
    discount_rate=1.0
):
    gw_params = dict(
        tile_array=tile_array,
        feature_rewards=frozendict(feature_rewards),
        step_cost=step_cost,
        discount_rate=discount_rate,
        absorbing_features=tuple(absorbing_features),
        wall_features=wall_features,
        default_features=default_features,
        initial_features=initial_features,
        success_prob=success_prob
    )
    gw = create_gridworld(gw_params)
    obstacles = [t for t in set(tuple("".join(tile_array))) if t in "0123456789"]
    vor = {}
    for construal in list(powerset(obstacles)):
        cgw_params = {
            **gw_params,
            "wall_features": "#"+''.join(sorted(construal))
        }
        cgw = create_gridworld(cgw_params)
        cpi = solve_gridworld(cgw_params)
        eps_soft_pi = epsilon_softmax_policy_matrix(
            q = cpi._qvaluemat,
            am = cgw.action_matrix,
            softmax_temp = 1/policy_inverse_temp,
            rand_choose = policy_rand_choose
        )
        initial_value = evaluate_policy_matrix(
            pi=eps_soft_pi,
            tf=gw.transition_matrix,
            rf=gw.reward_matrix,
            discount_rate=gw.discount_rate,
            nt=gw.nonterminal_state_vec,
            s0=gw.initial_state_vec,
        )
        assert initial_value < -10
        vor[construal] = initial_value - construal_weight*len(construal)
    return SoftValueGuidedConstrualModel(
        vor=vor,
        construal_inverse_temp=construal_inverse_temp,
        construal_rand_choose=construal_rand_choose,
        obs_awareness_prior=obs_awareness_prior
    )