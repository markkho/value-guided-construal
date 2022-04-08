from types import SimpleNamespace
import random
import math
import numpy as np
from msdm.core.problemclasses.mdp import TabularPolicy
from msdm.core.distributions import DictDistribution

class SparseTabularPolicy(TabularPolicy):
    def evaluate_on(self, mdp, n_simulations=1000, rng=random):
        state_occ = {s: [] for s in mdp.state_list}
        initial_value = []
        for i in range(n_simulations):
            traj = self.run_on(mdp, rng=rng)
            for s in state_occ.keys():
                state_occ[s].append(0)
            for s in traj.state_traj:
                state_occ[s][-1] += 1
            discounted_return = 0
            discount = 1.0
            for r in traj.reward_traj:
                discounted_return += r*discount
                discount *= mdp.discount_rate
            initial_value.append(discounted_return)

        return SimpleNamespace(
            initial_value=np.mean(initial_value),
            initial_value_sem=np.std(initial_value)/np.sqrt(n_simulations),
            occupancy={s: np.mean(occ) for s, occ in state_occ.items()},
            occupancy_sem={s: np.std(occ)/np.sqrt(n_simulations) for s, occ in state_occ.items()},
            policy=self,
            mdp=mdp,
            n_simulations=n_simulations
        )
    
    @classmethod
    def from_matrix(cls, states, actions, policy_matrix):
        policy = super(SparseTabularPolicy, cls).from_matrix(states, actions, policy_matrix)
        return SparseTabularPolicy(policy)
    
    @classmethod
    def from_q_matrix(cls, states, actions, q, inverse_temperature=float('inf')):
        policy = super(SparseTabularPolicy, cls).from_q_matrix(states, actions, q, inverse_temperature)
        return SparseTabularPolicy(policy)