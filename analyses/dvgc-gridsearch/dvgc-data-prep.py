import pandas as pd
import os
import json
from vgc_project import utils

def prepare_obstacle_data():
    DATA_DIRECTORY = "../../experiments"

    # Exp 1
    exp1_at = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp1/data/attentiontrials.json"), 'r')))
    exp1_at = exp1_at[['sessionId', 'round', 'grid', 'trans', 'probeobs', 'queryround', 'attention', 'rt']]\
        .rename(columns={"probeobs": "obstacle", "queryround": "proberound"})
    exp1_at['grid'] = exp1_at['grid'].apply(lambda gi: f"grid-{gi}")
    exp1_at['obstacle'] = exp1_at['obstacle'].apply(lambda oi: f"obs-{oi}")
    exp1_at['attention_N'] = utils.normalize(exp1_at['attention'], minval=-4, maxval=4)
    exp1_at_mean = exp1_at.groupby(["grid", "obstacle"])["attention_N"].mean()

    # Exp 2
    exp2_at = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp2/data/attentiontrials.json"), 'r')))
    exp2_at['earlyterm'] = exp2_at.navgridname.apply(lambda g: g.split('-')[-1])
    exp2_at = exp2_at[['sessionId', 'round', 'grid', 'trans', 'earlyterm', 'probeobs', 'queryround', 'attention', 'rt']]\
        .rename(columns={"probeobs": "obstacle", "queryround": "proberound"})
    exp2_at['grid'] = exp2_at['grid'].apply(lambda gi: f"grid-{gi}")
    exp2_at['obstacle'] = exp2_at['obstacle'].apply(lambda oi: f"obs-{oi}")
    exp2_at['attention_N'] = utils.normalize(exp2_at['attention'], minval=-4, maxval=4)
    exp2_at_mean = exp2_at.groupby(["grid", "obstacle"])["attention_N"].mean()

    # Exp 3 Awareness
    exp3_at = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp3/data/attentiontrials.json"), 'r')))
    exp3_at = exp3_at[['sessionId', 'round', 'grid', 'trans', 'probeobs', 'queryround', 'attention', 'rt']]\
        .rename(columns={"probeobs": "obstacle", "queryround": "proberound"})
    exp3_at['grid'] = exp3_at['grid'].apply(lambda gi: f"grid-{gi}")
    exp3_at['obstacle'] = exp3_at['obstacle'].apply(lambda oi: f"obs-{oi}")
    exp3_at['attention_N'] = utils.normalize(exp3_at['attention'], minval=-4, maxval=4)
    exp3_at_mean = exp3_at.groupby(['grid', 'obstacle'])['attention_N'].mean()

    # Exp 3 Acc, Conf
    exp3_mt = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp3/data/memorytrials.json"), 'r')))
    exp3_mt = exp3_mt[['sessionId', 'round', 'grid', 'trans', 'probeobs', 'queryround', 'correct', 'conf', 'rt_mem', 'rt_conf']]\
        .rename(columns={"probeobs": "obstacle", "queryround": "proberound"})
    exp3_mt['grid'] = exp3_mt['grid'].apply(lambda gi: f"grid-{gi}")
    exp3_mt['obstacle'] = exp3_mt['obstacle'].apply(lambda oi: f"obs-{oi}")
    exp3_mt['conf_N'] = utils.normalize(exp3_mt['conf'], minval=-4, maxval=4)
    exp3_mt_mean = exp3_mt.groupby(['grid', 'obstacle'])[['correct', 'conf_N']].mean()

    # Exp 4a
    exp4a_ht = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp4a/data/hovering-data-trials.json"), 'r')))
    exp4a_ht['obstacle'] = exp4a_ht['obstacle'].apply(lambda o: f"obs-{o}")
    exp4a_ht['grid'] = exp4a_ht['grid'].apply(lambda g: "-".join(g.split("-")[:-1]))
    exp4a_ht_mean = exp4a_ht.groupby(['grid', 'obstacle'])[['log_hoverduration', 'hovered']].mean()

    # Exp 4b
    exp4b_ht = pd.DataFrame(json.load(open(os.path.join(DATA_DIRECTORY, "exp4b/data/hovering-data-trials.json"), 'r')))
    exp4b_ht['obstacle'] = exp4b_ht['obstacle'].apply(lambda o: f"obs-{o}")
    exp4b_ht_mean = exp4b_ht.groupby(['grid', 'obstacle'])[['log_hoverduration', 'hovered']].mean()

    #  Save mean data
    mean_obstacle_data = dict(
        exp1_at=exp1_at_mean.reset_index().to_dict(),
        exp2_at=exp2_at_mean.reset_index().to_dict(),
        exp3_at=exp3_at_mean.reset_index().to_dict(),
        exp3_mt=exp3_mt_mean.reset_index().to_dict(),
        exp4a_ht=exp4a_ht_mean.reset_index().to_dict(),
        exp4b_ht=exp4b_ht_mean.reset_index().to_dict(),
    )

    with open("./mean_obstacle_data.json", "w") as file:
        file.write(json.dumps(mean_obstacle_data))

    # Mazes
    mazes_0_11 = json.load(open(os.path.join(DATA_DIRECTORY, "mazes/mazes_0-11.json"), 'r'))
    mazes_12_15 = json.load(open(os.path.join(DATA_DIRECTORY, "mazes/mazes_12-15.json"), 'r'))
    mazes = {
        **{"-".join(k.split('-')[:-1]): tuple(v) for k,v in mazes_0_11.items()},
        **{k: tuple(v) for k,v in mazes_12_15.items()}
    }
    with open("./mazes.json", "w") as file:
        file.write(json.dumps(mazes))

if __name__ == "__main__":
    prepare_obstacle_data()
