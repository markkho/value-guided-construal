#
# Prepare results for analysis
#
# %%
import pandas as pd
import numpy as np
from collections import defaultdict
import fire
import json

NUM_ROUNDS = 12

# Exclusion criteria
COMPREHENSION_CHECK_CUTOFF = 2
TOTAL_NAV_TIME_CUTOFF_MS = 60000
INIT_STEP_RT_CUTOFF_MS = 30000
NON_INITIAL_RT_CUTOFF_MS = 2000
VALID_ROUNDS_CUTOFF_PROP = .8

# %%
def do_exclusions(RESULTSDIR, BASEGRIDS_FILENAME):
    """Apply exclusion criteria to results files"""
#%%
    # load data
    pt = pd.read_json(open(RESULTSDIR+"all-participantdata.json", 'r'))
    nt = pd.read_json(open(RESULTSDIR+"all-navtrials.json", 'r'))
    at = pd.read_json(open(RESULTSDIR+"all-attentiontrials.json", 'r'))

    n_grid_probes = len(at[['grid', 'probeobs']].drop_duplicates())

    # pt = pt[['sessionId', 'condition', 'navCheck', 'navBonusCheck', 'memoryBonusCheck', 'bonusDollars', 'videogames', 'totaltime', 'age', 'gender']]
    # nt = nt[['sessionId', 'round', 'grid', 'trans',
    #          'trialnum', 'state', 'state_type', 'action', 'nextstate',
    #          'start_datetime', 'response_datetime', 'rt'
    # ]].reset_index(drop=True)
    # at = at[['sessionId', 'round', 'grid', 'trans', 'queryround', 'probeobs', 'attention', 'rt']]
    at = at[at['sessionId'].isin(pt.sessionId)]
    nt = nt[nt['sessionId'].isin(pt.sessionId)]

    try:
        notMissingTrials = at.groupby("sessionId")['block'].count() >= VALID_ROUNDS_CUTOFF_PROP*n_grid_probes
    except KeyError:
        notMissingTrials = at.groupby("sessionId")['attention'].count() >= VALID_ROUNDS_CUTOFF_PROP*n_grid_probes
    sidKeep = notMissingTrials.index[notMissingTrials]

    at = at[at['sessionId'].isin(sidKeep)]
    nt = nt[nt['sessionId'].isin(sidKeep)]
    pt = pt[pt['sessionId'].isin(sidKeep)]
    print(f"{len(sidKeep)} of {len(notMissingTrials)} with >{VALID_ROUNDS_CUTOFF_PROP*n_grid_probes} recorded trials")

    print("Performing Exclusions")
    response_stats = defaultdict(lambda: list)

# %% codecell
    # Comprehension checks
    def failed_comp_check(r):
        return ((r['navCheck'] == 'True') +
            (r['navBonusCheck'] == '10 cents') +
            (r['memoryBonusCheck'] == 'None')) < COMPREHENSION_CHECK_CUTOFF
    failed_comp = pt.apply(failed_comp_check, axis=1)
    passed_comp = pt[~failed_comp]['sessionId']

    pt = pt[pt['sessionId'].isin(passed_comp)]
    at = at[at['sessionId'].isin(passed_comp)]
    nt = nt[nt['sessionId'].isin(passed_comp)]

    print(f"{len(passed_comp)} of {len(failed_comp)} passed {COMPREHENSION_CHECK_CUTOFF} of 3 comprehension checks")

# %% codecell
    # Response Time and Round Exclusions
    def calc_by_round_exclusion_criteria(ts):
        ts = ts.sort_values('trialnum')
        straj = [tuple(s) for s in ts.sort_values('trialnum')['state']]
        tnums = ts['trialnum']
        non_consec_trials = \
            [(i + 1) != ii for i, ii in zip(tnums[:], tnums[1:])]

        total_nav_time = \
            ts['response_datetime'].max() - ts['start_datetime'].min()
        last_3_steps_rt = ts.sort_values('trialnum').iloc[-3:]['rt'].sum()
        init_step_time = ts[ts['trialnum'] == 0]['rt'].max()
        non_initial_step_rt = ts[ts['trialnum'] != 0]['rt'].max()

        return pd.Series({
            'non_consec_trials': sum(non_consec_trials) > 0,
            'multiple_first_trials':\
                (ts['trialnum'] == 0).sum() > 1,
            'high_total_nav_time':\
                total_nav_time > TOTAL_NAV_TIME_CUTOFF_MS,
            'high_initial_step_time':\
                init_step_time > INIT_STEP_RT_CUTOFF_MS,
            'high_non_initial_step_rt': \
                non_initial_step_rt > NON_INITIAL_RT_CUTOFF_MS
        })

    round_exclusions = nt.groupby(["grid", "sessionId", "round"]).\
        apply(calc_by_round_exclusion_criteria)
    round_exclusions['any_exclusion'] = round_exclusions.apply(any, axis=1)

    for col in round_exclusions.columns:
        print('\t'.join([col+": ", f"{round_exclusions[col].sum()} of {len(round_exclusions)}"]))

    rounds_to_keep =\
        round_exclusions[~round_exclusions['any_exclusion']].\
        reset_index()[['grid', 'sessionId', 'round']]
    at = at.merge(rounds_to_keep)
    nt = nt.merge(rounds_to_keep)
#%%
    # Exclusion based on valid rounds
    enoughTrials = at.groupby('sessionId')['attention'].count() >= VALID_ROUNDS_CUTOFF_PROP*n_grid_probes
    sidKeep = enoughTrials.index[enoughTrials]
    print(f"Participants with {VALID_ROUNDS_CUTOFF_PROP*n_grid_probes} of {n_grid_probes} valid response trials: {len(sidKeep)} of {len(pt)}")

    at = at[at['sessionId'].isin(sidKeep)]
    nt = nt[nt['sessionId'].isin(sidKeep)]
    pt = pt[pt['sessionId'].isin(sidKeep)]
#%%
    # save
    print(f"Total remaining participants: {len(pt)}")
    print(f"Total remaining rounds: {len(at.groupby(['sessionId', 'grid']))}")
    print(f"Total remaining responses: {len(at)}")

    pt.to_json(RESULTSDIR+"participantdata.json")
    at.to_json(RESULTSDIR+"attentiontrials.json")
    nt.to_json(RESULTSDIR+"navtrials.json")


# #%%
# def make_navigation_rounds(RESULTSDIR, BASEGRIDS_FILENAME):
#     """Create a dataframe of navigation round statistics"""
# #%%
#     at = pd.read_json(RESULTSDIR+"attentiontrials.json")
#     nt = pd.read_json(RESULTSDIR+"navtrials.json")
#     pt = pd.read_json(RESULTSDIR+"participantdata.json")
#     basegrids = json.load(open(BASEGRIDS_FILENAME, 'r'))
#
#     from collections import Counter
#
#     byround = [] #stats by round
#     nav_obstacles = [] #stats for each obstacle in a round
#     for idx, rows in nt.groupby(['sessionId', 'round', 'grid', 'trans', 'gridname']):
#         sid, ri, grid, trans, gridname = idx
#         rows = rows.sort_values('trialnum')
#         stateTraj = [tuple(s) for s in rows.sort_values('trialnum')['state']]
#         scounts = Counter(stateTraj)
#         revisits = sum([c-1 for c in scounts.values() if c > 1])
#         totrt = rows['rt'].sum()
#         totlogrt = np.log(totrt)
#         assert sum(rows['trialnum'] == 0) == 1
#         initlogrt = np.log(rows[rows['trialnum'] == 0]['rt']).mean()
#         initrt = rows[rows['trialnum'] == 0]['rt'].mean()
#         noninitlogrt = np.log(rows[rows['trialnum'] != 0]['rt'] + 1).mean()
#         noninitrt = rows[rows['trialnum'] != 0]['rt'].mean()
#
#         round_stats = {
#             'sessionId': sid,
#             'round': ri,
#             'grid': grid,
#             'trans': trans,
#             'gridname': gridname,
#
#             'nav_len': len(stateTraj),
#             'nav_revisits': revisits,
#             'nav_init_logrt': initlogrt,
#             'nav_init_rt': initrt,
#             'nav_mean_noninit_logrt': noninitlogrt,
#             'nav_mean_noninit_rt': noninitrt,
#             'nav_tot_rt': totrt,
#             'nav_tot_logrt': totlogrt
#         }
#         byround.append(round_stats)
#
#         # calculate statistics for each obstacle
#         navgrid = basegrids["grid-"+str(grid)+'-0']
#         for obsf in '0123456':
#             obs_locs = get_locs(navgrid, obsf)
#             mindiststats = min_dist(stateTraj, obs_locs, 'traj', 'obs')
#             goal_loc = get_locs(navgrid, "G")
#             goalstats = min_dist(obs_locs, goal_loc, 'obs', 'goal')
#             start_loc = get_locs(navgrid, "S")
#             startstats = min_dist(obs_locs, start_loc, 'obs', 'start')
#             nbumps = get_bumps(stateTraj, obs_locs)
#             nav_obstacles.append({
#                 "sessionId": sid,
#                 'round': ri,
#                 'grid': grid,
#                 'trans': trans,
#                 'gridname': gridname,
#                 "obstacle": "obs-"+obsf,
#                 'nbumps': nbumps,
#                 **{'nav_'+k: v for k, v in mindiststats.items()},
#                 **{'goal_'+k: v for k, v in goalstats.items()},
#                 **{'start_'+k: v for k, v in startstats.items()},
#             })
#     byround = pd.DataFrame(byround)
#     nav_obstacles = pd.DataFrame(nav_obstacles)
#     byround.to_json(RESULTSDIR+"navrounds.json")
#     nav_obstacles.to_json(RESULTSDIR+"nav-obs-results.json")

# %%
if __name__ == '__main__':
    fire.Fire()
