import time
from types import SimpleNamespace
import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
import scipy.sparse as sparse
from scipy.sparse.linalg import spsolve
from msdm.core.algorithmclasses import Plans, PlanningResult

from vgc_project.sparse.sparse_tabularmdp import SparseTabularMDP
from vgc_project.sparse.sparse_policy import SparseTabularPolicy

class Solver(Plans):
    def update_result_object(self, res, mdp):
        res.mdp = mdp
        res._valuevec = res.state_value_vec
        res._qvaluemat = res.state_action_value_matrix
        policy = SparseTabularPolicy.from_q_matrix(mdp.state_list, mdp.action_list, res.state_action_value_matrix)
        res.policy = res.pi = policy
        vf = dict(zip(mdp.state_list, res.state_value_vec))
        res.state_value_dict = res.valuefunc = res.V = vf
        q = {}
        for si, s in enumerate(mdp.state_list):
            q[s] = {}
            for ai, a in enumerate(mdp.action_list):
                q[s][a] = res.state_action_value_matrix[si, ai]
        res.actionvaluefunc = res.Q = q
        res.initial_value = sum([res.V[s0]*p for s0, p in mdp.initial_state_dist().items()])
        return res
    
def sparse_value_iteration(
    transition_matrix,
    state_action_reward_matrix,
    n_states,
    n_actions,
    discount_rate,
    max_iterations,
    convergence_diff
):
    v = csr_matrix((n_states, 1), dtype=transition_matrix.dtype)
    for i in range(max_iterations):
        q = state_action_reward_matrix + \
            (discount_rate*transition_matrix*v).reshape(n_states, n_actions)
        nv = q.max(-1)
        diff = np.abs(v - nv)
        if np.max(diff) < convergence_diff:
            break
        v = csr_matrix(nv)
    return SimpleNamespace(
        state_value_vec=np.array(v.toarray()).flatten(),
        iterations=i,
        state_action_value_matrix=np.array(q.toarray()),
        converged=(i < max_iterations - 1),
        max_bellman_error=np.max(diff)
    )
    
class SparseValueIteration(Solver):
    def __init__(
        self,
        iterations=int(1e20),
        convergence_diff=1e-8
    ):
        self.iterations = iterations
        self.convergence_diff = convergence_diff
    
    def plan_on(self, mdp: SparseTabularMDP):
        sa_rf = mdp.state_action_reward_matrix
        sa_rf += np.log(mdp.action_matrix)
        sa_rf = csr_matrix(sa_rf)
        res = sparse_value_iteration(
            transition_matrix=mdp.transition_matrix,
            state_action_reward_matrix=sa_rf,
            n_states=len(mdp.state_list),
            n_actions=len(mdp.action_list),
            discount_rate=mdp.discount_rate,
            max_iterations=self.iterations,
            convergence_diff=self.convergence_diff
        )
        return self.update_result_object(res, mdp)

class SuccessfulResult(SimpleNamespace): pass
class ErrorResult(SimpleNamespace): pass
    
def sparse_policy_iteration(
    transition_matrix,
    state_action_reward_matrix,
    n_states,
    n_actions,
    discount_rate,
    max_iterations,
    value_decimals,
    initial_pi=None
):
    sa_idx = np.arange(n_states*n_actions).reshape(n_states, n_actions)
    pi_sel_mat = np.zeros(n_states*n_actions)
    ss_eye = sparse.eye(n_states)
    nss_range = np.arange(n_states)
    sa_rf_flat = state_action_reward_matrix.reshape(n_states*n_actions, 1).tocsr()
    if initial_pi is not None:
        pi = initial_pi
    else:
        pi = np.random.randint(0, n_actions, size=n_states)
    
    start_time = time.time()
    for i in range(max_iterations):
        pi_sa_idx = sa_idx[nss_range, pi]
        mp = transition_matrix[pi_sa_idx, :]
        s_rf = sa_rf_flat[pi_sa_idx, :]
        v = spsolve(ss_eye - discount_rate*mp, s_rf)
        if np.isnan(v).any():
            raise ValueError("Error solving for values - discount*transition_matrix might be singular")
        v = csr_matrix(v).transpose()
        q = state_action_reward_matrix + \
            (discount_rate*transition_matrix*v).reshape(n_states, n_actions)
        q = np.round(q, decimals=value_decimals)
        new_pi = np.array(q.argmax(-1)).flatten()
        old_pi = pi
        if (new_pi == pi).all():
            break
        pi = new_pi
        
    return SuccessfulResult(
        state_value_vec=np.array(v.toarray()).flatten(),
        iterations=i,
        state_action_value_matrix=np.array(q.toarray()),
        converged=(i < max_iterations - 1),
        run_time=time.time() - start_time
    )
    
class SparsePolicyIteration(Solver):
    def __init__(
        self,
        iterations=int(1e20),
        value_decimals=10,
        initial_policy=None
    ):
        self.iterations = iterations
        self.value_decimals = value_decimals
        self.initial_policy = initial_policy
    
    def plan_on(self, mdp: SparseTabularMDP):
        sa_rf = mdp.state_action_reward_matrix
        sa_rf += np.log(mdp.action_matrix)
        sa_rf = csr_matrix(sa_rf)
        res = sparse_policy_iteration(
            transition_matrix=mdp.transition_matrix,
            state_action_reward_matrix=sa_rf,
            n_states=len(mdp.state_list),
            n_actions=len(mdp.action_list),
            discount_rate=mdp.discount_rate,
            max_iterations=self.iterations,
            value_decimals=self.value_decimals,
            initial_pi=self.initial_policy
        )
        if isinstance(res, ErrorResult):
            return res
        return self.update_result_object(res, mdp)