import {errors} from "../exputils.js"
jsPsych.plugins["CustomInstructions"] = (function() {
	//parameters: instructions, continue_wait_time, continue_keys
    var plugin = {};
    plugin.info = {
        name: 'CustomInstructions',
        parameters: {}
    };
    plugin.trial = errors.handle(async function(display_element, trial) {
        const startTime = Date.now();
        //default values for trial
        trial = Object.assign({
            instructions: "<div></div>",
        	continue_wait_time: 5000,
        	render_markdown: true,
            auto_continue: false
        }, trial)

        if (typeof(trial.preContinueFunc) === 'undefined') {
            // promise that needs to be fulfilled before continue button appears
            trial.preContinueFunc = () => new Promise(resolve => setTimeout(resolve, trial.continue_wait_time))
        }

        display_element.innerHTML = trial.instructions;
        trial.preContinueFunc()
        .then(() => {
            if (trial.auto_continue) {
                display_element.innerHTML = '';
                jsPsych.finishTrial();
            }
            else {
                display_element.innerHTML += "<div>Press <b>spacebar</b> to continue.</div>"
                $(document).on("keydown.continue", (e) => {
                    let kc = e.keyCode ? e.keyCode : e.which;
                    if (kc !== 32) {
                        return
                    }
                    e.preventDefault();
                    $(document).off("keydown.continue");
                    display_element.innerHTML = '';
                    jsPsych.finishTrial({data: {
                        type: "instructions",
                        name: trial.name,
                        responseTime: Date.now() - startTime
                    }})
                });
            }
        })
    });

    return plugin;
})();
