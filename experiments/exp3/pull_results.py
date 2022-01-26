import urllib.request
import csv, json
import fire
import numpy as np
import pandas as pd
from vgc_project.gridutils import untransformations, untransformState, transformations

# %%
# %%
def pull_data_from_server(EXP_NAME, RAWRESULTS_DIR, CREDENTIALS_FILE):
# %%
    """Download data from the server"""
    CREDENTIALS = json.load(open(CREDENTIALS_FILE, 'r'))
    EXPURL = CREDENTIALS["EXPURL"]
    USERNAME = CREDENTIALS["USERNAME"]
    PASSWORD = CREDENTIALS["PASSWORD"]

    if len(EXPURL) == 0 or len(USERNAME) == 0 or len(PASSWORD) == 0:
        print("No url/username/password specified for downloading data")
        return

    sourcedest = [
        (f"data/{EXP_NAME}/trialdata", RAWRESULTS_DIR+"rawtrialdata.csv"),
        (f"data/{EXP_NAME}/questiondata", RAWRESULTS_DIR+"rawquestiondata.csv"),
        (f"data/{EXP_NAME}/bonusdata", RAWRESULTS_DIR+"rawbonusdata.csv")
    ]
    # stuff needed to open with authentication
    print(f"pulling data for experiment '{EXP_NAME}' from {EXPURL} with credentials {USERNAME}:{PASSWORD}")
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

    excludewid = [
        '5e14f5764f849eb011a0da:02my8yeqr7n6' #debugging
    ]
# %%
    #parse question data
    participantdata = {}
    for row in questiondata:
        wid, key, value = row
        if "debug" in wid:
            continue
        if wid in excludewid:
            continue
        participantdata[wid] = participantdata.get(wid, {})
        participantdata[wid][key] = value

# %%
    # parse trial data
    trainingtrials = []
    navtrials = []
    attntrials = []
    memtrials = []
    conftrials = []
    startendtimes = {}
    for t in trialdata:
        wid, page, datetimeMS, record = t
        if "debug" in wid or (wid in excludewid):
            continue

        #get participant's timeline
        try:
            pcond = expConfig['timelines'][int(participantdata[wid]['condition'])]
        except KeyError:
            print(f"Skipping unknown participant: {wid}")
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
        elif record.get("roundtype", None) == "probe_2afc":
            memtrials.append(record)
        elif record.get("roundtype", None) == "probe_conf":
            conftrials.append(record)
        elif record.get("type", None) == "experiment_setup":
            del record['bonusDollars']
            participantdata[wid] = participantdata.get(wid, {})
            participantdata[wid].update(record)
        elif record.get('trial_type') in ["survey-multi-choice", "survey-text"]:
            participantdata[wid] = participantdata.get(wid, {})
            trialidx = record['trial_index'] - 1 #first is fullscreen
            trialparams = pcond[trialidx]['questions']
            record2 = {trialparams[int(qi[1:])]['name']: resp
                       for qi, resp in json.loads(record['responses']).items()}
            participantdata[wid].update(record2)
        elif record.get('trial_type') in ["survey-likert"]:
            participantdata[wid] = participantdata.get(wid, {})
            trialidx = record['trial_index'] - 1 #first is fullscreen
            trialparams = pcond[trialidx]['questions']
            record2 = {trialparams[int(qi[1:])]['name']: trialparams[int(qi[1:])]['labels'][resp]
                       for qi, resp in json.loads(record['responses']).items()}
            participantdata[wid].update(record2)
        elif record.get('trial_type') in ["GridNavigation", "GridMatching",
                                          "CustomInstructions", "fullscreen",
                                          "GridMatchConfidence", "GridBlockAttentionQuery", "CustomItem"]:
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
    #memory and confidence trials
    mt = pd.DataFrame(memtrials)
    mt['grid'] = mt['navgridname'].apply(lambda n: n.split('-')[1])
    mt['mod'] = mt['navgridname'].apply(lambda n: {'0': 'true', 'M': 'mod'}[n.split('-')[2]])
    mt['trans'] = mt['navgridname'].apply(lambda n: n.split('-')[3])
    mt['earlyterm'] = mt['navgridname'].apply(lambda n: n.split('-')[4])
    mt['true_color'] = mt['true_color'].apply(lambda c: {"#DCCB5D": "Yellow", "#44A9A0": "Green"}[c])
    mt['correct'] = mt.apply(lambda r: r['true_color'] == r['response'], axis=1)
    mt['rt'] = mt['responsetime'] - mt['starttime']
    mt = mt[[
       'navgridname', 'probegridname', 'probeobs', 'queryround', 'round',
       'sessionId', 'starttime', 'responsetime', 'response', 'wid', 'grid',
       'trans', 'earlyterm', 'correct', 'rt', 'true_color'
    ]]

    ct = pd.DataFrame(conftrials)
    ct['grid'] = ct['navgridname'].apply(lambda n: n.split('-')[1])
    ct['mod'] = ct['navgridname'].apply(lambda n: {'0': 'true', 'M': 'mod'}[n.split('-')[2]])
    ct['trans'] = ct['navgridname'].apply(lambda n: n.split('-')[3])
    ct['earlyterm'] = ct['navgridname'].apply(lambda n: n.split('-')[4])
    ct['conf'] = ct['response'].apply(lambda r: {'1': -4, '2': -3, '3': -2,
                                                      '4': -1, '5': 1, '6': 2, '7': 3, '8': 4}[r.strip()])
    ct['true_color'] = ct['true_color'].apply(lambda c: {"#DCCB5D": "Yellow", "#44A9A0": "Green"}[c])
    ct['rt'] = ct['responsetime'] - ct['starttime']
    ct = ct[[
       'navgridname', 'probegridname', 'probeobs', 'queryround', 'round',
       'sessionId', 'starttime', 'responsetime', 'response', 'wid', 'grid',
       'trans', 'earlyterm', 'conf', 'rt', 'true_color'
    ]]

    mt = mt.merge(ct, on=['sessionId', 'round', 'navgridname', 'queryround', 'probeobs', 'true_color', 'grid', 'trans'], suffixes=("_mem", "_conf"))

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
        g = basegrids[f"gridB-{row['grid']}-0"]
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
    mt.to_json(EXP_RESULTS_DIR+"all-memorytrials.json")

#%%
if __name__ == "__main__":
    fire.Fire()
