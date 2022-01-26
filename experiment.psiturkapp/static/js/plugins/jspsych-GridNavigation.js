import {GridWorldTask} from "../gridworld/gridworld-task.js"
import {errors} from "../exputils.js"

jsPsych.plugins["GridNavigation"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'GridNavigation',
        parameters: {}
    };

    plugin.trial = errors.handle(async function(display_element, trial) {
        console.log(trial);
        const startTime = Date.now();
        display_element.innerHTML = '<div id="messages"></div><div id="gridworld"></div>';
        let taskdiv = $("#gridworld")[0];
        let msgdiv = $("#messages")[0];
        let trialnum = 0;
        let addToBonus = typeof(trial.bonus) !== "undefined" ? trial.bonus : true;
        trial.goalCountdown = typeof(trial.goalCountdown) === "undefined" ? false : trial.goalCountdown;
        trial.hideObstaclesOnMove = typeof(trial.hideObstaclesOnMove) === "undefined" ? false : trial.hideObstaclesOnMove;
        trial.message = trial.message || "&nbsp;";
        trial.INITIALGOAL_COUNTDOWN_SEC = trial.INITIALGOAL_COUNTDOWN_SEC || 5000;
        trial.GOAL_COUNTDOWN_SEC = trial.GOAL_COUNTDOWN_SEC || 1000;
        trial.GOALSIZE = trial.GOALSIZE || .4;
        trial.TILE_SIZE = trial.TILE_SIZE || 50
        trial.OBJECT_ANIMATION_TIME = trial.OBJECT_ANIMATION_TIME || 50
        let trialData = [];

        //goal animation countdown
        let goalobj, goalanim;
        let goalloc = trial.taskparams['absorbing_states'][0];
        let bonusTime = true;
        let getFullGoalParams = (painter) => {
            let offset = (1 - trial.GOALSIZE)/2
            return {
                x : (goalloc[0]+offset)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
                y : painter.y_to_h(goalloc[1] - offset)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
                width : painter.TILE_SIZE*trial.GOALSIZE,
                height : painter.TILE_SIZE*trial.GOALSIZE,
            }
        }
        let getEmptyGoalParams = (painter) => {
            return {
                x: (goalloc[0]+.5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
                y: painter.y_to_h(goalloc[1] - .5)*painter.TILE_SIZE+painter.DISPLAY_BORDER,
                width : 0,
                height : 0,
            }
        }
        let initGoal = (painter) => {
            let fullGoalParams = getFullGoalParams(painter);
            goalobj = painter.paper.add([
                Object.assign(
                {
                    type: "rect",
                    fill : 'green',
                    stroke: 'white',
                    "stroke-width": 1
                },
                fullGoalParams
                )
            ]);
            goalanim = goalobj.animate(getEmptyGoalParams(painter), trial.INITIALGOAL_COUNTDOWN_SEC, "linear", () => {bonusTime = false})
        }
        let resetGoal = (painter) => {
            if (!bonusTime) {
                return
            }
            goalanim.stop();
            goalobj.attr(getFullGoalParams(painter))
            goalanim = goalobj.animate(getEmptyGoalParams(painter), trial.GOAL_COUNTDOWN_SEC, "linear", () => {bonusTime = false})
        }

        //hiding obstacles
        let hideObstacles = (task) => {
            task.painter.tiles.filter((t) => {
                let s = t['grid_xy'];
                return ['0', '1', '2', '3', '4', '5', '6'].includes(task.mdp.state_features[s])
            }).map((t) => {
                t.attr('fill', 'white')
            })
        }

        let task = new GridWorldTask({
            container: taskdiv,
            step_callback: (d) => {
                if (trial.goalCountdown){
                    resetGoal(task.painter);
                }
                if (trial.hideObstaclesOnMove) {
                    if (trialnum == 0) {
                        hideObstacles(task);
                    }
                }
                d.type = trial.type;
                d.round = trial.round;
                d.roundtype = trial.roundtype;
                d.gridname = trial.taskparams.name;
                d.trialnum = trialnum;
                d.sessionId = window.globalExpStore.sessionId;
                trialnum += 1;
                trialData.push(d);
            },
            endtask_callback: () => {
                setTimeout(function() {
                    if (addToBonus && bonusTime) {
                        window.globalExpStore.bonusDollars += window.globalExpStore.roundBonusCents/100;
                        console.log("bonus!")
                    }
                    else {
                        console.log("no bonus :(")
                    }
                    display_element.innerHTML = '';
                    jsPsych.finishTrial({data: trialData})
                }, trial.ENDTASK_TIMEOUT || 0);
            },
            TILE_SIZE: trial.TILE_SIZE,
            OBJECT_ANIMATION_TIME: trial.OBJECT_ANIMATION_TIME
        });

        trial.participantStarts = typeof(trial.participantStarts) === 'undefined' ? true : trial.participantStarts
        window.task = task;
        if (trial.participantStarts) {
            $(msgdiv).html("Press <u>space</u> to begin the round.");
            let gridheight = trial.taskparams['feature_array'].length;
            let gridwidth = trial.taskparams['feature_array'][0].length;
            let row = '.'.repeat(gridwidth);
            trial.emptygrid = trial.emptygrid || Array(gridheight).fill(row);
            task.init({feature_array: trial.emptygrid});

            //press space to start task
            $(document).on("keydown.start_task", (e) => {
                let kc = e.keyCode ? e.keyCode : e.which;
                if (kc !== 32) {
                    return
                }
                e.preventDefault();
                $(document).off("keydown.start_task");
                $(msgdiv).html(trial.message);
                task.init(trial.taskparams);
                task.start();
                if (trial.goalCountdown){
                    initGoal(task.painter);
                }
            });
        }
        else {
            task.init(trial.taskparams);
            task.start();
            if (trial.goalCountdown){
                initGoal(task.painter);
            }
        }
    });

    return plugin;
})();
