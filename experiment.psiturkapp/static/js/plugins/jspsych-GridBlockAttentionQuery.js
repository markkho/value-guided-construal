// Plugin for choosing between two grids which one was just done
// Example parameters:
// var params = {
//     type: "GridBlockAttentionQuery",
//     round: 0,
//     roundtype: "practice",
//	   queryround: 1, //the n-th asked about this round
//     probegridparams: gridparams,
//	   probeobs: 5
// }
import {GridWorldTask} from "../gridworld/gridworld-task.js"
import {errors} from "../exputils.js"

jsPsych.plugins["GridBlockAttentionQuery"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'GridBlockAttentionQuery',
        parameters: {}
    };

    plugin.trial = errors.handle(async function(display_element, trial) {
        if (typeof(trial.questiontext) === 'undefined') {
            trial.questiontext = "During the trial, how aware of the highlighted obstacle were you?";
        }
        if (typeof(trial.responselabels) === 'undefined') {
            trial.responselabels = [" Not at all ", " A lot "]
        }
        const startTime = Date.now();
        display_element.innerHTML = `<div id="messages">${trial.questiontext}</div>
        <div id="gridpanel">
            <div id="probegrid"></div>
        </div>
        <br>
        <div style="font-size:200%">
            <span style="font-size: 50%">${trial.responselabels[0]}</span>
            <span id="resp_-4" class="resp">1</span>
            <span> &nbsp; </span>
            <span id="resp_-3" class="resp">2</span>
            <span> &nbsp; </span>
		    <span id="resp_-2" class="resp">3</span>
		    <span> &nbsp; </span>
		    <span id="resp_-1" class="resp">4</span>
		    <span style="font-size: 80%"> &nbsp; ? &nbsp; </span>
		    <span id="resp_1" class="resp">5</span>
		    <span> &nbsp; </span>
		    <span id="resp_2" class="resp">6</span>
            <span> &nbsp; </span>
            <span id="resp_3" class="resp">7</span>
            <span> &nbsp; </span>
            <span id="resp_4" class="resp">8</span>
            <span style="font-size: 50%">${trial.responselabels[1]}</span>
		</div>
        <br>
        <br>
        <div id="postmessage" style="font-size:70%">Use the &#x2190; and &#x2192; keys to make your selection, then press <b>spacebar</b></div>
        `;

        let grid = new GridWorldTask({
            container: $("#probegrid")[0],
            TILE_SIZE: trial.TILE_SIZE || 25,
        })
        grid.init(trial.probegridparams);

        let validkeys = [37, 39];
        if (trial.guessoption) {
            validkeys.push(32)
        }
        let resp = 0;
        $(document).on("keydown.response", (e) => {
            let kc = e.keyCode ? e.keyCode : e.which;
            if (![32, 37, 39].includes(kc)) {
            	return
            }
            if (resp === 0 && kc === 32) {
            	return
            }
            if ([37, 39].includes(kc)){
	            e.preventDefault();
            	let dx = {37: -1, 39: 1}[kc];
            	resp = Math.max(Math.min(resp + dx, 4), -4);
	        	let respstr = `${{"-1": '-', "1": '', "0": ""}[Math.sign(resp)]}${Math.abs(resp)}`;
	            $(`.resp`).css("border-style", "none");
	            $(`#resp_${respstr}`).css("border-style", "solid");
	            $(`#resp_${respstr}`).css("border-color", "green");
            	return
            }
            if (kc === 32) {
	            e.preventDefault();
	            $(document).off("keydown.response");
	        	let respstr = `${{"-1": '-', "1": '', "0": ""}[Math.sign(resp)]}${Math.abs(resp)}`;
                let trialData = Object.assign(
                    {},
                    trial,
                    { //parameters to ignore
                        "probegridparams": "",
                    },
                    { //data from trial
                        sessionId: window.globalExpStore.sessionId,
                        starttime: startTime,
                        responsetime: Date.now(),
                        response: $(`#resp_${respstr}`).text(),
                    }
                )
                display_element.innerHTML = '';
                jsPsych.finishTrial({data: trialData})
            }
        });
    });

    return plugin;
})();

jsPsych.plugins["CustomItem"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'CustomItem',
        parameters: {}
    };

    plugin.trial = errors.handle(async function(display_element, trial) {
        trial = Object.assign({ //defaults
            questiontext: "How much of a thing?",
            responseLabels: [1, 2, 3, 4, "?", 5, 6, 7, 8],
            validResponses: [1, 2, 3, 4, 5, 6, 7, 8],
            initResponse: "?",
            responseEndLabels: [" Not at all ", " A lot "],
            stimuli: [{
                type: "gridworld",
                gridworldparams: {
                    "feature_array": [
                        "............S",
                        "....2........",
                        "....2....1...",
                        "....22#.11...",
                        ".....E#..1..B",
                        "...EEE#....BB",
                        "C..#######0.B",
                        "C.....#...000",
                        "CC4...#......",
                        "444...#...DD.",
                        "...........DD",
                        "......33.A...",
                        "G......33AAA."
                    ],
                    "feature_colors": {
                        "#": "black",
                        "0": "#DCCB5D",
                        "A": "#44A9A0"
                    },
                },
                TILE_SIZE: 25
            }],
            dontSave: ["stimuli", ]
        }, trial)

        const startTime = Date.now();
        let pageElements = [];
        pageElements.push(`<div id="messages">${trial.questiontext}</div>`)
        pageElements.push(`<div id="itemdisplay"></div>`)
        pageElements.push(`<br>`)
        pageElements.push(`<div style="font-size:200%">`)
        pageElements.push(`<span style="font-size: 50%">${trial.responseEndLabels[0]}</span><span> &nbsp; </span>`)
        pageElements.push(...trial.responseLabels.map((label, resp_i) => {
            return `<span id="resp_${resp_i}" class="resp">${label}</span><span> &nbsp; </span>`
        }))
        pageElements.push(`<span style="font-size: 50%">${trial.responseEndLabels[1]}</span>`)
        pageElements.push('</div>')
        pageElements.push('</div>')
        pageElements.push(`<br>
                           <br>
                           <div id="postmessage" style="font-size:70%">Use the &#x2190; and &#x2192; keys to make your selection, then press <b>spacebar</b></div>`)
        display_element.innerHTML = pageElements.join("")

        // set up stimuli
        for (let si = 0; si < trial.stimuli.length; si++) {
            let sparams = trial.stimuli[si];
            if (sparams.type === "gridworld") {
                $("#itemdisplay").append(`<span id="stimulus_${si}"></span>`)
                let grid = new GridWorldTask({
                    container: $(`#stimulus_${si}`)[0],
                    TILE_SIZE: sparams.TILE_SIZE || 25,
                })
                grid.init(sparams.gridworldparams);
            }
        }

        let movekeys = [37, 39];
        let submitkey = 32;
        let initRespIndex = trial.responseLabels.indexOf(trial.initResponse)
        let validRespIndices = trial.validResponses.map((r) => trial.responseLabels.indexOf(r));
        let respIndex = initRespIndex;
        $(document).on("keydown.response", (e) => {
            let kc = e.keyCode ? e.keyCode : e.which;
            if (![32, 37, 39].includes(kc)) {
                return
            }
            if (!validRespIndices.includes(respIndex) && kc === 32) {
                return
            }
            if ([37, 39].includes(kc)){
                e.preventDefault();
                let dx = {37: -1, 39: 1}[kc];
                respIndex = Math.max(Math.min(respIndex + dx, trial.responseLabels.length - 1), 0);
                let respstr = `#resp_${respIndex}`;
                $(`.resp`).css("border-style", "none");
                if (validRespIndices.includes(respIndex)){
                    $(respstr).css("border-style", "solid");
                    $(respstr).css("border-color", "green");
                }
                return
            }
            if (kc === 32) {
                e.preventDefault();
                $(document).off("keydown.response");
                let resp = $(`#resp_${respIndex}`).text();
                let trialData = Object.assign(
                    {},
                    trial,
                    //parameters to ignore
                    Object.fromEntries(trial.dontSave.map((n) => [n, ""])),
                    { //data from trial
                        sessionId: window.globalExpStore.sessionId,
                        starttime: startTime,
                        responsetime: Date.now(),
                        response: resp,
                    }
                )
                display_element.innerHTML = '';
                jsPsych.finishTrial({data: trialData})
            }
        });
    });

    return plugin;
})();
