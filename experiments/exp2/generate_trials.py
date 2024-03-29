# %% markdown
## Experiment 2 Trials
# %%
import numpy as np
import fire
import random
import pandas as pd
import json
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

    nRounds = 12
    roundBonusCents = 10
    INITIALGOAL_COUNTDOWN_SEC = 60000
    emptygrid = [
        "..........G",
        "...........",
        "...........",
        ".....#.....",
        ".....#.....",
        "...#####...",
        ".....#.....",
        ".....#.....",
        "...........",
        "...........",
        "S.........."
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

                The green square will shrink when you stand still. It will initially shrink slowly, and then shrink quickly once you start moving.

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
                    "G.......000",
                    "..........0",
                    "...........",
                    ".....#.....",
                    ".....#.....",
                    "...#####...",
                    ".....#.....",
                    ".....#.....",
                    "...........",
                    "0..........",
                    "000........"
                ],
                "init_state":[10, 0],
                "absorbing_states":[[0, 10]],
                "name": "trainingA",
                **sharedparams
            },
            "emptygrid": emptygrid,
            "goalCountdown": True,
            "participantStarts": False,
            "INITIALGOAL_COUNTDOWN_SEC": INITIALGOAL_COUNTDOWN_SEC
        },
        {
            "type": "GridNavigation",
            "round": 1,
            "roundtype": "practice",
            "bonus": False,
            "message": """Get to the <span style='background-color: yellow;'>Yellow</span> goal. You cannot go through <br><span style='background-color: black;color: white'>Black</span> or <br><span style='background-color: cornflowerblue; color:white'>Blue</span> tiles.""",
            "taskparams": {
            "feature_array": [
                    "G..........",
                    "...........",
                    "...........",
                    ".....#.....",
                    ".....#..0..",
                    ".00#####000",
                    ".0...#.....",
                    ".0...#.....",
                    "...........",
                    "...........",
                    "..........."
                ],
                "init_state":[10, 0],
                "absorbing_states":[[0, 10]],
                "name": "trainingB",
                **sharedparams
            },
            "emptygrid": emptygrid,
            "goalCountdown": True,
            "participantStarts": False,
            "INITIALGOAL_COUNTDOWN_SEC": INITIALGOAL_COUNTDOWN_SEC
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
                    "G.......000",
                    "..........0",
                    "...........",
                    ".....#.....",
                    ".....#.....",
                    "...#####...",
                    ".....#.....",
                    ".....#.....",
                    "...........",
                    "0..........",
                    "000........"
                ],
                "init_state":[10, 0],
                "absorbing_states":[[0, 10]],
                "name": "trainingA",
                **sharedparams
            },
            "emptygrid": emptygrid,
            "goalCountdown": True,
            "participantStarts": False,
            "hideObstaclesOnMove": True,
            "INITIALGOAL_COUNTDOWN_SEC": INITIALGOAL_COUNTDOWN_SEC
        },
        {
            "type": "GridNavigation",
            "round": 3,
            "roundtype": "practice",
            "bonus": False,
            "message": """The <span style='background-color: cornflowerblue; color:white'>Blue</span> tiles turn invisible.""",
            "taskparams": {
            "feature_array": [
                    "G..........",
                    "...........",
                    "...........",
                    ".....#.....",
                    ".....#..0..",
                    ".00#####000",
                    ".0...#.....",
                    ".0...#.....",
                    "...........",
                    "...........",
                    "..........."
                ],
                "init_state":[10, 0],
                "absorbing_states":[[0, 10]],
                "name": "trainingB",
                **sharedparams
            },
            "emptygrid": emptygrid,
            "goalCountdown": True,
            "participantStarts": False,
            "hideObstaclesOnMove": True,
            "INITIALGOAL_COUNTDOWN_SEC": INITIALGOAL_COUNTDOWN_SEC
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
        },
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
                  "options": ["10 cents", "5 cents", "2 cents", "None"],
                  "required": True,
                  "name": "navBonusCheck"
                },
                {
                  "prompt": "How much of a bonus will you receive for answering the questions about what you paid attention to?",
                  "options": ["10 cents", "5 cents", "2 cents", "None"],
                  "required": True,
                  "name": "memoryBonusCheck"
                }
            ]
        },
    ]
# %% codecell
    posttask = [
          {
            "type": 'survey-text',
            "questions": [
              {
                  "prompt": "How did you answer the attention questions?",
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
    maingridnames = []

    #terminate after 2 steps
    earlyTermDist = [[-2, 0], [2, 0], [0, -2], [0, 2], [1, 1], [-1, 1], [1, -1], [-1, -1]]

    for gridname, trialArray in basegrids.items():
        for tname, trans in transformations.items():
            for earlyTerm in ['full', 'earlyterm']:
                tgridname = f"{gridname}-{tname}-{earlyTerm}"
                maingridnames.append(tgridname)
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

    def generateTrialParameters(basegrids, seed, reverse=False, flipEarlyTerm=False):
        random.seed(seed)
        translations = ['base', 'rot180', 'vflip', 'hflip']
        grididx = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        earlyTerms = ['full', 'earlyterm', 'full', 'earlyterm']

        #block-randomize translations
        alltrans = [deepcopy(translations) for _ in range(int(len(grididx)/len(translations)))]
        for t in alltrans:
            random.shuffle(t)
        alltrans = sum(alltrans, [])

        #block-randomize early termination
        allearlyterms = [deepcopy(earlyTerms) for _ in range(int(len(grididx)/len(earlyTerms)))]
        for et in allearlyterms:
            random.shuffle(et)
        allearlyterms = sum(allearlyterms, [])
        if flipEarlyTerm:
            allearlyterms = [{'full': 'earlyterm', 'earlyterm': 'full'}[et] for et in allearlyterms]

        #randomize grid order
        random.shuffle(grididx)

        rounds = []
        for trans, et, gi in zip(alltrans, allearlyterms, grididx):
            probeorder = ['0', '1', '2', '3', '4', '5', '6']
            random.shuffle(probeorder)
            rounds.append({
                "block": 0,
                "navgridname": f"grid-{gi}-0-{trans}-{et}",
                "probeorder": probeorder
            })

        emptygrid = [
            "..........G",
            "...........",
            "...........",
            ".....#.....",
            ".....#.....",
            "...#####...",
            ".....#.....",
            ".....#.....",
            "...........",
            "...........",
            "S.........."
        ]
        trialparams = []
        if reverse:
            rounds = rounds[::-1]
        pi = 0
        for ri, row in enumerate(rounds):
            #create navigation trial
            trialparams.append({
                "type": "GridNavigation",
                "page": pi,
                "block": row["block"],
                "round": ri,
                "roundtype": "navigation",
                "bonus": True,
                "goalCountdown": True,
                "hideObstaclesOnMove": True,
                "message": "",
                "taskparams": expgrids[row['navgridname']],
                "emptygrid": emptygrid,
                "navgridname": row['navgridname'],
                "INITIALGOAL_COUNTDOWN_SEC": INITIALGOAL_COUNTDOWN_SEC
            })
            pi += 1

            #create maze-obstacle attention trials
            for probeidx, probeobs in enumerate(row['probeorder']):
                probegrid = deepcopy(expgrids[row['navgridname']])
                probegrid['feature_colors'][probeobs] = '#48D1CC' #MediumTurquoise
                trialparams.append({
                    "type": "GridBlockAttentionQuery",
                    "page": pi,
                    "round": ri,
                    "block": row["block"],
                    "roundtype": "attentionquery",
                    "queryround": probeidx, #the n-th asked about this round
                    "probegridparams": probegrid,
                    "navgridname": row['navgridname'],
                    "probeobs": probeobs,
                    "questiontext": "How aware of the highlighted obstacle were you at any point?"
                })
                pi += 1
        return trialparams

# %% codecell
    maintrials = []
    #note, including reversals and flipping of early termination
    #version 1
    maintrials.append(generateTrialParameters(basegrids, seed=9057, reverse=False, flipEarlyTerm=False))
    maintrials.append(generateTrialParameters(basegrids, seed=9057, reverse=True, flipEarlyTerm=False))
    maintrials.append(generateTrialParameters(basegrids, seed=9057, reverse=False, flipEarlyTerm=True))
    maintrials.append(generateTrialParameters(basegrids, seed=9057, reverse=True, flipEarlyTerm=True))

    #version 2
    maintrials.append(generateTrialParameters(basegrids, seed=5031, reverse=False, flipEarlyTerm=False))
    maintrials.append(generateTrialParameters(basegrids, seed=5031, reverse=True, flipEarlyTerm=False))
    maintrials.append(generateTrialParameters(basegrids, seed=5031, reverse=False, flipEarlyTerm=True))
    maintrials.append(generateTrialParameters(basegrids, seed=5031, reverse=True, flipEarlyTerm=True))

    #version 3
    maintrials.append(generateTrialParameters(basegrids, seed=17031, reverse=False, flipEarlyTerm=False))
    maintrials.append(generateTrialParameters(basegrids, seed=17031, reverse=True, flipEarlyTerm=False))
    maintrials.append(generateTrialParameters(basegrids, seed=17031, reverse=False, flipEarlyTerm=True))
    maintrials.append(generateTrialParameters(basegrids, seed=17031, reverse=True, flipEarlyTerm=True))

    #version 4
    maintrials.append(generateTrialParameters(basegrids, seed=61031, reverse=False, flipEarlyTerm=False))
    maintrials.append(generateTrialParameters(basegrids, seed=61031, reverse=True, flipEarlyTerm=False))
    maintrials.append(generateTrialParameters(basegrids, seed=61031, reverse=False, flipEarlyTerm=True))
    maintrials.append(generateTrialParameters(basegrids, seed=61031, reverse=True, flipEarlyTerm=True))

    #version 5
    maintrials.append(generateTrialParameters(basegrids, seed=13021, reverse=False, flipEarlyTerm=False))
    maintrials.append(generateTrialParameters(basegrids, seed=13021, reverse=True, flipEarlyTerm=False))
    maintrials.append(generateTrialParameters(basegrids, seed=13021, reverse=False, flipEarlyTerm=True))
    maintrials.append(generateTrialParameters(basegrids, seed=13021, reverse=True, flipEarlyTerm=True))
# %% codecell
    timelines = [instructionstraining+mt+posttask for mt in maintrials]
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
