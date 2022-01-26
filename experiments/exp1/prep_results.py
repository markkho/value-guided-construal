#
# Prepare results for analysis
#
import pandas as pd
import numpy as np
from collections import defaultdict
import fire
import json

NUM_ROUNDS = 12

# Exclusion criteria
COMPREHENSION_CHECK_CUTOFF = 2
TOTAL_NAV_TIME_CUTOFF_MS = 20000
LAST3STEPS_RT_CUTOFF_MS = 1500
INIT_STEP_RT_CUTOFF_MS = 5000
NON_INITIAL_RT_CUTOFF_MS = 2000
VALID_ROUNDS_CUTOFF_PROP = .8

def do_exclusions(RESULTSDIR, BASEGRIDS_FILENAME):
    """Apply exclusion criteria to results files"""
    # load data
    pt = pd.read_json(open(RESULTSDIR+"all-participantdata.json", 'r'))
    nt = pd.read_json(open(RESULTSDIR+"all-navtrials.json", 'r'))
    at = pd.read_json(open(RESULTSDIR+"all-attentiontrials.json", 'r'))

    n_grid_probes = len(at[['grid', 'probeobs']].drop_duplicates())
    at = at[at['sessionId'].isin(pt.sessionId)]
    nt = nt[nt['sessionId'].isin(pt.sessionId)]
    notMissingTrials = at.groupby("sessionId")['block'].count() >= VALID_ROUNDS_CUTOFF_PROP*n_grid_probes
    sidKeep = notMissingTrials.index[notMissingTrials]
    at = at[at['sessionId'].isin(sidKeep)]
    nt = nt[nt['sessionId'].isin(sidKeep)]
    pt = pt[pt['sessionId'].isin(sidKeep)]
    print(f"{len(sidKeep)} of {len(notMissingTrials)} with >{VALID_ROUNDS_CUTOFF_PROP*n_grid_probes} recorded trials")

    print("Performing Exclusions")
    response_stats = defaultdict(lambda: list)

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
            'high_last_3_steps_rt':\
                last_3_steps_rt > LAST3STEPS_RT_CUTOFF_MS,
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

    # Exclusion based on valid rounds
    enoughTrials = at.groupby('sessionId')['attention'].count() >= VALID_ROUNDS_CUTOFF_PROP*n_grid_probes
    sidKeep = enoughTrials.index[enoughTrials]
    print(f"Participants with {VALID_ROUNDS_CUTOFF_PROP*n_grid_probes} of {n_grid_probes} valid response trials: {len(sidKeep)} of {len(pt)}")

    at = at[at['sessionId'].isin(sidKeep)]
    nt = nt[nt['sessionId'].isin(sidKeep)]
    pt = pt[pt['sessionId'].isin(sidKeep)]

    # save
    print(f"Total remaining participants: {len(pt)}")
    print(f"Total remaining rounds: {len(at.groupby(['sessionId', 'grid']))}")
    print(f"Total remaining responses: {len(at)}")

    pt.to_json(RESULTSDIR+"participantdata.json")
    at.to_json(RESULTSDIR+"attentiontrials.json")
    nt.to_json(RESULTSDIR+"navtrials.json")

if __name__ == '__main__':
    fire.Fire()
