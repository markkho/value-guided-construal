import numpy as np 
import random
from functools import lru_cache
from frozendict import frozendict
from types import SimpleNamespace

from msdm.algorithms import PolicyIteration, ValueIteration
from msdm.core.problemclasses.mdp import TabularPolicy

from vgc_project.sparse import SparsePolicyIteration, SparseTabularPolicy
from vgc_project.dynamic_vgc import ConstrualSwitchingMDP
from vgc_project.maze import Maze, Location
from vgc_project.dynamic_vgc import powerset, softmax_epsilon_policy_matrix, solve_maze
from collections import defaultdict


def softmax_epsilon_policy(mdp, qvalue_matrix, inv_temp, rand_choose):
    policy_mat = softmax_epsilon_policy_matrix(qvalue_matrix, inv_temp, rand_choose)
    return SparseTabularPolicy.from_matrix(mdp.state_list, mdp.action_list, policy_mat)

@lru_cache()
def make_construal_switching_mdp(switching_mdp_params):
    cs_mdp = ConstrualSwitchingMDP(**switching_mdp_params)
    return cs_mdp

@lru_cache()
def solve_construal_switching_mdp(switching_mdp_params):
    max_iterations = 200
    cs_mdp = make_construal_switching_mdp(switching_mdp_params)
    cs_mdp_res = SparsePolicyIteration(iterations=max_iterations).plan_on(cs_mdp)
    return cs_mdp_res

def policy_evaluation_stats(policy_eval):
    # Calculates:
    # obstacle awareness count: occ(obs) = sum_c occ(obs, c)*1[obs \in c]
    # obstacle awareness probability: p(obs) = sum_c p(obs, c)*1[obs \in c]
    # obstacle, location count: sum_c occ(obs, loc, c)*1[obs \in c]
    # obstacle, location prob: p(obs, loc) = sum_c p(obs, loc, c)*1[obs \in c]
    # location prob
    # obstacle given location prob: p(obs | loc) = p(obs, loc) / p(loc)
    obs_occ = defaultdict(float)
    obs_prob = defaultdict(float)
    obs_loc_occ = defaultdict(lambda : defaultdict(float))
    obs_loc_prob = defaultdict(lambda : defaultdict(float))
    loc_prob = defaultdict(float)
    loc_occ = defaultdict(float)
    total_occ = sum(policy_eval.occupancy.values())
    for o in list("0123456789"):
        for s, occ in policy_eval.occupancy.items():
            if occ == 0:
                continue
            if o in s.construal:
                obs_occ[o] += occ
                obs_prob[o] += occ/total_occ
                loc = Location(s.ground_state.x, s.ground_state.y)
                obs_loc_occ[o][loc] += occ
                obs_loc_prob[o][loc] += occ/total_occ
    for s, occ in policy_eval.occupancy.items():
        loc = Location(s.ground_state.x, s.ground_state.y)
        loc_prob[loc] += occ/total_occ
        loc_occ[loc] += occ
            
    # calculate the probability of attending to an obstacle given you are in a location
    # P(o | l) = P(o, l) / p(l)
    obs_prob_per_loc = defaultdict(lambda : defaultdict(float))
    for o in obs_loc_prob.keys():
        for loc in obs_loc_prob[o].keys():
            obs_prob_per_loc[o][loc] = obs_loc_prob[o][loc]/loc_prob[loc]
    
    return dict(
        obs_occ=dict(obs_occ),
        obs_prob=dict(obs_prob),
        obs_loc_occ=dict(obs_loc_occ),
        obs_loc_prob=dict(obs_loc_prob),
        loc_occ=dict(loc_occ),
        loc_prob=dict(loc_prob),
        obs_prob_per_loc=dict(obs_prob_per_loc),
        total_occ=total_occ
    )

def evaluate_sparse_policy_matrix(policy_mat, mdp, n_simulations, max_sim_length):
    n_states, n_actions = policy_mat.shape
    terminal_states = (mdp.nonterminal_state_vec == 0)

    @lru_cache(maxsize=int(1e5))
    def next_state_probs(sa_i):
        ns_probs = mdp.transition_matrix[sa_i, :].A.flatten()
        return ns_probs

    def run_simulation():
        state_traj = []
        reward_traj = []
        s_i = np.random.choice(n_states, p=mdp.initial_state_vec)
        for timestep in range(max_sim_length):

            a_i = np.random.choice(n_actions, p=policy_mat[s_i])
            sa_i = s_i*n_actions + a_i #need to get state/action index
            r = mdp.state_action_reward_matrix[s_i, a_i]

            state_traj.append(mdp.state_list[s_i])
            reward_traj.append(r)

            ns_i = np.random.choice(n_states, p=next_state_probs(sa_i))
            if terminal_states[ns_i]:
                break
            s_i = ns_i
        if timestep == max_sim_length - 1:
            raise ValueError("Maximum simulation length reached")
        return state_traj, reward_traj

    state_occ = {s: [] for s in mdp.state_list}
    initial_value = []
    for sim_i in np.arange(n_simulations):
        state_traj, reward_traj = run_simulation()
        for s in state_occ.keys():
            state_occ[s].append(0)
        for s in state_traj:
            state_occ[s][-1] += 1
        discounted_return = 0
        discount = 1.0
        for r in reward_traj:
            discounted_return += r*discount
            discount *= mdp.discount_rate
        initial_value.append(discounted_return)

    return SimpleNamespace(
        initial_value=np.mean(initial_value),
        initial_value_sem=np.std(initial_value)/np.sqrt(n_simulations),
        occupancy={s: np.mean(occ) for s, occ in state_occ.items()},
        occupancy_sem={s: np.std(occ)/np.sqrt(n_simulations) for s, occ in state_occ.items()},
        mdp=mdp,
        n_simulations=n_simulations
    )

from joblib import Memory
import functools

joblib_mem = Memory("./_cache", verbose=0)

@functools.lru_cache(maxsize=int(1e3))
@joblib_mem.cache()
def dynamic_vgc(
    tile_array,
    ground_policy_inv_temp=None,
    ground_policy_rand_choose=0.,
    ground_discount_rate=1.0-1e-5,
    action_deviation_reward=0,
    wall_bias=0.,
    wall_bump_cost=0.,
    added_obs_cost=1,
    removed_obs_cost=0,
    continuing_obs_cost=0,
    construal_switch_cost=0,
    switching_inv_temp=5,
    switching_rand_choose=0.,
    switching_discount_rate=1-1e-5,
    max_construal_size=3,
    n_simulations=1000,
    seed=None
):
    assert seed is not None, "`seed` cannot be none (bc of caching)"

    rng = random.Random(seed)
    np.random.seed(seed)
    true_mdp_params = dict(
        tile_array=tile_array,
        feature_rewards=(("G", 0), ),
        absorbing_features=("G",),
        wall_features="#0123456789",
        default_features=(".",),
        initial_features=("S",),
        step_cost=-1,
        discount_rate=ground_discount_rate,
        success_prob=1-1e-5,
        wall_bias=wall_bias,
        wall_bump_cost=wall_bump_cost
    )
    if action_deviation_reward != 0:
        true_mdp_params['action_deviation_reward'] = action_deviation_reward

    obstacles = set(''.join(tile_array)) & set("0123456789")
    construals = tuple([''.join(sorted(c)) for c in powerset(obstacles, maxsize=max_construal_size)])

    switching_mdp_params = frozendict(
        construals=construals, 
        initial_construal="",
        eval_ground_mdp_params=frozendict(true_mdp_params),
        policy_ground_mdp_params=frozendict(true_mdp_params),
        ground_policy_inv_temp=ground_policy_inv_temp,
        ground_policy_rand_choose=ground_policy_rand_choose,
        added_obs_cost=added_obs_cost,
        removed_obs_cost=removed_obs_cost,
        continuing_obs_cost=continuing_obs_cost,
        construal_switch_cost=construal_switch_cost,
        discount_rate=switching_discount_rate,
    )
    res = solve_construal_switching_mdp(switching_mdp_params)
    switching_mdp = make_construal_switching_mdp(switching_mdp_params)
    switch_mdp_properties = dict(
        transition_matrix_entries = switching_mdp.transition_matrix.size,
        n_states = len(switching_mdp.state_list),
        n_actions = len(switching_mdp.action_list),
    )
    switch_policy_mat = softmax_epsilon_policy_matrix(
        res._qvaluemat,
        inv_temp=switching_inv_temp,
        rand_choose=switching_rand_choose
    )
    pi_eval = evaluate_sparse_policy_matrix(
        policy_mat=switch_policy_mat,
        mdp=switching_mdp,
        n_simulations=n_simulations,
        max_sim_length=10000
    )
    # for debugging purposes
    # switch_policy = TabularPolicy.from_matrix(
    #     switching_mdp.state_list,
    #     switching_mdp.action_list, 
    #     switch_policy_mat
    # )

    eval_stats = policy_evaluation_stats(pi_eval)

    eval_stats['initial_value'] = pi_eval.initial_value
    eval_stats['initial_value_sem'] = pi_eval.initial_value_sem
    eval_stats['switching_mdp_solver_converged'] = res.converged

    # calculate optimality gap
    no_aux_costs_true_mdp_params = {**true_mdp_params}
    no_aux_costs_true_mdp_params['wall_bias'] = 0
    if 'action_deviation_reward' in no_aux_costs_true_mdp_params:
        no_aux_costs_true_mdp_params['action_deviation_reward'] = 0
    switching_no_costs_mdp = make_construal_switching_mdp(frozendict({
        **switching_mdp_params,
        **dict(
            added_obs_cost=0,
            removed_obs_cost=0,
            continuing_obs_cost=0,
            construal_switch_cost=0
        ),
        'eval_ground_mdp_params': frozendict(no_aux_costs_true_mdp_params),
        'policy_ground_mdp_params': frozendict(true_mdp_params),
    }))
    no_cost_pi_eval = evaluate_sparse_policy_matrix(
        policy_mat=switch_policy_mat,
        mdp=switching_no_costs_mdp,
        n_simulations=n_simulations,
        max_sim_length=10000
    )
    no_aux_cost_ground_mdp = solve_maze(frozendict(no_aux_costs_true_mdp_params))
    eval_stats['no_aux_cost_ground_initial_value'] = no_aux_cost_ground_mdp.initial_value
    eval_stats['no_aux_cost_switch_mdp_initial_value'] = no_cost_pi_eval.initial_value
    behavioral_utility_gap = no_cost_pi_eval.initial_value - no_aux_cost_ground_mdp.initial_value
    eval_stats['behavioral_utility_gap'] = behavioral_utility_gap
    eval_stats['true_mdp_params'] = true_mdp_params
    eval_stats['switch_mdp_params'] = {
        **switching_mdp_params,
        'ground_mdp_params': true_mdp_params
    }
    eval_stats['switch_mdp_properties'] = switch_mdp_properties
    eval_stats['obstacles'] = obstacles

    return eval_stats
