# %% markdown
## Experiment 3 Trials
# %%
import numpy as np
import fire
import random
import pandas as pd
import json
from itertools import product
from markdown import markdown
import textwrap
from copy import deepcopy
import os, sys, json, pprint
from vgc_project.gridutils import transformations, getFeatureXYs

# %% codecell
def main(BASEGRIDS_FILENAME, EXP_NAME, EXP_CONFIG_FILE):
# %% codecell
    basegrids = json.load(open(BASEGRIDS_FILENAME, 'r'))
    sharedparams = {
        "feature_colors": {
            "#": "black",
            "G": "yellow",
            "S": "white",
            ".": "white",
            **{i: "mediumblue" for i in "0123456"}
        },
        "wall_features": ["#", ] + list("0123456"),
        "show_rewards": False,
    }

    nRounds = 4*2
    roundBonusCents = 15
    INITIALGOAL_COUNTDOWN_SEC = 60000
    EXPERIMENTVERSION = "1.7c"
    emptygrid = [
        "............G",
        ".............",
        ".............",
        "......#......",
        "......#......",
        "......#......",
        "...#######...",
        "......#......",
        "......#......",
        "......#......",
        ".............",
        ".............",
        "S............"
    ]
    instructionstraining = [
        {
            "type": "CustomInstructions",
            "instructions": markdown(textwrap.dedent("""
                # Instructions
                Thank you for participating in our experiment!

                You will play a game where you control a blue circle on a grid. You can move up, down, left, or right by pressing the __arrow keys__⬆️⬇️⬅️➡️.

                <img src="static/images/bluedotgrid.png" width="150px">

                 The <span style='background-color: yellow;'><b>Yellow</b></span> tile with the <span style="color: green"><b>green</b></span> square is the goal 👀.

                <img src="static/images/goalsquare.png" width="150px">

                The green square will shrink when you stand still. It will initially shrink slowly, and then shrink quickly once you start moving. Keep moving!

                <br>

                __Black__ tiles are walls that you cannot pass through ⛔️.

                <br>

                <span style="background-color: cornflowerblue;color:white"><b>Blue</b></span> tiles are obstacles that might change
                between different rounds. You cannot pass through these either 🚫.
            """)),
            "timing_post_trial": 1000,
            "continue_wait_time": 5000,
        },
        {
            "type": "GridNavigation",
            "round": 0,
            "roundtype": "practice",
            "bonus": False,
            "message": """Get to the <span style='background-color: yellow;'>Yellow</span> goal. You cannot go through <br><span style='background-color: black;color: white'>Black</span> or <br><span style='background-color: cornflowerblue; color:white'>Blue</span> tiles.""",
            "taskparams": {
                "feature_array": [
                    "G.........000",
                    "............0",
                    ".............",
                    "......#......",
                    "......#......",
                    "......#......",
                    "...#######...",
                    "......#......",
                    "......#......",
                    "......#......",
                    ".............",
                    "0............",
                    "000.........."
                ],
                "init_state":[12, 0],
                "absorbing_states":[[0, 12]],
                "name": "trainingA",
                **sharedparams
            },
            "emptygrid": emptygrid,
            "goalCountdown": True,
            "participantStarts": False,
            "INITIALGOAL_COUNTDOWN_SEC": INITIALGOAL_COUNTDOWN_SEC,
            "TILE_SIZE": 40
        },
        {
            "type": "GridNavigation",
            "round": 1,
            "roundtype": "practice",
            "bonus": False,
            "message": """Get to the <span style='background-color: yellow;'>Yellow</span> goal. You cannot go through <br><span style='background-color: black;color: white'>Black</span> or <br><span style='background-color: cornflowerblue; color:white'>Blue</span> tiles.""",
            "taskparams": {
            "feature_array": [
                    "G............",
                    ".............",
                    ".............",
                    "......#......",
                    "......#......",
                    "......#...0..",
                    ".00#######000",
                    ".0....#......",
                    ".0....#......",
                    "......#......",
                    ".............",
                    ".............",
                    "............."
                ],
                "init_state":[12, 0],
                "absorbing_states":[[0, 12]],
                "name": "trainingB",
                **sharedparams
            },
            "emptygrid": emptygrid,
            "goalCountdown": True,
            "participantStarts": False,
            "INITIALGOAL_COUNTDOWN_SEC": INITIALGOAL_COUNTDOWN_SEC,
            "TILE_SIZE": 40
        },
        {
            "type": "CustomInstructions",
            "instructions": markdown(textwrap.dedent("""
                # Instructions
                Great! Now, you will be given similar grids, however, after your first move the
                <span style="background-color: cornflowerblue;color:white"><b>Blue</b></span> tiles
                will become invisible.
            """)),
            "timing_post_trial": 1000,
            "continue_wait_time": 2000,
        },
        {
            "type": "GridNavigation",
            "round": 2,
            "roundtype": "practice",
            "bonus": False,
            "message": """The <span style='background-color: cornflowerblue; color:white'>Blue</span> tiles turn invisible.""",
            "taskparams": {
                "feature_array": [
                    "G.........000",
                    "............0",
                    ".............",
                    "......#......",
                    "......#......",
                    "......#......",
                    "...#######...",
                    "......#......",
                    "......#......",
                    "......#......",
                    ".............",
                    "0............",
                    "000.........."
                ],
                "init_state":[12, 0],
                "absorbing_states":[[0, 12]],
                "name": "trainingA",
                **sharedparams,
                "TILE_SIZE": 40
            },
            "emptygrid": emptygrid,
            "goalCountdown": True,
            "participantStarts": False,
            "hideObstaclesOnMove": True,
            "INITIALGOAL_COUNTDOWN_SEC": INITIALGOAL_COUNTDOWN_SEC,
            "TILE_SIZE": 40
        },
        {
            "type": "GridNavigation",
            "round": 3,
            "roundtype": "practice",
            "bonus": False,
            "message": """The <span style='background-color: cornflowerblue; color:white'>Blue</span> tiles turn invisible.""",
            "taskparams": {
            "feature_array": [
                    "G............",
                    ".............",
                    ".............",
                    "......#......",
                    "......#......",
                    "......#...0..",
                    ".00#######000",
                    ".0....#......",
                    ".0....#......",
                    "......#......",
                    ".............",
                    ".............",
                    "............."
                ],
                "init_state":[12, 0],
                "absorbing_states":[[0, 12]],
                "name": "trainingB",
                **sharedparams
            },
            "emptygrid": emptygrid,
            "goalCountdown": True,
            "participantStarts": False,
            "hideObstaclesOnMove": True,
            "INITIALGOAL_COUNTDOWN_SEC": INITIALGOAL_COUNTDOWN_SEC,
            "TILE_SIZE": 40
        },
        {
            "type": "CustomInstructions",
            "instructions": markdown(textwrap.dedent(f"""
                # Instructions
                Great!

                <br>

                Next, we will give you a series of {nRounds} rounds. For each round, you will receive a
                bonus of {roundBonusCents} cents but <b>only if you reach the goal
                without the green square disappearing</b>.

                You can win a total bonus of up to &#36;{nRounds*roundBonusCents/100:.2f}.

                <br>

                At the start of each round, we will show you a grid showing only the walls (black).
                When you are ready to begin the round, press the __spacebar__.
                The obstacles (<span style="background-color: cornflowerblue; color:white">blue</span>),
                your start location, and goal will appear.

                Remember, once you move, the blue obstacles will turn invisible!
            """)),
            "timing_post_trial": 1000,
            "continue_wait_time": 5000,
        }
    ]
    location_instructions = [
        {
            "type": "CustomInstructions",
            "instructions": markdown(textwrap.dedent("""
                # ☝️ Please note the following

                To transition between the rounds as smoothly as possible, we recommend using
                one hand to press the spacebar and the other use the arrow keys 🙌.

                <br>

                Try to go as <u>quickly</u> and <u>carefully</u> as possible 💫.

                <br>

                In addition, we are interested in your thought process while navigating each maze 🤔.
                Following each trial, we will ask you about where one of the obstacles was originally placed.
                You will be shown two possible locations, and asked where it was in the maze you just did.

                **Your answers to these questions will not affect your bonus, but please try to respond accurately.**.

                <br>

                Thanks again for participating in our experiment!

                <br>
            """)),
            "timing_post_trial": 1000,
            "continue_wait_time": 5000,
        },
        {
            "type": 'survey-multi-choice',
            "questions": [
                {
                  "prompt": "If the green square disappears, you will not receive a bonus on that round:",
                  "options": ["True", "False"],
                  "required": True,
                  "name": "navCheck"
                },
                {
                  "prompt": "How much of a bonus will you receive for completing each maze before the green square disappears?",
                  "options": ["25 cents", "15 cents", "12 cents", "None"],
                  "required": True,
                  "name": "navBonusCheck"
                },
                {
                  "prompt": "How much of a bonus will you receive for answering the questions about what you paid attention to?",
                  "options": ["25 cents", "15 cents", "12 cents", "None"],
                  "required": True,
                  "name": "memoryBonusCheck"
                }
            ]
        }
    ]
    awareness_instructions = [
        {
            "type": "CustomInstructions",
            "instructions": markdown(textwrap.dedent("""
                # ☝️ Please note the following

                To transition between the rounds as smoothly as possible, we recommend using
                one hand to press the spacebar and the other use the arrow keys 🙌.

                <br>

                Try to go as <u>quickly</u> and <u>carefully</u> as possible 💫.

                <br>

                In addition, we are interested in your thought process while navigating each maze 🤔.
                Following each trial, we will ask you <u>how aware of each obstacle you were at any point</u>.
                Your answer should reflect the amount you paid attention to an obstacle, whether it was
                at the beginning or end of navigating the maze.

                **Your answers to these questions will not affect your bonus**.

                <br>

                Finally, <b>the maze rounds will sometimes end randomly <u>before</u> you reach the goal</b>.
                As long as the green square has not disappeared, you will receive your bonus on that round,
                but we will still ask you questions about your thought process.

                <br>

                Thanks again for participating in our experiment!

                <br>
            """)),
            "timing_post_trial": 1000,
            "continue_wait_time": 5000,
        },
        {
            "type": 'survey-multi-choice',
            "questions": [
                {
                  "prompt": "If the green square disappears, you will not receive a bonus on that round:",
                  "options": ["True", "False"],
                  "required": True,
                  "name": "navCheck"
                },
                {
                  "prompt": "How much of a bonus will you receive for completing each maze before the green square disappears?",
                  "options": ["25 cents", "15 cents", "12 cents", "None"],
                  "required": True,
                  "name": "navBonusCheck"
                },
                {
                  "prompt": "How much of a bonus will you receive for answering the questions about what you paid attention to?",
                  "options": ["25 cents", "15 cents", "12 cents", "None"],
                  "required": True,
                  "name": "memoryBonusCheck"
                }
            ]
        }
    ]

# %% codecell
    posttask = [
          {
            "type": 'survey-text',
            "questions": [
              {
                  "prompt": "Please describe your process for answering the questions.",
                  "rows": 5,
                  "columns":50,
                  "required": True,
                  "name": "howAttention"
              },
              {
                  "prompt": "Any general comments?",
                  "rows": 5,
                  "columns":50,
                  "required": True,
                  "name": "generalComments"
              },
            ],
          },
          {
            "type": 'survey-likert',
            "questions": [
                {
                    "prompt": "How often do you play video games?",
                    "labels": ["Never", "Every few months", "Monthly", "Weekly", "Daily"],
                    "required": True,
                    "name": "videogames"
                }
            ]
          },
          {
            "type": 'survey-text',
            "questions": [
              {"prompt": "Age", "required": True, "name": "age"},
              {"prompt": "Gender", "required": True, "name": "gender"},
            ],
          }
    ]
# %% codecell
    # ## Generate main trials
    expgrids = {}

    #terminate after 2 steps
    earlyTermDist = [[-2, 0], [2, 0], [0, -2], [0, 2], [1, 1], [-1, 1], [1, -1], [-1, -1]]

    for gridname, trialArray in basegrids.items():
        for tname, trans in transformations.items():
            for earlyTerm in ['full', 'earlyterm']:
                tgridname = f"{gridname}-{tname}-{earlyTerm}"
                transformed = trans(trialArray)
                if earlyTerm == 'full':
                    expgrids[tgridname] = {
                        "feature_array": transformed,
                        "init_state": getFeatureXYs(transformed, "S")[0],
                        "absorbing_states": getFeatureXYs(transformed, "G"),
                        "name": tgridname,
                        **sharedparams
                    }
                elif earlyTerm == 'earlyterm':
                    s0 = getFeatureXYs(transformed, "S")[0]
                    adjToS0 = [[s0[0] + dx, s0[1] + dy] for dx, dy in earlyTermDist]
                    adjToS0 = [s for s in adjToS0 if (s[0] >= 0) and (s[1] >= 0)]
                    expgrids[tgridname] = {
                        "feature_array": transformed,
                        "init_state": s0,
                        "absorbing_states": getFeatureXYs(transformed, "G") + adjToS0,
                        "name": tgridname,
                        **sharedparams
                    }

# %% codecell
    # ### Trial orders
    from functools import reduce

    YELLOW = "#DCCB5D"
    GREEN = "#44A9A0"

    def generateTrialParameters(basegrids, seed, reverse=False, flipEarlyTerm=False, probetype="awareness"):
        random.seed(seed)
        translations = ['base', 'vflip', 'hflip', 'trans']
        truemod_colors = [(GREEN, YELLOW), (YELLOW, GREEN)]
        grididx = [12, 13, 14, 15]

        # at the nav-trial level, randomly assign translations to the grids in 2 blocks
        nblocks = 2
        navtrialparams = []
        for blocki in range(nblocks):
            btrans = deepcopy(translations)
            random.shuffle(btrans)
            bgrids = deepcopy(grididx)
            random.shuffle(bgrids)
            navtrialparams.append([(blocki, gidx, trans) for gidx, trans in zip(bgrids, btrans)])

        # at the probe-trial level, randomly but evenly assign true/mod to each obstacle in
        #the first nav-trial block, then do the opposite in the second nav-trial block.
        # shuffle the probe level trials within each grid block
        probetrials = {}
        firstblock = navtrialparams[0]
        for blocki, gidx, trans in firstblock:
            assert blocki == 0
            probes = ['0', '1', '2', '3', '4']
            probe_colororder = [[(p, corder) for corder in truemod_colors] for p in probes]
            for pcolors in probe_colororder:
                random.shuffle(pcolors)
            probecolors0, probecolors1 = [list(pm) for pm in zip(*probe_colororder)]
            random.shuffle(probecolors0)
            random.shuffle(probecolors1)
            probetrials[(0, gidx)] = probecolors0
            probetrials[(1, gidx)] = probecolors1

        # flatten the blocks
        navtrialparams = sum(navtrialparams, [])
        if reverse:
            navtrialparams = navtrialparams[::-1]

        emptygrid = [
            "............G",
            ".............",
            ".............",
            "......#......",
            "......#......",
            "......#......",
            "...#######...",
            "......#......",
            "......#......",
            "......#......",
            ".............",
            ".............",
            "S............"
        ]
        trialparams = []
        pi = 0
        for ri, (bi, gidx, trans) in enumerate(navtrialparams):
            navgridname = f"gridB-{gidx}-0-{trans}-full"
            #create navigation trial
            trialparams.append({
                "type": "GridNavigation",
                "page": pi,
                "round": ri,
                "roundtype": "navigation",
                "bonus": True,
                "goalCountdown": True,
                "hideObstaclesOnMove": True,
                "message": "",
                "taskparams": expgrids[navgridname],
                "emptygrid": emptygrid,
                "navgridname": navgridname,
                "INITIALGOAL_COUNTDOWN_SEC": INITIALGOAL_COUNTDOWN_SEC,
                "TILE_SIZE": 40
            })
            pi += 1

            if probetype == "location":
                #create maze-obstacle memory trials
                probeparams = probetrials[(bi, gidx)]
                for probeidx, (probeobs, colororder) in enumerate(probeparams):
                    num2alpha = dict(zip("01234", "ABCDE"))

                    probegridname = f"gridB-{gidx}-M-{trans}-full"
                    probegrid = deepcopy(expgrids[probegridname])
                    probeobs = str(probeobs)
                    obs_colors = { #color order is (true, mod)
                        probeobs: colororder[0],
                        num2alpha[probeobs]: colororder[1]
                    }
                    fc = {"#": 'black', **obs_colors}
                    probegrid['feature_colors'] = fc

                    #2afc
                    trialparams.append({
                        #plugin parameters
                        "type": "CustomItem",
                        "questiontext": "An obstacle was <b>either</b> in the yellow <b>or</b> green location (not both), which one was it?",
                        "responseLabels": ["Yellow", "?", "Green"],
                        "validResponses": ["Yellow", "Green"],
                        "initResponse": "?",
                        "responseEndLabels": ["", ""],
                        "stimuli": [{
                            "type": "gridworld",
                            "gridworldparams": probegrid,
                            "TILE_SIZE": 25
                        }],
                        "dontSave": ["stimuli", ],

                        #other information to save
                        "roundtype": "probe_2afc",
                        "page": pi,
                        "round": ri,
                        "queryround": probeidx, #the n-th asked about this round
                        "navgridname": navgridname,
                        "probegridname": probegridname,
                        "true_color": colororder[0],
                        "mod_color": colororder[1],
                        "probeobs": probeobs,
                    })
                    pi += 1

                    #confidence
                    trialparams.append({
                        #plugin parametersr
                        "type": "CustomItem",
                        "questiontext": "How confident are you?",
                        "responseLabels": [1, 2, 3, 4, "?", 5, 6, 7, 8],
                        "validResponses": [1, 2, 3, 4, 5, 6, 7, 8],
                        "initResponse": "?",
                        "responseEndLabels": ["I guessed", "I'm certain"],
                        "stimuli": [{
                            "type": "gridworld",
                            "gridworldparams": probegrid,
                            "TILE_SIZE": 25
                        }],
                        "dontSave": ["stimuli", ],

                        #other information to save
                        "roundtype": "probe_conf",
                        "page": pi,
                        "round": ri,
                        "queryround": probeidx, #the n-th asked about this round
                        "navgridname": navgridname,
                        "probegridname": probegridname,
                        "true_color": colororder[0],
                        "mod_color": colororder[1],
                        "probeobs": probeobs,
                    })
                    pi += 1
            elif probetype == "awareness":
                probeparams = probetrials[(bi, gidx)]
                probeorder = [probeobs for probeobs, _ in probeparams]
                #create maze-obstacle attention trials
                for probeidx, probeobs in enumerate(probeorder):
                    probegrid = deepcopy(expgrids[navgridname])
                    probegrid['feature_colors'][probeobs] = '#48D1CC' #MediumTurquoise
                    trialparams.append({
                        "type": "GridBlockAttentionQuery",
                        "page": pi,
                        "round": ri,
                        "roundtype": "attentionquery",
                        "queryround": probeidx, #the n-th asked about this round
                        "probegridparams": probegrid,
                        "navgridname": navgridname,
                        "probeobs": probeobs,
                        "questiontext": "How aware of the highlighted obstacle were you at any point?"
                    })
                    pi += 1
            else:
                assert False, "unknown probetype"
        return trialparams

# %% codecell
    #note, there are 8 seeds, so 8 * 2 * 2 = 32 conditions
    seeds = [23199, 27190, 31210, 31290, 31993, 61993, 63993, 67993]
    timelines = []
    for seed, reverse, probetype in product(seeds, [True, False], ['awareness', 'location']):
        maintrials = generateTrialParameters(basegrids, seed=seed, reverse=reverse, probetype=probetype)
        if probetype == "awareness":
            pretask = instructionstraining + awareness_instructions
        elif probetype == 'location':
            pretask = instructionstraining + location_instructions
        timelines.append(pretask+maintrials+posttask)

# %% codecell
    params = {
        "nRounds": nRounds,
        "roundBonusCents": roundBonusCents,
        "EXP_NAME": EXP_NAME
    }
    experiment = {"timelines": timelines, "params": params}
    json.dump(
        experiment,
        open(EXP_CONFIG_FILE, "w"),
        sort_keys=True, indent=4
    )

# %%
if __name__ == "__main__":
    fire.Fire(main)
