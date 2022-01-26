import pandas as pd
import numpy as np
import seaborn as sns
from vgc_project import utils, gridutils
from msdm.domains import GridWorld
from vgc_project.modelinterface import create_modeling_interface

import json
from functools import lru_cache
from itertools import combinations, product
import warnings
from tqdm import tqdm
sem = lambda c: np.std(c)/np.sqrt(np.sum(c != np.nan))
import matplotlib.pyplot as plt
import sys
import logging
logger = logging.getLogger()
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.WARNING)

import os
DATA_DIRECTORY = "../experiments"

# ========= #
# Utilities #
# ========= #
@lru_cache()
def make_gridworld(tile_array):
    gw = GridWorld(
        tile_array,
        initial_features="S",
        absorbing_features="G",
        wall_features="#0123456789",
        step_cost=-1
    )
    def plot(*args, **kwargs):
        kwargs = {
            "featurecolors": {
                "#": 'k',
                "G": "green",
                **{k: 'mediumblue' for k in "0123456789"}
            },
            "plot_walls": False,
            **kwargs
        }
        return GridWorld.plot(gw, *args, **kwargs)
    gw.plot = plot
    return gw

def calc_nav_mindist(navtrial):
    flocs = make_gridworld(mazes[navtrial['grid']]).feature_locations
    dists = {}
    for obs, locs in flocs.items():
        if obs not in "0123456789":
            continue
        locs = [(l['x'], l['y']) for l in locs]
        dist = gridutils.min_dist(navtrial['state_traj'], locs)
        dists[f"obs-{obs}"] = dist['mindist']
    return pd.Series(dists)

def calc_nav_mindist_timestep(navtrial):
    flocs = make_gridworld(mazes[navtrial['grid']]).feature_locations
    steps = {}
    for obs, locs in flocs.items():
        if obs not in "0123456789":
            continue
        locs = [(l['x'], l['y']) for l in locs]
        dist = gridutils.min_dist(navtrial['state_traj'], locs, sourcename='traj')
        mindist_loc = (dist['mintrajloc.x'], dist['mintrajloc.y'])
        mindist_step = max(i for i, loc in enumerate(navtrial['state_traj']) if tuple(loc) == mindist_loc)
        steps[f"obs-{obs}"] = mindist_step
    return pd.Series(steps)

# ================= #
# Model Predictions #
# ================= #
mazes_0_11 = json.load(open(os.path.join(DATA_DIRECTORY, "mazes/mazes_0-11.json"), 'r'))
mazes_12_15 = json.load(open(os.path.join(DATA_DIRECTORY, "mazes/mazes_12-15.json"), 'r'))
mazes = {
    **{"-".join(k.split('-')[:-1]): tuple(v) for k,v in mazes_0_11.items()},
    **{k: tuple(v) for k,v in mazes_12_15.items()}
}

mods = create_modeling_interface(joblib_cache_location="./_analysiscache")
model_preds = []
for grid, tile_array in mazes.items():
    for obs in sorted(set("0123456789") & set.union(*[set(r) for r in tile_array])):
        preds = {
            "grid": grid,
            "obstacle": f"obs-{obs}",
            **mods.predictions(tile_array, obs, seed=72193880),
        }
        model_preds.append(preds)
model_preds = pd.DataFrame(model_preds)

to_zscore = [
    'vgc_weight',
    'log_traj_based_hitcount',
    'graph_based_hitcount',
    'goal_dist',
    'start_dist',
    'optpolicy_dist',
    'walls_dist',
    'center_dist',
    'bottleneck_dist',
    'sr_occ'
]
for col in to_zscore:
    model_preds[col+"_Z"] = utils.zscore(model_preds[col])

# ================= #
# Experiment 1 Data #
# ================= #
@lru_cache()
def get_exp1_nt():
    def parse_exp1_navtrial(t):
        t = t.sort_values('trialnum')
        return pd.Series({
            'state_traj': list(t['state']),
            'initial_rt': t['rt'].iloc[0],
            'total_rt': t['rt'].sum()
        })
    exp1_nt = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp1/data/navtrials.json"), 'r')))
    exp1_nt = exp1_nt.groupby(['sessionId', 'round', 'grid', 'trans'])\
        .apply(parse_exp1_navtrial).reset_index()
    exp1_nt['grid'] = exp1_nt['grid'].apply(lambda gi: f"grid-{gi}")
    return exp1_nt

@lru_cache()
def get_exp1_navdist():
    exp1_nt = get_exp1_nt()
    exp1_navdist = pd.concat([
        exp1_nt[['sessionId', 'round', 'grid']],
        exp1_nt.apply(calc_nav_mindist, axis=1)
    ], axis=1).melt(id_vars=['sessionId', 'round', 'grid'], var_name="obstacle", value_name="nav_mindist")
    return exp1_navdist

@lru_cache()
def get_exp1_navdist_timestep():
    exp1_nt = get_exp1_nt()
    exp1_navdist_timestep = pd.concat([
        exp1_nt[['sessionId', 'round', 'grid']],
        exp1_nt.apply(calc_nav_mindist_timestep, axis=1)
    ], axis=1).melt(id_vars=['sessionId', 'round', 'grid'], var_name="obstacle", value_name="nav_mindist_timestep")
    return exp1_navdist_timestep

@lru_cache()
def get_exp1_at():
    print("Loading Experiment 1 Attention Trials")
    exp1_at = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp1/data/attentiontrials.json"), 'r')))
    exp1_at = exp1_at[['sessionId', 'round', 'grid', 'trans', 'probeobs', 'queryround', 'attention', 'rt']]\
        .rename(columns={"probeobs": "obstacle", "queryround": "proberound"})
    exp1_at['grid'] = exp1_at['grid'].apply(lambda gi: f"grid-{gi}")
    exp1_at['obstacle'] = exp1_at['obstacle'].apply(lambda oi: f"obs-{oi}")
    exp1_at['attention_N'] = utils.normalize(exp1_at['attention'], minval=-4, maxval=4)
    exp1_navdist = get_exp1_navdist()
    exp1_navdist_timestep = get_exp1_navdist_timestep()
    exp1_at = exp1_at.\
        merge(exp1_navdist, on=['sessionId', 'round', 'grid', 'obstacle']).\
        merge(exp1_navdist_timestep, on=['sessionId', 'round', 'grid', 'obstacle'])
    exp1_at['nav_mindist_Z'] = utils.zscore(exp1_at['nav_mindist'])
    exp1_at['nav_mindist_timestep_Z'] = utils.zscore(exp1_at['nav_mindist_timestep'])
    exp1_at = exp1_at.merge(model_preds)

    #check that each column of data is unique
    for c1, c2 in product(exp1_at.columns, repeat=2):
        if c1 != c2:
            assert not all(exp1_at[c1] == exp1_at[c2])
    return exp1_at
    

# ================= #
# Experiment 2 Data #
# ================= #
@lru_cache()
def get_exp2_at():
    exp2_at = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp2/data/attentiontrials.json"), 'r')))
    exp2_at['earlyterm'] = exp2_at.navgridname.apply(lambda g: g.split('-')[-1])
    exp2_at = exp2_at[['sessionId', 'round', 'grid', 'trans', 'earlyterm', 'probeobs', 'queryround', 'attention', 'rt']]\
        .rename(columns={"probeobs": "obstacle", "queryround": "proberound"})
    exp2_at['grid'] = exp2_at['grid'].apply(lambda gi: f"grid-{gi}")
    exp2_at['obstacle'] = exp2_at['obstacle'].apply(lambda oi: f"obs-{oi}")
    exp2_at['attention_N'] = utils.normalize(exp2_at['attention'], minval=-4, maxval=4)
    exp2_nt = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp2/data/navtrials.json"), 'r')))
    def parse_exp2_navtrial(t):
        t = t.sort_values('trialnum')
        return pd.Series({
            'state_traj': list(t['state']),
            'initial_rt': t['rt'].iloc[0],
            'total_rt': t['rt'].sum()
        })
    exp2_nt = exp2_nt.groupby(['sessionId', 'round', 'grid', 'trans'])\
        .apply(parse_exp2_navtrial).reset_index()
    exp2_nt['grid'] = exp2_nt['grid'].apply(lambda gi: f"grid-{gi}")
    exp2_navdist = pd.concat([
        exp2_nt[['sessionId', 'round']],
        exp2_nt.apply(calc_nav_mindist, axis=1)
    ], axis=1).melt(id_vars=['sessionId', 'round'], var_name="obstacle", value_name="nav_mindist")
    exp2_navdist_timestep = pd.concat([
        exp2_nt[['sessionId', 'round']],
        exp2_nt.apply(calc_nav_mindist_timestep, axis=1)
    ], axis=1).melt(id_vars=['sessionId', 'round'], var_name="obstacle", value_name="nav_mindist_timestep")
    exp2_at = exp2_at.\
        merge(exp2_navdist, on=['sessionId', 'round', 'obstacle']).\
        merge(exp2_navdist_timestep, on=['sessionId', 'round', 'obstacle'])
    exp2_at['nav_mindist_Z'] = utils.zscore(exp2_at['nav_mindist'])
    exp2_at['nav_mindist_timestep_Z'] = utils.zscore(exp2_at['nav_mindist_timestep'])
    exp2_at = exp2_at.merge(model_preds)
    return exp2_at
    

# ================= #
# Experiment 3 Data #
# ================= #

@lru_cache()
def get_exp3_at__exp3_mt():
    # load navigation trials
    exp3_nt = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp3/data/navtrials.json"), 'r')))
    def parse_exp3_navtrial(t):
        t = t.sort_values('trialnum')
        return pd.Series({
            'state_traj': list(t['state']),
            'initial_rt': t['rt'].iloc[0],
            'total_rt': t['rt'].sum()
        })
    exp3_nt = exp3_nt.groupby(['sessionId', 'round', 'grid', 'trans'])\
        .apply(parse_exp3_navtrial).reset_index()
    exp3_nt['grid'] = exp3_nt['grid'].apply(lambda gi: f"grid-{gi}")
    exp3_navdist = pd.concat([
        exp3_nt[['sessionId', 'round']],
        exp3_nt.apply(calc_nav_mindist, axis=1)
    ], axis=1).melt(id_vars=['sessionId', 'round'], var_name="obstacle", value_name="nav_mindist")
    exp3_navdist_timestep = pd.concat([
        exp3_nt[['sessionId', 'round']],
        exp3_nt.apply(calc_nav_mindist_timestep, axis=1)
    ], axis=1).melt(id_vars=['sessionId', 'round'], var_name="obstacle", value_name="nav_mindist_timestep")

    # awareness trials
    exp3_at = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp3/data/attentiontrials.json"), 'r')))
    exp3_at = exp3_at[['sessionId', 'round', 'grid', 'trans', 'probeobs', 'queryround', 'attention', 'rt']]\
        .rename(columns={"probeobs": "obstacle", "queryround": "proberound"})
    exp3_at['grid'] = exp3_at['grid'].apply(lambda gi: f"grid-{gi}")
    exp3_at['obstacle'] = exp3_at['obstacle'].apply(lambda oi: f"obs-{oi}")
    exp3_at['attention_N'] = utils.normalize(exp3_at['attention'], minval=-4, maxval=4)
    exp3_at = exp3_at.\
        merge(exp3_navdist, on=['sessionId', 'round', 'obstacle']).\
        merge(exp3_navdist_timestep, on=['sessionId', 'round', 'obstacle'])
    exp3_at['nav_mindist_Z'] = utils.zscore(exp3_at['nav_mindist'])
    exp3_at['nav_mindist_timestep_Z'] = utils.zscore(exp3_at['nav_mindist_timestep'])
    exp3_at = exp3_at.merge(model_preds)
    exp3_at['near'] = (exp3_at['optpolicy_dist'] <= exp3_at['optpolicy_dist'].median())
    exp3_at['relevant'] = exp3_at['vgc_weight'] >= .5
    exp3_at['critical'] = ~exp3_at['near'] & exp3_at['relevant']
    exp3_at['obs_type'] = exp3_at.apply(lambda r: 'irrel' if not r['relevant'] else 'crit' if r['critical'] else 'none', axis=1)

    # location recall trials
    exp3_mt = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp3/data/memorytrials.json"), 'r')))
    exp3_mt = exp3_mt[['sessionId', 'round', 'grid', 'trans', 'probeobs', 'queryround', 'correct', 'conf', 'rt_mem', 'rt_conf']]\
        .rename(columns={"probeobs": "obstacle", "queryround": "proberound"})
    exp3_mt['grid'] = exp3_mt['grid'].apply(lambda gi: f"grid-{gi}")
    exp3_mt['obstacle'] = exp3_mt['obstacle'].apply(lambda oi: f"obs-{oi}")
    exp3_mt['conf_N'] = utils.normalize(exp3_mt['conf'], minval=-4, maxval=4)
    exp3_mt = exp3_mt.\
        merge(exp3_navdist, on=['sessionId', 'round', 'obstacle']).\
        merge(exp3_navdist_timestep, on=['sessionId', 'round', 'obstacle'])
    exp3_mt['nav_mindist_Z'] = utils.zscore(exp3_mt['nav_mindist'])
    exp3_mt['nav_mindist_timestep_Z'] = utils.zscore(exp3_mt['nav_mindist_timestep'])
    exp3_mt = exp3_mt.merge(model_preds)
    exp3_mt['near'] = (exp3_mt['optpolicy_dist'] <= exp3_mt['optpolicy_dist'].median())
    exp3_mt['relevant'] = exp3_mt['vgc_weight'] >= .5
    exp3_mt['critical'] = ~exp3_mt['near'] & exp3_mt['relevant']
    exp3_mt['obs_type'] = exp3_mt.apply(lambda r: 'irrel' if not r['relevant'] else 'crit' if r['critical'] else 'none', axis=1)
    
    
    #sanity check
    n_unique_sid_at = len(exp3_at.sessionId.unique())
    n_unique_mean_rt_at = len(exp3_at.groupby('sessionId')['rt'].mean().unique())
    assert n_unique_sid_at == n_unique_mean_rt_at

    n_unique_sid_mt = len(exp3_mt.sessionId.unique())
    n_unique_mean_rt_mt = len(exp3_mt.groupby('sessionId')['rt_mem'].mean().unique())
    assert n_unique_sid_mt == n_unique_mean_rt_mt

    assert len(set(exp3_at.sessionId) & set(exp3_mt.sessionId)) == 0
    
    return exp3_at, exp3_mt

# ================== #
# Experiment 4a Data #
# ================== #
@lru_cache()
def get_exp4a_ht():
    exp4a_ht = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp4a/data/hovering-data-trials.json"), 'r')))
    exp4a_ht['obstacle'] = exp4a_ht['obstacle'].apply(lambda o: f"obs-{o}")
    exp4a_ht['grid'] = exp4a_ht['grid'].apply(lambda g: "-".join(g.split("-")[:-1]))
    exp4a_ht = exp4a_ht.merge(model_preds)
    
    # sanity checking
    n_sessionIds = len(exp4a_ht.sessionId.unique())
    n_mean_hoverdur = len(exp4a_ht.groupby('sessionId')['hoverduration'].mean().unique())
    assert n_sessionIds == n_mean_hoverdur
    
    return exp4a_ht

# ================== #
# Experiment 4b Data #
# ================== #
@lru_cache()
def get_exp4b_ht():
    exp4b_ht = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp4b/data/hovering-data-trials.json"), 'r')))
    exp4b_ht['obstacle'] = exp4b_ht['obstacle'].apply(lambda o: f"obs-{o}")
    exp4b_ht = exp4b_ht.merge(model_preds)
    
    # sanity checking
    n_sessionIds = len(exp4b_ht.sessionId.unique())
    n_mean_hoverdur = len(exp4b_ht.groupby('sessionId')['hoverduration'].mean().unique())
    assert n_sessionIds == n_mean_hoverdur
    
    return exp4b_ht

# ================== #
# Experiment 5a Data #
# ================== #
@lru_cache()
def get_exp5a_at():
    exp5a_st = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp5a/data/all-survey-trials.json"), 'r')))
    exp5a_at = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp5a/data/all-attention-trials.json"), 'r')))

    #apply exclusions
    exp5a_st = exp5a_st[~exp5a_st.exclude].reset_index(drop=True)
    exp5a_at = exp5a_at[exp5a_at.sessionId.isin(exp5a_st.sessionId)].reset_index(drop=True)
    exp5a_at = exp5a_at.rename(columns={"transform": "trans", "queryround": "proberound", "attn_resp": "attention"})
    exp5a_at = exp5a_at.rename(columns={"transform": "trans", "queryround": "proberound", "attn_resp_N": "attention_N"})

    # reformat attention
    temp = exp5a_at.attention
    temp = temp - 4
    temp[temp <= 0] = temp[temp <= 0] - 1
    exp5a_at.attention = temp
    exp5a_at = exp5a_at.drop('attention_N', axis=1)
    exp5a_at['attention_N'] = utils.normalize(exp5a_at['attention'])
    exp5a_at['obstacle'] = exp5a_at['obstacle'].apply(lambda o: f"obs-{o}")
    exp5a_at['grid'] = exp5a_at['grid'].apply(lambda g: "-".join(g.split('-')[:-1]))
    return exp5a_at

@lru_cache()
def get_exp2_5a_at():
    exp2_at = get_exp2_at()
    exp5a_at = get_exp5a_at()
    assert set(exp2_at['attention'].unique()) == set(exp5a_at['attention'].unique())
    assert set(exp2_at['obstacle'].unique()) == set(exp5a_at['obstacle'].unique())
    assert set(exp2_at['grid'].unique()) == set(exp5a_at['grid'].unique())

    # combine attn into a single dataframe
    exp2_5a_at = pd.concat([
        exp2_at[['sessionId', 'round', 'grid', 'trans', 'earlyterm', 'obstacle',
           'proberound', 'attention', 'rt', 'nav_mindist',
           'nav_mindist_timestep']].assign(exp="exp2"),
        exp5a_at[['sessionId', 'grid', 'trans', 'round', 'proberound',
                  'obstacle', 'rt', 'attention']].assign(exp="exp5a")
    ]).reset_index(drop=True)
    exp2_5a_at['attention_N'] = utils.normalize(exp2_5a_at['attention'])
    exp2_5a_at = exp2_5a_at.merge(model_preds)
    exp2_5a_at['neg_optpolicy_dist_Z'] = -exp2_5a_at['optpolicy_dist_Z']
    return exp2_5a_at

# ================= #
# Experiment 5b Data #
# ================= #
@lru_cache()
def get_exp5b_at__exp5b_mt():
    exp5b_st = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp5b/data/all-survey-trials.json"), 'r')))
    exp5b_at = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp5b/data/all-attention-trials.json"), 'r')))
    exp5b_mt = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp5b/data/all-memory-trials.json"), 'r')))

    #apply exclusions
    exp5b_st = exp5b_st[~exp5b_st.exclude].reset_index(drop=True)
    exp5b_at = exp5b_at[exp5b_at.sessionId.isin(exp5b_st.sessionId)].reset_index(drop=True)
    exp5b_at = exp5b_at.rename(columns={"transform": "trans", "queryround": "proberound", "attn_resp": "attention"})
    exp5b_at = exp5b_at.rename(columns={"transform": "trans", "queryround": "proberound", "attn_resp_N": "attention_N"})
    exp5b_mt = exp5b_mt[exp5b_mt.sessionId.isin(exp5b_st.sessionId)].reset_index(drop=True)
    exp5b_mt = exp5b_mt.rename(columns={"transform": "trans", "queryround": "proberound", "attn_resp": "attention"})
    exp5b_mt = exp5b_mt.rename(columns={"transform": "trans", "queryround": "proberound", "attn_resp_N": "attention_N"})

    # reformat attention
    temp = exp5b_at.attention
    temp = temp - 4
    temp[temp <= 0] = temp[temp <= 0] - 1
    exp5b_at.attention = temp
    exp5b_at = exp5b_at.drop('attention_N', axis=1)
    exp5b_at['attention_N'] = utils.normalize(exp5b_at['attention'])
    exp5b_at['obstacle'] = exp5b_at['obstacle'].apply(lambda o: f"obs-{o}")

    # reformat conf
    temp = exp5b_mt.conf
    temp = temp - 4
    temp[temp <= 0] = temp[temp <= 0] - 1
    exp5b_mt.conf = temp
    exp5b_mt['conf_N'] = utils.normalize(exp5b_mt['conf'])
    exp5b_mt['obstacle'] = exp5b_mt['obstacle'].apply(lambda o: f"obs-{o}")
    return exp5b_at, exp5b_mt

@lru_cache()
def get_exp3_5b_at__exp3_5b_mt():
    exp3_at, exp3_mt = get_exp3_at__exp3_mt()
    exp5b_at, exp5b_mt = get_exp5b_at__exp5b_mt()
    assert set(exp3_at['attention'].unique()) == set(exp5b_at['attention'].unique())
    assert set(exp3_at['obstacle'].unique()) == set(exp5b_at['obstacle'].unique())
    assert set(exp3_at['grid'].unique()) == set(exp5b_at['grid'].unique())
    assert set(exp3_mt['conf'].unique()) == set(exp5b_mt['conf'].unique())
    assert set(exp3_mt['obstacle'].unique()) == set(exp5b_mt['obstacle'].unique())
    assert set(exp3_mt['grid'].unique()) == set(exp5b_mt['grid'].unique())

    # combine attn into a single dataframe
    exp3_5b_at = pd.concat([
        exp3_at[['sessionId', 'round', 'grid', 'trans', 'obstacle',
           'proberound', 'attention', 'rt', 'nav_mindist',
           'nav_mindist_timestep']].assign(exp="exp3"),
        exp5b_at[['sessionId', 'grid', 'trans', 'round', 'proberound',
                  'obstacle', 'rt', 'attention']].assign(exp="exp5b")
    ]).reset_index(drop=True)
    exp3_5b_at['attention_N'] = utils.normalize(exp3_5b_at['attention'])
    exp3_5b_at = exp3_5b_at.merge(model_preds)
    exp3_5b_at['neg_optpolicy_dist_Z'] = -exp3_5b_at['optpolicy_dist_Z']

    # combine memory into a single dataframe
    exp3_5b_mt = pd.concat([
        exp3_mt[['sessionId', 'round', 'grid', 'trans', 'obstacle',
           'proberound', 'correct', 'conf', 'nav_mindist',
           'nav_mindist_timestep']].assign(exp="exp3"),
        exp5b_mt[['sessionId', 'grid', 'trans', 'round', 'proberound',
                  'obstacle', 'correct', 'conf']].assign(exp="exp5b")
    ]).reset_index(drop=True)
    exp3_5b_mt['conf_N'] = utils.normalize(exp3_5b_mt['conf'])
    exp3_5b_mt = exp3_5b_mt.merge(model_preds)
    exp3_5b_mt['neg_optpolicy_dist_Z'] = -exp3_5b_mt['optpolicy_dist_Z']
    return exp3_5b_at, exp3_5b_mt

# ================== #
# Experiment 6a Data #
# ================== #
@lru_cache()
def get_exp6a_st__exp6a_nt():
    exp6a_st = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp6a/data/all-survey-trials.json"), "r")))
    exp6a_nt = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp6a/data/all-nav-trials.json"), "r")))

    #apply exclusions
    exp6a_st = exp6a_st[~exp6a_st.exclude].reset_index(drop=True)
    exp6a_nt = exp6a_nt[~exp6a_nt['exclude_trial'] & exp6a_nt.sessionId.isin(exp6a_st.sessionId)].reset_index(drop=True)

    exp6a_nt['grid'] = exp6a_nt['grid'].apply(lambda g: "-".join(g.split('-')[:-1]))
    exp6a_nt['state_traj'] = exp6a_nt['navigationData'].apply(lambda d: [tuple(i['state']) for i in d])
    return exp6a_st, exp6a_nt
    
@lru_cache()
def get_exp6a_navdist():
    exp6a_st, exp6a_nt = get_exp6a_st__exp6a_nt()
    exp6a_navdist = pd.concat([
        exp6a_nt[['sessionId', 'round', 'grid']],
        exp6a_nt.apply(calc_nav_mindist, axis=1)
    ], axis=1).melt(id_vars=['sessionId', 'round', 'grid'], var_name="obstacle", value_name="nav_mindist")
    return exp6a_navdist
    
@lru_cache()
def get_exp6a_navdist_timestep():
    exp6a_st, exp6a_nt = get_exp6a_st__exp6a_nt()
    exp6a_navdist_timestep = pd.concat([
        exp6a_nt[['sessionId', 'round', 'grid']],
        exp6a_nt.apply(calc_nav_mindist_timestep, axis=1)
    ], axis=1).melt(id_vars=['sessionId', 'round', 'grid'], var_name="obstacle", value_name="nav_mindist_timestep")
    return exp6a_navdist_timestep
    
@lru_cache()
def get_exp6a_at():
    exp6a_st, exp6a_nt = get_exp6a_st__exp6a_nt()
    exp6a_at = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp6a/data/all-attention-trials.json"), "r")))

    #apply exclusions over attention trials
    exp6a_at = exp6a_at[~exp6a_at['exclude_trial'] & exp6a_at.sessionId.isin(exp6a_st.sessionId)].reset_index(drop=True)
    exp6a_at = exp6a_at.rename(columns={"transform": "trans", "queryround": "proberound", "attn_resp": "attention", "attn_resp_N": "attention_N"})
    exp6a_at['obstacle'] = exp6a_at['obstacle'].apply(lambda o: f"obs-{o}")
    exp6a_at['grid'] = exp6a_at['grid'].apply(lambda g: "-".join(g.split('-')[:-1]))

    # reformat attention
    temp = exp6a_at.attention
    temp = temp - 4
    temp[temp <= 0] = temp[temp <= 0] - 1
    exp6a_at.attention = temp
    exp6a_at = exp6a_at.drop('attention_N', axis=1)
    exp6a_at['attention_N'] = utils.normalize(exp6a_at['attention'])

    #calculate navdist predictors
    exp6a_navdist = get_exp6a_navdist()
    exp6a_navdist_timestep = get_exp6a_navdist_timestep()
    exp6a_at = exp6a_at.\
        merge(exp6a_navdist, on=['sessionId', 'round', 'grid', 'obstacle']).\
        merge(exp6a_navdist_timestep, on=['sessionId', 'round', 'grid', 'obstacle'])
    return exp6a_at

@lru_cache()
def get_exp1_6a_at():
    exp1_at = get_exp1_at()
    exp6a_at = get_exp6a_at()
    assert set(exp1_at['attention'].unique()) == set(exp6a_at['attention'].unique())
    assert set(exp1_at['obstacle'].unique()) == set(exp6a_at['obstacle'].unique())
    assert set(exp1_at['grid'].unique()) == set(exp6a_at['grid'].unique())

    # combine attn into a single dataframe
    exp1_6a_at = pd.concat([
        exp1_at[['sessionId', 'round', 'grid', 'trans', 'obstacle',
           'proberound', 'attention', 'rt', 'nav_mindist',
           'nav_mindist_timestep']].assign(exp="exp1"),
        exp6a_at[['sessionId', 'grid', 'trans', 'round', 'proberound',
                  'obstacle', 'rt', 'attention', 'nav_mindist']].assign(exp="exp6a")
    ]).reset_index(drop=True)
    exp1_6a_at['attention_N'] = utils.normalize(exp1_6a_at['attention'])
    exp1_6a_at['nav_mindist_Z'] = utils.zscore(exp1_6a_at['nav_mindist'])
    exp1_6a_at = exp1_6a_at.merge(model_preds)
    exp1_6a_at['neg_optpolicy_dist_Z'] = -exp1_6a_at['optpolicy_dist_Z']
    exp1_6a_at['neg_nav_mindist_Z'] = -exp1_6a_at['nav_mindist_Z']
    return exp1_6a_at

# ================== #
# Experiment 6b Data #
# ================== #
@lru_cache()
def get_exp6b_at__exp6b_mt():
    exp6b_st = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp6b/data/all-survey-trials.json"), 'r')))
    exp6b_at = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp6b/data/all-attention-trials.json"), 'r')))
    exp6b_mt = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp6b/data/all-memory-trials.json"), 'r')))
    # note: nav_mindist is already in 6b_at and 6b_mt

    #apply exclusions
    exp6b_st = exp6b_st[~exp6b_st.exclude].reset_index(drop=True)
    exp6b_at = exp6b_at[exp6b_at.sessionId.isin(exp6b_st.sessionId)].reset_index(drop=True)
    exp6b_at = exp6b_at.rename(columns={"transform": "trans", "queryround": "proberound", "attn_resp": "attention", "attn_resp_N": "attention_N"})
    exp6b_mt = exp6b_mt[exp6b_mt.sessionId.isin(exp6b_st.sessionId)].reset_index(drop=True)
    exp6b_mt = exp6b_mt.rename(columns={"transform": "trans", "queryround": "proberound"})

    # reformat attention
    temp = exp6b_at.attention
    temp = temp - 4
    temp[temp <= 0] = temp[temp <= 0] - 1
    exp6b_at.attention = temp
    exp6b_at['attention_N'] = utils.normalize(exp6b_at['attention'])
    exp6b_at['obstacle'] = exp6b_at['obstacle'].apply(lambda o: f"obs-{o}")

    # reformat conf
    temp = exp6b_mt.conf
    temp = temp - 4
    temp[temp <= 0] = temp[temp <= 0] - 1
    exp6b_mt.conf = temp
    exp6b_mt['conf_N'] = utils.normalize(exp6b_mt['conf'])
    exp6b_mt['obstacle'] = exp6b_mt['obstacle'].apply(lambda o: f"obs-{o}")
    return exp6b_at, exp6b_mt

@lru_cache()
def get_exp3_6b_at__exp3_6b_mt():
    exp3_at, exp3_mt = get_exp3_at__exp3_mt()
    exp6b_at, exp6b_mt = get_exp6b_at__exp6b_mt()
    assert set(exp3_at['attention'].unique()) == set(exp6b_at['attention'].unique())
    assert set(exp3_at['obstacle'].unique()) == set(exp6b_at['obstacle'].unique())
    assert set(exp3_at['grid'].unique()) == set(exp6b_at['grid'].unique())
    assert set(exp3_mt['conf'].unique()) == set(exp6b_mt['conf'].unique())
    assert set(exp3_mt['obstacle'].unique()) == set(exp6b_mt['obstacle'].unique())
    assert set(exp3_mt['grid'].unique()) == set(exp6b_mt['grid'].unique())

    # combine attn into a single dataframe
    exp3_6b_at = pd.concat([
        exp3_at[['sessionId', 'round', 'grid', 'trans', 'obstacle',
           'proberound', 'attention', 'rt', 'nav_mindist',
           'nav_mindist_timestep']].assign(exp="exp3"),
        exp6b_at[['sessionId', 'grid', 'trans', 'round', 'proberound',
                  'obstacle', 'rt', 'attention']].assign(exp="exp6b")
    ]).reset_index(drop=True)
    exp3_6b_at['attention_N'] = utils.normalize(exp3_6b_at['attention'])
    exp3_6b_at = exp3_6b_at.merge(model_preds)
    exp3_6b_at['neg_optpolicy_dist_Z'] = -exp3_6b_at['optpolicy_dist_Z']

    # combine memory into a single dataframe
    exp3_6b_mt = pd.concat([
        exp3_mt[['sessionId', 'round', 'grid', 'trans', 'obstacle',
           'proberound', 'correct', 'conf', 'nav_mindist',
           'nav_mindist_timestep']].assign(exp="exp3"),
        exp6b_mt[['sessionId', 'grid', 'trans', 'round', 'proberound',
                  'obstacle', 'correct', 'conf']].assign(exp="exp6b")
    ]).reset_index(drop=True)
    exp3_6b_mt['conf_N'] = utils.normalize(exp3_6b_mt['conf'])
    exp3_6b_mt = exp3_6b_mt.merge(model_preds)
    exp3_6b_mt['neg_optpolicy_dist_Z'] = -exp3_6b_mt['optpolicy_dist_Z']
    return exp3_6b_at, exp3_6b_mt
