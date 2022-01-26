import urllib.request
import csv, json
import fire
import numpy as np
import pandas as pd
from vgc_project.gridutils import untransformations, untransformState, transformations


# %%
def pull_data_from_server(EXP_NAME, RAWRESULTS_DIR, CREDENTIALS_FILE):
# %%
    """Download data from the server"""
    CREDENTIALS = json.load(open(CREDENTIALS_FILE, 'r'))
    EXPURL = CREDENTIALS["EXPURL"]
    USERNAME = CREDENTIALS["USERNAME"]
    PASSWORD = CREDENTIALS["PASSWORD"]
    sourcedest = [
        (f"data/{EXP_NAME}/trialdata", RAWRESULTS_DIR+"rawtrialdata.csv"),
        (f"data/{EXP_NAME}/questiondata", RAWRESULTS_DIR+"rawquestiondata.csv"),
        (f"data/{EXP_NAME}/bonusdata", RAWRESULTS_DIR+"rawbonusdata.csv")
    ]
    # stuff needed to open with authentication
    print(f"pulling data for experiment '{EXP_NAME}'")
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, EXPURL, USERNAME, PASSWORD)
    handler = urllib.request.HTTPBasicAuthHandler(password_mgr)

    for SOURCE, DEST in sourcedest:
        opener = urllib.request.build_opener(handler)
        opener.open(EXPURL+SOURCE)
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(EXPURL+SOURCE, DEST)

#%%
def parse_raw_datafiles(
    BASEGRIDS_FILENAME, RAWRESULTS_DIR,
    EXP_CONFIG_FILE, EXP_RESULTS_DIR):
#%%
    """Parse downloaded datafiles"""
    print("Parsing downloaded datafiles...")

    basegrids = json.load(open(BASEGRIDS_FILENAME, 'r'))
    trialdata = [line for line in csv.reader(open(RAWRESULTS_DIR+"rawtrialdata.csv", 'r'))]
    questiondata = [line for line in csv.reader(open(RAWRESULTS_DIR+"rawquestiondata.csv", 'r'))]
    bonusdata = [line for line in csv.reader(open(RAWRESULTS_DIR+"rawtrialdata.csv", 'r'))]

    # jsPsych does not save questions
    expConfig = json.load(open(EXP_CONFIG_FILE, 'r'))
    cond0 = expConfig['timelines'][0]

    excludewid = [
        '5e14f5764f849eb011a0da:02my8yeqr7n6', #debugging
        '5f0df709c887690e5bede0ec:5fa986ab92918916e8fce2b4' #did not understand trials ended early
    ]
# %%
    #parse question data
    participantdata = {}
    for row in questiondata:
        wid, key, value = row
        if "debug" in wid:
            continue
        if wid in excludewid:
            print(f"Excluding {wid}")
            continue
        participantdata[wid] = participantdata.get(wid, {})
        participantdata[wid][key] = value

# %%
    # parse trial data
    trainingtrials = []
    navtrials = []
    attntrials = []
    startendtimes = {}
    for t in trialdata:
        wid, page, datetimeMS, record = t
        if "debug" in wid or (wid in excludewid):
            continue
        startendtimes[wid] = startendtimes.get(wid, {'starttime': np.inf, "endtime": -np.inf})
        startendtimes[wid]['starttime'] = min(startendtimes[wid]['starttime'], int(datetimeMS))
        startendtimes[wid]["endtime"] = max(startendtimes[wid]["endtime"], int(datetimeMS))
        record = json.loads(record)
        record['wid'] = wid
        if record.get('roundtype', None) == "navigation":
            navtrials.append(record)
        elif record.get('roundtype', None) == "practice":
            trainingtrials.append(record)
        elif record.get("type", None) == "GridBlockAttentionQuery":
            attntrials.append(record)
        elif record.get("type", None) == "experiment_setup":
            del record['bonusDollars']
            participantdata[wid] = participantdata.get(wid, {})
            participantdata[wid].update(record)
        elif record.get('trial_type') in ["survey-multi-choice", "survey-text"]:
            participantdata[wid] = participantdata.get(wid, {})
            trialidx = record['trial_index'] - 1 #first is fullscreen
            trialparams = cond0[trialidx]['questions']
            record2 = {trialparams[int(qi[1:])]['name']: resp
                       for qi, resp in json.loads(record['responses']).items()}
            participantdata[wid].update(record2)
        elif record.get('trial_type') in ["survey-likert"]:
            participantdata[wid] = participantdata.get(wid, {})
            trialidx = record['trial_index'] - 1 #first is fullscreen
            trialparams = cond0[trialidx]['questions']
            record2 = {trialparams[int(qi[1:])]['name']: trialparams[int(qi[1:])]['labels'][resp]
                       for qi, resp in json.loads(record['responses']).items()}
            participantdata[wid].update(record2)
        elif record.get('trial_type') in ["GridNavigation", "GridMatching",
                                          "CustomInstructions", "fullscreen",
                                          "GridMatchConfidence", "GridBlockAttentionQuery"]:
            continue
        elif record.get('type') in ["instructions"]:
            continue
        else:
            print(record)

    for wid, rec in participantdata.items():
        try:
            rec.update(startendtimes[wid])
        except KeyError:
            continue

    pt = pd.DataFrame(participantdata.values())
    tt = pd.DataFrame(trainingtrials)
    nt = pd.DataFrame(navtrials)
    at = pd.DataFrame(attntrials)

# %%
    # participant trials
    pt['totaltime'] = pt['endtime'] - pt['starttime']

# %% codecell
    # set up navtrials
    nt['grid'] = nt['gridname'].apply(lambda n: int(n.split("-")[1]))
    nt['trans'] = nt['gridname'].apply(lambda n: n.split("-")[3])
    nt['trialnum'] = nt['trialnum'].apply(int)
    nt['round'] = nt['round'].apply(int)
    nt['rt'] = nt['response_datetime'] - nt['start_datetime']

    # ### recoding navigation trials
    transformedGrids = {}
    def recodeState(row):
        t = row['trans']
        ts = row['trans_state']
        g = basegrids[f"grid-{row['grid']}-0"]
        try:
            tg = transformedGrids[(t, tuple(g))]
        except KeyError:
            tg = transformations[t](g)
            transformedGrids[(t, tuple(g))] = tg
        s = untransformState[t](tg, ts)
        return [int(si) for si in tuple(np.rint(s))]
    nt['trans_state'] = nt['state']
    nt['state'] = nt.apply(recodeState, axis=1)

# %%
    # attention trials
    attn_resp_recode = {
        '1': -4, '2': -3, '3': -2,
        '4': -1, '5': 1,
        '6': 2, '7': 3, '8': 4
    }
    at['grid'] = at['navgridname'].apply(lambda n: int(n.split('-')[1]))
    at['trans'] = at['navgridname'].apply(lambda n: n.split('-')[3])
    at['attention'] = at['response'].apply(lambda r: attn_resp_recode[str(r).strip()])
    at['rt'] = at['responsetime'] - at['starttime']
    at['logrt'] = np.log(at['rt'])

# %%
    # save
    pt[['wid', 'bonusDollars']].to_json(EXP_RESULTS_DIR+"all-bonuses.json")
    pt = pt.drop('wid', axis=1)
    pt.to_json(EXP_RESULTS_DIR+"all-participantdata.json")
    tt = tt.drop('wid', axis=1)
    tt.to_json(EXP_RESULTS_DIR+"all-trainingtrials.json")
    nt = nt.drop('wid', axis=1)
    nt.to_json(EXP_RESULTS_DIR+"all-navtrials.json")
    at = at.drop('wid', axis=1)
    at.to_json(EXP_RESULTS_DIR+"all-attentiontrials.json")

#%%
if __name__ == "__main__":
    fire.Fire()
