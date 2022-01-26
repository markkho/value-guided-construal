import {GridWorldTask} from "../gridworld/gridworld-task.js"
import {errors} from "../exputils.js"

jsPsych.plugins["GridWatchDot"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'GridWatchDot',
        parameters: {}
    };
    function createEmptyGridParams(taskparams) {
        return Object.assign(
            {},
            taskparams,
            {
                feature_colors: {
                    "#": taskparams.feature_colors["#"],
                    ".": taskparams.feature_colors["."],
                },
                init_state: undefined
            }
        )
    }

    plugin.trial = errors.handle(async function(display_element, trial) {
        let trialparams = Object.assign({
            dotAppearances: [
                {
                    x: 0,
                    y: 4,
                    time_ms: 3000,
                    duration_ms: 1000
                }
            ],
            catchBonusDollars: .1,
            GOALSIZE: .4,
            INITIALGOAL_COUNTDOWN_SEC: 60000,
            TRIAL_DURATION_MS: 10000,
            DOT_RADIUS: .1,
            TILE_SIZE: 50
        }, trial.trialparams)
        trialparams.nDots = trialparams.dotAppearances.length;
        console.log(trialparams);
        let taskparams = trial.taskparams;
        let trialData = {
            trialparams,
            taskparams,
            sessionId: window.globalExpStore.sessionId,
            dotCatches: 0,
            dotMisfires: 0,
            datatype: "trialData"
        }
        window.trialData = trialData;

        display_element.innerHTML = '<div id="messages"></div><div id="gridworld"></div>';
        let task = new GridWorldTask({
            container: $("#gridworld")[0],
            TILE_SIZE: trialparams.TILE_SIZE
        });
        window.task = task;

        //initialize empty grid and wait for participant to press space
        $("#messages").html("Press spacebar to start")
        task.init(createEmptyGridParams(taskparams))
        let xy_to_node = {};
        task.painter.tiles.map((t) => {
            let f = task.mdp.state_features[t.grid_xy];
            xy_to_node[t.grid_xy] = t.node;
        })
        await new Promise(resolve => {
            $(document).on("keydown.starttask", (e) => {
                let kc = e.keyCode ? e.keyCode : e.which;
                if (kc !== 32) {
                    return
                }
                $(document).off("keydown.starttask");
                $("#messages").html("&nbsp;")
                // task.init(taskparams)
                initialize_grid()
                resolve()
            });
        });

        //start the trial
        setTimeout(activateNoDotListener, 1000);
        setTimeout(endTrial, trialparams.TRIAL_DURATION_MS)
        for (let i = 0; i < trialparams.dotAppearances.length; i++) {
            let dotparams = trialparams.dotAppearances[i];
            setTimeout(createDotCallback(dotparams), dotparams.time_ms)
        }

        //functions
        function initialize_grid() {
            let sf = task.mdp.state_features;
            let goalLoc = Object.keys(sf).filter(k => sf[k] === "G")[0];
            task.init(taskparams)
            let goalTile = task.painter.tiles.filter(t => t.grid_xy.join(",") === goalLoc)[0];
            let offset = trialparams.TILE_SIZE*(1 - trialparams.GOALSIZE)/2
            let goalObj = task.painter.paper.add([{
                x: goalTile.attrs.x + offset,
                y: goalTile.attrs.y + offset,
                width: trialparams.TILE_SIZE*trialparams.GOALSIZE,
                height: trialparams.TILE_SIZE*trialparams.GOALSIZE,
                type: "rect",
                fill : 'green',
                stroke: 'white',
                "stroke-width": 1
            }])
            goalObj.animate({
                x: goalTile.attrs.x + .5*trialparams.TILE_SIZE,
                y: goalTile.attrs.y + .5*trialparams.TILE_SIZE,
                width: 0,
                height: 0
            }, trialparams.INITIALGOAL_COUNTDOWN_SEC, 'linear')
        }

        function endTrial() {
            console.log(trialData)
            let caughtAllDots = trialparams.nDots === trialData.dotCatches;
            if (caughtAllDots && (trialData.dotMisfires=== 0)) {
                window.globalExpStore.bonusDollars += trialparams.catchBonusDollars
            }
            deactivateListeners()
            display_element.innerHTML = '';
            jsPsych.finishTrial({data: trialData})
        }
        function createDotCallback(dotparams) {
            let response = Object.assign({}, dotparams);
            function showDot() {
                activateDotListener();
                let node = xy_to_node[[dotparams.x, dotparams.y]];
                let dot = task.painter.paper.circle(
                    parseInt(node.getAttribute("x")) + parseInt(node.getAttribute("width"))/2,
                    parseInt(node.getAttribute("y")) + parseInt(node.getAttribute("height"))/2,
                    trialparams.DOT_RADIUS*trialparams.TILE_SIZE
                )
                dot.attr("fill", "red")
                dot.attr("stroke-width", "0")
                setTimeout(() => {
                    dot.remove()
                    activateNoDotListener();
                }, dotparams.duration_ms);
            }
            return showDot
        }
        function activateNoDotListener() {
            $(document).off("keydown.dot_active");
            $(document).on("keydown.dot_inactive", (e) => {
                let kc = e.keyCode ? e.keyCode : e.which;
                if (kc !== 32) {
                    return
                }
                trialData.dotMisfires += 1;
            });
        }
        function activateDotListener() {
            $(document).off("keydown.dot_inactive");
            $(document).on("keydown.dot_active", (e) => {
                let kc = e.keyCode ? e.keyCode : e.which;
                if (kc !== 32) {
                    return
                }
                trialData.dotCatches += 1;
                $(document).off("keydown.dot_active");
            });
        }
        function deactivateListeners() {
            $(document).off("keydown.dot_inactive");
            $(document).off("keydown.dot_active");
        }
    });

    return plugin;
})();

jsPsych.plugins["GridNavBreadcrumbs"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'GridNavBreadcrumbs',
        parameters: {}
    };
    function createEmptyGridParams(taskparams) {
        return Object.assign(
            {},
            taskparams,
            {
                feature_colors: {
                    "#": taskparams.feature_colors["#"],
                    ".": taskparams.feature_colors["."],
                },
                init_state: undefined
            }
        )
    }

    plugin.trial = errors.handle(async function(display_element, trial) {
        let trialparams = Object.assign({
            breadCrumbs: [
                {x: 1, y: 0},
                {x: 2, y: 2},
                {x: 3, y: 4},
                {x: 2, y: 8},
                {x: 3, y: 8},
            ],
            participantStarts: true,
            message: "&nbsp;",
            roundBonusCents: .1,
            CRUMB_SIZE: .05,
            MAX_TIMESTEPS: 1e10,
            GOALSIZE: .4,
            TILE_SIZE: 50,
            OBJECT_ANIMATION_TIME: 50,
            INITIALGOAL_COUNTDOWN_SEC: 5000,
            GOAL_COUNTDOWN_SEC: 1000,
            GOALSIZE: .4
        }, trial.trialparams)
        console.log(trialparams);
        let taskparams = trial.taskparams;
        let trialData = {
            trialparams,
            taskparams,
            sessionId: window.globalExpStore.sessionId,
            navigationData: [],
            allCollected: false,
            datatype: "trialData"
        }
        window.trialData = trialData;

        const startTime = Date.now();
        display_element.innerHTML = '<div id="messages"></div><div id="gridworld"></div>';
        let crumb, goalObj, all_crumbs;
        let task = setupTask()
        $("#messages").html("Press spacebar to start")
        task.init(createEmptyGridParams(taskparams))
        await new Promise(resolve => {
            $(document).on("keydown.starttask", (e) => {
                let kc = e.keyCode ? e.keyCode : e.which;
                if (kc !== 32) {
                    return
                }
                $(document).off("keydown.starttask");
                resolve()
            });
        });
        $("#messages").html(trialparams.message)
        task.init(taskparams);
        goalObj = setupGoal(task)
        all_crumbs = setupBreadcrumbElements(trialparams.breadCrumbs, task)
        crumb = all_crumbs[0]
        crumb.show();
        task.start();

        function setupGoal(task) {
            let sf = task.mdp.state_features;
            let goalLoc = Object.keys(sf).filter(k => sf[k] === "G")[0];
            let goalTile = task.painter.tiles.filter(t => t.grid_xy.join(",") === goalLoc)[0];
            let offset = trialparams.TILE_SIZE*(1 - trialparams.GOALSIZE)/2
            let fullParams = {
                x: goalTile.attrs.x + offset,
                y: goalTile.attrs.y + offset,
                width: trialparams.TILE_SIZE*trialparams.GOALSIZE,
                height: trialparams.TILE_SIZE*trialparams.GOALSIZE,
                type: "rect",
                fill : 'green',
                stroke: 'white',
                "stroke-width": 1
            }
            let doneParams = {
                x: goalTile.attrs.x + .5*trialparams.TILE_SIZE,
                y: goalTile.attrs.y + .5*trialparams.TILE_SIZE,
                width: 0,
                height: 0
            }
            let goalObj = task.painter.paper.add([fullParams])
            let goalAnim;
            let goalGone = false;
            goalAnim = goalObj.animate(doneParams, trialparams.INITIALGOAL_COUNTDOWN_SEC, 'linear', () => (goalGone = true))
            goalObj.resetGoal = () => {
                if (goalGone) {
                    return false
                }
                goalAnim.stop()
                goalObj.attr(fullParams)
                goalAnim = goalObj.animate(doneParams, trialparams.GOAL_COUNTDOWN_SEC, "linear", () => (goalGone = true))
                return true
            }
            return goalObj
        }

        function makeBreadCrumb(b, task) {
            let xy = [b.x, b.y];
            let node = task.painter.xy_to_tiles[xy][0];
            let crumb = task.painter.paper.circle(
                parseInt(node.getAttribute("x")) + parseInt(node.getAttribute("width"))/2,
                parseInt(node.getAttribute("y")) + parseInt(node.getAttribute("height"))/2,
                trialparams.CRUMB_SIZE*trialparams.TILE_SIZE
            )
            crumb.xy_str = xy.join(",");
            crumb.attr("fill", "black")
            crumb.hide();
            crumb.isVisible = () => crumb.node.style.display !== "none"
            return crumb
        }
        function setupBreadcrumbElements(breadCrumbs, task) {
            let crumbEle = breadCrumbs.map(b => makeBreadCrumb(b, task));
            for (let i = 0; i < crumbEle.length; i++) {
                let c = crumbEle[i];
                if (i < crumbEle.length - 1) {
                    let nc = crumbEle[i + 1]
                    c.getNext = ((nc) => () => {
                        return nc
                    })(nc)
                    c.isLast = false;
                }
                else {
                    c.isLast = true;
                }
            }
            return crumbEle
        }

        function setupTask() {
            let trialnum = 0;
            let task = new GridWorldTask({
                container: $("#gridworld")[0],
                step_callback: (d) => {
                    if (trialnum === 0) {
                        $("#messages").html("&nbsp;");
                    }
                    goalObj.resetGoal();
                    if (crumb.xy_str === d.nextstate.join(',')) {
                        d.landedOnBreadCrumb = true;
                        let old_crumb = crumb;
                        if (!old_crumb.isLast) {
                            crumb = old_crumb.getNext();
                            setTimeout(() => crumb.show(), 100)
                        }
                        old_crumb.hide();
                        old_crumb.remove();
                    }
                    else {
                        d.landedonbreadcrumb = false;
                    }
                    d.trialnum = trialnum;
                    d.sessionId = window.globalExpStore.sessionId;
                    trialData.navigationData.push(d)
                    trialnum += 1;
                    console.log(d);
                    if (trialnum >= trialparams.MAX_TIMESTEPS) {
                        task.end_task()
                    }
                },
                endtask_callback: () => {
                    setTimeout(function() {
                        if (all_crumbs.map(c => !c.isVisible()).every(Boolean)) {
                            window.globalExpStore.bonusDollars += trialparams.roundBonusCents/100;
                            trialData.allCollected = true;
                        }
                        display_element.innerHTML = '';
                        jsPsych.finishTrial({data: trialData})
                    }, trialparams.ENDTASK_TIMEOUT || 0);
                },
                TILE_SIZE: trialparams.TILE_SIZE,
                OBJECT_ANIMATION_TIME: trialparams.OBJECT_ANIMATION_TIME
            });
            return task
        }
    });

    return plugin;
})();
