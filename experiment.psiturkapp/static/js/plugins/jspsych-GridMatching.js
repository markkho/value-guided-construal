import {GridWorldTask} from "../gridworld/gridworld-task.js"
import {errors} from "../exputils.js"

// Plugin for choosing between two grids which one was just done
// Example parameters:
// var gridmatch_block = {
//     type: "GridMatching",
//     round: 0,
//     roundtype: "practice",
//     left: gridParams1,
//     right: gridParams2
// }
jsPsych.plugins["GridMatching"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'GridMatching',
        parameters: {}
    };

    plugin.trial = errors.handle(async function(display_element, trial) {
        trial.MINRESPONSETIME_MS = trial.MINRESPONSETIME_MS || 1000
        console.log(trial);

        const startTime = Date.now();
        display_element.innerHTML = `<div id="messages"></div>
        <div style="width: 50%; float:left;" id="leftpanel">
            <div id="leftgrid"></div>
            <div style="font-size:50px" id="leftarrow">&#x2190;</div>
        </div>
        <div style="width: 50%; float:right;" id="rightpanel">
            <div id="rightgrid"></div>
            <div style="font-size:50px" id="rightarrow">&#x2192;</div>
        </div>`;
        if (trial.guessoption) {
            display_element.innerHTML += `<div id="guesspanel">
                <div style='font-size: 25px' id="guessarrow">Press <b>spacebar</b> if you can only guess.</div>
                </div>`
        }
        let leftdiv= $("#leftgrid")[0];
        let left = new GridWorldTask({
            container: leftdiv,
            TILE_SIZE: trial.TILE_SIZE || 25,
        })
        let rightdiv= $("#rightgrid")[0];
        let right = new GridWorldTask({
            container: rightdiv,
            TILE_SIZE: trial.TILE_SIZE || 25,
        })
        let msgdiv = $("#messages")[0];
        $(msgdiv).html("Which maze did you just do? (use arrow keys)");
        left.init(trial.left);
        right.init(trial.right);

        let validkeys = [37, 39];
        if (trial.guessoption) {
            validkeys.push(32)
        }
        setTimeout(() => {
            $(document).on("keydown.response", (e) => {
                let kc = e.keyCode ? e.keyCode : e.which;
                if (!validkeys.includes(kc)) {
                    return
                }
                e.preventDefault();
                $(document).off("keydown.response");
                let response = {32: "guess", 37: "left", 39: "right"}[kc];
                $(`#${response}panel`).css("border-style", "solid");
                $(`#${response}panel`).css("border-color", "green");
                $(`#${response}arrow`).css("color", "green");
                let trialData = {
                    response,
                    sessionId: window.globalExpStore.sessionId,
                    type : trial.type,
                    round: trial.round,
                    roundtype: trial.roundtype,
                    left: trial.left,
                    right: trial.right,
                    starttime: startTime,
                    responsetime: Date.now()
                }
                display_element.innerHTML = '';
                jsPsych.finishTrial({data: trialData})
            });
        }, trial.MINRESPONSETIME_MS)
    });
    return plugin;
})();
