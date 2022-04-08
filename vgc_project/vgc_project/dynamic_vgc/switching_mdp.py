from collections import namedtuple, defaultdict
from types import SimpleNamespace
from functools import lru_cache
from itertools import combinations, product
import scipy.sparse as sparse
import numpy as np 
from frozendict import frozendict

from msdm.core.problemclasses.mdp import TabularMarkovDecisionProcess, TabularPolicy
from msdm.algorithms import PolicyIteration, ValueIteration
from msdm.core.distributions import DictDistribution
from msdm.core.utils.funcutils import method_cache, cached_property

from vgc_project.dynamic_vgc import \
    create_maze, solve_maze, evaluate_construal,\
    powerset, softmax_epsilon_policy_matrix
from vgc_project.sparse import SparsePolicyIteration, SparseTabularMDP, SparseValueIteration

ConstrualState = namedtuple("ConstrualState", "construal ground_state")

class ConstrualSwitchingMDPBase(TabularMarkovDecisionProcess):
    def __init__(
        self,
        construals, 
        initial_construal,
        eval_ground_mdp_params,
        policy_ground_mdp_params,
        ground_policy_inv_temp,
        ground_policy_rand_choose,
        added_obs_cost,
        removed_obs_cost,
        continuing_obs_cost,
        construal_switch_cost,
        discount_rate,
    ):
        """
        
        eval_ground_mdp_params :
           Ground MDP parameters for *evaluating* (e.g., rewards) 
        policy_ground_mdp_params :
            Ground MDP parameters for *policy* construction
        added_obs_cost : 
            Cost multiplier per new obstacle
        removed_obs_cost :
            Cost multiplier per removed obstacle
        continuing_obs_cost :
            Cost multiplier per continuing obstacle
        construal_switch_cost :
            Cost multiplier for changing construal at all
        """
        self.construals = tuple(construals)
        self.initial_construal = initial_construal
        self.eval_ground_mdp_params = eval_ground_mdp_params
        self.policy_ground_mdp_params = policy_ground_mdp_params
        self.ground_policy_inv_temp = ground_policy_inv_temp
        self.ground_policy_rand_choose = ground_policy_rand_choose
        self.added_obs_cost = added_obs_cost
        self.removed_obs_cost = removed_obs_cost
        self.continuing_obs_cost = continuing_obs_cost
        self.construal_switch_cost = construal_switch_cost
        self.discount_rate = discount_rate
        
    def next_state_dist(self, s, a):
        if self.is_terminal(s):
            return DictDistribution({})
        next_construal = a
        adist = self.ground_policies[next_construal].action_dist(s.ground_state)
        nsdist = defaultdict(float)
        for ground_a, aprob in adist.items():
            for ground_ns, nsprob in self.ground_mdp.next_state_dist(s.ground_state, ground_a).items():
                nsdist[ground_ns] += aprob*nsprob
        assert np.isclose(sum(nsdist.values()), 1.0)
        return DictDistribution({ConstrualState(next_construal, ns): p for ns, p in nsdist.items()})
    
    def reward(self, s, a, ns):
        if self.is_terminal(s):
            return 0.
        
        # calculate expected ground reward
        # R(s, \pi) = \sum_a \sum_s' \pi(a | s) P(s' | s, a) R(s, a, s')
        ground_pi = self.ground_policies[a]
        ground_reward = 0
        for ground_action, aprob in ground_pi.action_dist(s.ground_state).items():
            for ground_ns, nsprob in self.ground_mdp.next_state_dist(s.ground_state, ground_action).items():
                ground_reward += self.ground_mdp.reward(s.ground_state, ground_action, ground_ns)*aprob*nsprob
        
        # calculate switching reward
        switch_reward = self.switch_reward(s.construal, ns.construal)
        return ground_reward + switch_reward
    
    @cached_property
    def ground_policies(self):
        policies = {}
        for c in self.construals:
            cgw_params = {**self.policy_ground_mdp_params, 'wall_features':"#"+c}
            cplan_res = solve_maze(cgw_params, planning_alg="policy_iteration")
            cplan = softmax_epsilon_policy_matrix(
                cplan_res._qvaluemat,
                self.ground_policy_inv_temp,
                self.ground_policy_rand_choose
            )
            cplan = TabularPolicy.from_matrix(
                self.ground_mdp.state_list,
                self.ground_mdp.action_list,
                cplan
            )
            policies[c] = cplan
        return policies
    
    def switch_reward(self, c, nc):
        added_obs = len(set(nc) - set(c))
        removed_obs = len(set(c) - set(nc))
        continuing_obs = len(set(c) & set(nc))
        construal_changed = c != nc
        switch_cost = \
            added_obs*self.added_obs_cost + \
            removed_obs*self.removed_obs_cost + \
            continuing_obs*self.continuing_obs_cost + \
            construal_changed*self.construal_switch_cost
        return -switch_cost
    
    def actions(self, s):
        return self.construals
    
    def initial_state_dist(self):
        return self.ground_mdp.initial_state_dist().marginalize(
            lambda e: ConstrualState(self.initial_construal, e)
        )
    
    def is_terminal(self, s):
        return self.ground_mdp.is_terminal(s.ground_state)
    
    @cached_property
    def construal_index(self):
        return self.action_index
    
    @cached_property
    def state_list(self):
        return tuple([ConstrualState(c, s) for c, s in product(self.construals, self.ground_mdp.state_list)])
    
    @cached_property
    def ground_mdp(self):
        return create_maze(self.eval_ground_mdp_params)
        
    @cached_property
    def action_list(self):
        return self.construals
    
    
class ConstrualSwitchingMDP(ConstrualSwitchingMDPBase, SparseTabularMDP):
    """
    This overwrites matrix creation methods of the base switching MDP
    with ones that return more efficient *sparse* versions.
    """
    def _compare_to_base_implementations(self):
        """
        Compares sparse transition matrix and state/action reward matrices
        to base implementations.
        """
        for si, s in enumerate(self.state_list):
            for ci, c in enumerate(self.actions(s)):
                sc_reward = 0
                for ns, prob in super().next_state_dist(s, c).items():
                    nsi = self.state_index[ns]
                    sci = si*len(self.action_list) + ci
                    assert np.isclose(self.transition_matrix[sci, nsi], prob)
                    sc_reward += prob*super().reward(s, c, ns)
                assert np.isclose(self.state_action_reward_matrix[si, ci], sc_reward)
    
    @cached_property
    def transition_matrix(self):
        # components
        gtf_san_dense = self.ground_mdp.transition_matrix.copy()
        terminal_states = ~self.ground_mdp.nonterminal_state_vec.astype(bool)
        gtf_san_dense[terminal_states, :, :] = 0.
        gpi_xsa_dense = self.ground_policy_matrix
        ncc, nss, naa = gpi_xsa_dense.shape
        stf_xd_dense = np.eye(ncc)

        # combine ground transitions with ground policies via cross-product and reduction
        gpi_sa_x = sparse.csr_matrix(gpi_xsa_dense.transpose(1, 2, 0).reshape(-1, ncc))
        gtf_sa_n = sparse.csr_matrix(gtf_san_dense.reshape(-1, nss))
        tf_sasa_xn = sparse.kron(gpi_sa_x, gtf_sa_n, format='csr')
        sa_eye = np.eye(nss*naa, dtype=bool).flatten()
        tf_sa_xn = tf_sasa_xn[sa_eye, :]

        # marginalize out ground actions
        tf_xns_a = tf_sa_xn.transpose().reshape(-1, naa)
        tf_xns_ = tf_xns_a*sparse.csr_matrix(np.ones((naa, 1)))

        # join with switching dynamics
        tf_x_ns = tf_xns_.reshape(ncc, -1)
        stf_x_d = sparse.csr_matrix(stf_xd_dense)
        tf_xx_dns = sparse.kron(stf_x_d, tf_x_ns, format='csr')
        x_eye = np.eye(ncc, dtype=bool).flatten()
        tf_x_dns = tf_xx_dns[x_eye, :]

        # join initial construal state
        tf_sx_dn = tf_x_dns.reshape(-1, nss).transpose().reshape(nss*ncc, ncc*nss)
        stf_c_ = sparse.csr_matrix(np.ones((ncc, 1)))
        tf_csx_dn = sparse.kron(stf_c_, tf_sx_dn, format='csr')
        return tf_csx_dn
    
    @property
    def reward_matrix(self):
        raise NotImplementedError("This should only use a sparse state-action reward `self.state_action_reward_matrix`")
    
    @cached_property
    def state_action_reward_matrix(self):
        rf_san = self.ground_mdp.reward_matrix*self.ground_mdp.transition_matrix
        sxa_ground_pis = self.ground_policy_matrix.transpose(1, 0, 2)
        rf_sx = np.einsum("san,xsa->sx", rf_san, self.ground_policy_matrix)
        rf_csx = rf_sx[None, :, :] + self.switch_reward_matrix[:, None, :]
        rf_csx = np.einsum("csx,s->csx", rf_csx, self.ground_mdp.nonterminal_state_vec)
        return rf_csx.reshape(-1, len(self.construals))
    
    @cached_property
    def switch_reward_matrix(self):
        construal_switch_rewards = np.zeros((len(self.construals), len(self.construals)))
        for (ci, c), (nci, nc) in product(enumerate(self.construals), repeat=2):
            construal_switch_rewards[ci, nci] = self.switch_reward(c, nc)
        return construal_switch_rewards
    
    @cached_property
    def ground_policy_matrix(self):
        ground_pis = []
        for c in self.construals:
            cgw_params = {**self.policy_ground_mdp_params, 'wall_features':"#"+c}
            cplan_res = solve_maze(cgw_params, planning_alg="policy_iteration")
            cplan = softmax_epsilon_policy_matrix(
                cplan_res._qvaluemat,
                self.ground_policy_inv_temp,
                self.ground_policy_rand_choose
            )
            ground_pis.append(cplan)
        ground_pis = np.stack(ground_pis)
        return ground_pis
