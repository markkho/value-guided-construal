import {errors} from "../exputils.js"
// Plugin for choosing between two grids which one was just done
// Example parameters:
// var gridmatch_confidence = {
//     type: "GridMatchConfidence",
//     round: 0,
//     roundtype: "practice",
//     left: gridParams1,
//     right: gridParams2
// }
jsPsych.plugins["GridMatchConfidence"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'GridMatchConfidence',
        parameters: {}
    };

    plugin.trial = errors.handle(async function(display_element, trial) {
        console.log(trial);
        const startTime = Date.now();
        display_element.innerHTML = `<div id="messages">How confident are you?</div>
        <br>
        <div style="font-size:200%">
            <span style="font-size: 50%"> I guessed </span>
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
            <span style="font-size: 50%"> I'm certain </span>
		</div>
        <br>
        <br>
        <div id="postmessage" style="font-size:75%">Use the &#x2190; and &#x2192; keys to make your selection, then press <b>spacebar</b></div>
        `;

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
	            let trialData = {
	            	response: $(`#resp_${respstr}`).text(),
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
            }
        });
    });

    return plugin;
})();
