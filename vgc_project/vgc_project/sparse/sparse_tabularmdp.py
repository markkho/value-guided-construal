import numpy as np
from msdm.core.problemclasses.mdp import TabularMarkovDecisionProcess
from msdm.core.utils.funcutils import method_cache, cached_property
from scipy.sparse import lil_matrix, csr_matrix, dok_matrix

class SparseTabularMDP(TabularMarkovDecisionProcess):
    """
    Uses sparse matrices for transition and reward functions
    """
    @cached_property
    def transition_matrix(self) -> np.array:
        ss = self.state_list
        ssi = self.state_index
        aa = self.action_list
        aai = self.action_index
        tf = dok_matrix((len(ss)*len(aa), len(ss)), dtype=float)
        for s, si in ssi.items():
            for a in self._cached_actions(s):
                sai = si*len(aa) + aai[a]
                for ns, nsp in self._cached_next_state_dist(s, a).items():
                    if self.is_terminal(s):
                        assert nsp == 0., "Terminal states have zero outgoing probabilities"
                    tf[sai, ssi[ns]] = nsp
        return csr_matrix(tf)

    @cached_property
    def reward_matrix(self):
        ss = self.state_list
        ssi = self.state_index
        aa = self.action_list
        aai = self.action_index
        rf = dok_matrix((len(ss)*len(aa), len(ss)), dtype=float)
        for s, si in ssi.items():
            for a in self._cached_actions(s):
                sai = si*len(aa) + aai[a]
                for ns, p in self._cached_next_state_dist(s, a).items():
                    if p == 0.:
                        continue
                    rf[sai, ssi[ns]] = self.reward(s, a, ns)
        return csr_matrix(rf)

    @cached_property
    def state_action_reward_matrix(self):
        rf = self.reward_matrix
        tf = self.transition_matrix
        return np.sum(rf.multiply(tf), -1).reshape(len(self.state_list), len(self.action_list))