import {makeid, FailedAttentionCheckException, errors, isNumber} from "./exputils.js"

//Global variables
window.timeline;
window.psiturk = new PsiTurk(uniqueId, adServerLoc, mode);
window.searchParams = new URLSearchParams(location.search);
window.globalExpStore = {};
window.globalExpStore.sessionId = makeid(10);
window.globalExpStore.bonusDollars = 0;
window.globalExpStore.contactEmail = 'mho@princeton.edu' //default
window.onload = main

async function main () {
    $("body").append(`
        <div id="experiment" class="jspsych-display-element" style="max-width: 800px; margin: auto; margin-top: 15vh;"></div>
        `)
    $(".jspsych-display-element").css("overflow-y", "visible"); //get rid of annoying sidebar
    $("#experiment").html(`
        <div id='welcome-message' class='jspsych-content'>
            <h1>Welcome</h1>
            <p>Thanks for participating!
            <p>Please wait while we load the experiment.
        </div>
        <div id="load-icon"></div>
    `)
    window.onbeforeunload = function (e) {
        psiturk.saveData();
        let message = "Please do not leave before completing.";
        e = e || window.event;
        if (e) { // For IE and Firefox
          e.returnValue = message;
        }
        return message // For Safari
    };

    errors.setHandler(async (e) => {
        console.log('Error in experiment', e);
        if (e instanceof FailedAttentionCheckException) {
            await handleAttentionCheckFailure(e, "experiment")
        } else {
            await handleExperimentError(e, "experiment")
        }
    })
    await errors.handle(runExperiment)("experiment")
    await errors.handle(wrapUp)("experiment")
    await errors.handle(endSuccessfully)("experiment")
}

async function runExperiment(display_element) {
    /* Load exp configuration file */
    let CONFIG_FILE = searchParams.get("CONFIG_FILE") || "config.json.zip";
    let CONFIG_LOCATION = "./static/config/"+CONFIG_FILE;
    let config;
    console.log("Loading configuration from: " + CONFIG_LOCATION)
    if (CONFIG_FILE.split(".").slice(-1)[0] === "zip") {
        let config_binary = await new Promise((resolve, reject) => {
            JSZipUtils.getBinaryContent(CONFIG_LOCATION, function(err, data) {
                if (err) {
                    reject(err);
                } else {
                    resolve(data);
                }
            });
        });
        config = await JSZip.loadAsync(config_binary);
        config = await config.file("config.json").async("string")
        config = JSON.parse(config) ;
    }
    else {
        config = await fetch(CONFIG_LOCATION);
        config = await config.json()
    }

    console.log("Experiment Parameters:")
    console.log(config['params'])

    /* Set up timeline and global parameters*/
    let page = parseInt(searchParams.get('page') || 0);
    let condition = parseInt(searchParams.get('condition') || window.condition) || 0;
    window.timeline = config['timelines'][condition].slice(page);
    window.globalExpStore = Object.assign(window.globalExpStore, config.params);
    window.globalExpStore.condition = condition;
    window.globalExpStore.page = page;

    psiturk.preloadImages(config.preloadImages || [])

    /* Miscellaneous things */
    await new Promise(resolve => psiturk.saveData({error: resolve, success: resolve}))
    $("#welcome").hide();

    /* Run the timeline */
    await new Promise(resolve => {
        jsPsych.init({
            timeline: window.timeline,
            display_element: display_element,
            exclusions: {
                min_width: 800,
                min_height: 600
            },
            experiment_width: 800,
            on_data_update: errors.handle(async (data) => {
                if (!isNumber(window.globalExpStore.bonusDollars)) {
                    throw new Error("Bonus is not a number")
                }
                psiturk.recordTrialData(data);
            }),
            on_finish: () => {
                resolve()
            }
        })
    })
};

async function wrapUp (display_element) {
    if (window.location.pathname === "/testexperiment") {
        $("#"+display_element).html(`
            <div id='error' class='jspsych-content'>
                Recorded data:
                <pre style="text-align:left; text-indent:0">${JSON.stringify(JSON.parse(jsPsych.data.get().json()), null, 2)}</pre>
            </div>
        `)
        return
    }

    /* Save trial data */
    $("#"+display_element).html('<div id="load-icon"></div><div>Saving data...</div>');
    psiturk.recordUnstructuredData("bonusDollars", window.globalExpStore.bonusDollars);
    let saved = false;
    let attempts = 1;
    let TIMEOUT_MS = 30000;
    while (!saved) {
        saved = await new Promise(resolve => {
            let timeout = setTimeout(() => resolve(false), TIMEOUT_MS);
            psiturk.saveData({
                error: () => {
                    clearTimeout(timeout);
                    resolve(false);
                },
                success: () => {
                    clearTimeout(timeout);
                    resolve(true)
                }
            })
        })
        attempts += 1;
        $("#"+display_element).html(`<div id="load-icon"></div><div>Saving data... (Attempt ${attempts})</div>`);
    }

    await new Promise(resolve => psiturk.computeBonus("\compute_bonus", resolve))
}

async function endSuccessfully(display_element) {
    await new Promise(resolve => $.get(`worker_complete?uniqueId=${uniqueId}`, resolve))
    if (window.globalExpStore.recruitment_platform === "prolific") {
        $("#"+display_element).html(`
            <div class='jspsych-display-element'>
                <h1>Study complete</h1>

                <p>
                Your completion code is <b>3AF5D4D6</b>
                Click this link to submit<br>
                <a href=https://app.prolific.co/submissions/complete?cc=3AF5D4D6>
                    https://app.prolific.co/submissions/complete?cc=3AF5D4D6
                </a>
                <p>
                If you have problems submitting, please contact
                <a href="mailto:${window.globalExpStore.contactEmail}">${window.globalExpStore.contactEmail}</a>
            </div>
        `)
    }
    else if (window.globalExpStore.recruitment_platform === "mturk") {
        psiturk.completeHIT();
    }
    else {
        $("#"+display_element).html(`
            <div class='jspsych-display-element'>
                <h1>Study complete</h1>
                <p>
                If you have problems submitting, please contact
                <a href="mailto:${window.globalExpStore.contactEmail}">${window.globalExpStore.contactEmail}</a>
                </p>
            </div>
        `)
    }
    window.onbeforeunload = () => {};
}

/* ERROR HANDLING */
async function handleExperimentError(e, display_element) {
    let msg = "Error"
    if (e.stack) {
        msg = e.stack;
    } else if (e.name != null) {
        msg = e.name;
        if (e.message) {
            msg += ': ' + e.message;
        }
    } else {
        msg = e;
    }
    let message = `
        <pre style="text-align:left; text-indent:0">
        HitID: ${(typeof hitId !== "undefined" && hitId !== null ? hitId[0] : 'N/A')}
        AssignmentId: ${(typeof assignId !== "undefined" && assignId !== null ? assignId : 'N/A')}
        WorkerId: ${(typeof workerId !== "undefined" && workerId !== null ? workerId[0] : 'N/A')}
        SessionId: ${(typeof window.globalExpStore.sessionId !== "undefined" ? window.globalExpStore.sessionId : 'N/A')}

        ${msg}
        </pre>
    `.split("        ").join("")
    $("#" + display_element).html(`
        <div id='error' class='jspsych-content'>
            <h1>Error</h1>

            ${message}

            <p><a href="mailto:${window.globalExpStore.contactEmail}?subject=Error in experiment&body=${encodeURIComponent(message)}">Click here</a> to report the error by email. Then click the button below to exit. Thank you!</p>

            <button id="submit">Exit</button>
        </div>
    `)
    await new Promise(resolve => $("#submit").click(resolve))
    await wrapUp("experiment")
    window.onbeforeunload = () => {};
}

async function handleAttentionCheckFailure(e, display_element) {
    $("#"+display_element).html(e.message);
    await new Promise(resolve => setTimeout(resolve, 2000))
    await wrapUp("experiment")
    if (typeof e.redirectLink !== "undefined") {
        window.onbeforeunload = () => {};
        window.location.href = e.redirectLink;
    }
}
