import {GridWorldTask} from "../gridworld/gridworld-task.js"
import {errors} from "../exputils.js"

jsPsych.plugins["GridNavigationHoverReveal"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'GridNavigationHoverReveal',
        parameters: {}
    };

    plugin.trial = errors.handle(async function(display_element, trial) {
        let trialparams = Object.assign({
            initialText: "",
            hoverText: "",
            navigationText: "",
            hoverMode: true,
            flashMaze: false,
            participantStarts: true,
            requireMouseMove: false,
            hideCursorDuringNav: true,
            MAX_TIMESTEPS: 1e10,
            DWELL_REVEAL_TIME_MS: 500,
            GOALSIZE: .4,
            TILE_SIZE: 50,
            OBJECT_ANIMATION_TIME: 50,
            PREFLASH_DURATION_MS: 2000,
            FLASHMAZE_DURATION_MS: 500,
            MASK_DURATION_MS: 500
        }, trial.trialparams)
        let taskparams = trial.taskparams;
        let trialData = {
            trialparams,
            taskparams,
            sessionId: window.globalExpStore.sessionId,
            navigationData: [],
            mouseMoveData: [],
            mouseHoverData: [],
            datatype: "trialData"
        }
        window.trialData = trialData;

        const startTime = Date.now();
        display_element.innerHTML = '<div id="messages"></div><div id="gridworld"></div>';
        let trialnum = 0;

        let task = new GridWorldTask({
            container: $("#gridworld")[0],
            step_callback: (d) => {
                if (trialnum === 0) {
                    deactivateHovering()
                    if (trialparams.hideCursorDuringNav) {
                        $("#gridworld").css("cursor", "none")
                    }
                    $("#messages").html(trialparams.navigationText);
                }
                d.trialnum = trialnum;
                d.sessionId = window.globalExpStore.sessionId;
                trialData.navigationData.push(d)
                trialnum += 1;
                if (trialnum >= trialparams.MAX_TIMESTEPS) {
                    task.end_task()
                }
            },
            endtask_callback: () => {
                setTimeout(function() {
                    display_element.innerHTML = '';
                    jsPsych.finishTrial({data: trialData})
                }, trialparams.ENDTASK_TIMEOUT || 0);
            },
            TILE_SIZE: trialparams.TILE_SIZE,
            OBJECT_ANIMATION_TIME: trialparams.OBJECT_ANIMATION_TIME
        });

        $("#messages").html(trialparams.initialText);
        task.init({
            feature_array: removeNonWalls(taskparams['feature_array'])
        })
        if (trialparams.participantStarts) {
            await participantStartsTrial()
        }
        if (trialparams.flashMaze) {
            await flashMaze()
        }
        if (trialparams.hoverMode) {
            hoverMaze(trialData.mouseMoveData, trialData.mouseHoverData)
        }
        else {
            normalMaze()
        }

        function participantStartsTrial() {
            return new Promise((resolve) => {
                const y = Math.floor(taskparams.feature_array.length/2)
                const x = Math.floor(taskparams.feature_array[0].length/2)
                let start = task.painter.add_text({x, y, text: 'X'})
                            .attr('fill', 'red')
                            .attr('cursor', 'default')
                $(start[0]).on('click', () => {
                    start.remove()
                    $(start[0]).off('click')
                    resolve()
                })
            })
        }

        async function flashMaze() {
            let flash_taskparams = Object.assign(
                {},
                taskparams,
                {
                    feature_colors: {
                        "#": taskparams.feature_colors["#"],
                        ".": taskparams.feature_colors["."],
                        "G": taskparams.feature_colors["G"],
                        "S": taskparams.feature_colors["S"]
                    }
                }
            )
            task.init(flash_taskparams)
            await new Promise(resolve => setTimeout(resolve, trialparams.PREFLASH_DURATION_MS))
            task.init(taskparams)
            await new Promise(resolve => setTimeout(resolve, trialparams.FLASHMAZE_DURATION_MS))
            const mask_params = Object.assign(
                {},
                taskparams,
                {
                    feature_array: randomMaskLike(taskparams['feature_array'])
                }
            )
            task.init(mask_params)
            await new Promise(resolve => setTimeout(resolve, trialparams.MASK_DURATION_MS))
        }

        function hoverMaze(mouseMoveData, mouseHoverData) {
            let hover_taskparams = Object.assign(
                {},
                taskparams,
                {
                    feature_colors: {
                        "#": taskparams.feature_colors["#"],
                        ".": taskparams.feature_colors["."],
                        "G": taskparams.feature_colors["G"],
                        "S": taskparams.feature_colors["S"]
                    }
                }
            )
            $("#messages").html(trialparams.hoverText);
            task.init(hover_taskparams);
            activateHovering(mouseMoveData, mouseHoverData)
            if (trialparams.requireMouseMove) {
                $(document).on("mousemove.requiredmove", () => {
                    $(document).off("mousemove.requiredmove")
                    task.start()
                })
            }
            else {
                task.start()
            }
        }

        function normalMaze() {
            $("#messages").html(trialparams.navigationText);
            task.init(taskparams);
            task.start()
        }

        function activateHovering(mouseMoveData, mouseHoverData) {
            let obstacleFeatures = ["0", "1", "2", "3", "4", "5", "6", "7"];
            let obstacleTiles = obstacleFeatures.reduce( // to get tiles quickly
                (ot, o) => {
                    ot[o] = [];
                    return ot
                }, {}
            )
            task.painter.tiles.map((tile) => {
                //update obstacle-tile lookup
                let f = task.mdp.state_features[tile.grid_xy];
                if (obstacleFeatures.includes(f)) {
                    obstacleTiles[f].push(tile[0])
                    tile.isObstacle = true;
                }

                //apply hovering handles
                let obsName = `obstacle_${f}`;
                $(tile[0]).on("mouseenter", () => {
                    let hoverEvent = {
                        visible: false,
                        x: tile.grid_xy[0],
                        y: tile.grid_xy[1],
                        obstacle: f,
                        enterTime: Date.now()
                    };
                    let dwell = setTimeout(() => {
                        if (obstacleFeatures.includes(f)) {
                            obstacleTiles[f].map((obstile) => {
                                $(obstile).attr('fill', taskparams.feature_colors[f])
                            })
                        }
                        hoverEvent.visible = true;
                    }, trialparams.DWELL_REVEAL_TIME_MS);
                    $(tile[0]).on("mouseleave", () => {
                        clearTimeout(dwell);
                        if (hoverEvent.visible) {
                            hoverEvent.exitTime = Date.now();
                            mouseHoverData.push(hoverEvent)
                            if (obstacleFeatures.includes(f)) {
                                obstacleTiles[f].map((obstile) => {
                                    $(obstile).attr('fill', 'white')
                                })
                            }
                        }
                        $(tile[0]).off("mouseleave")
                    })
                })
            })

            //record mouse movements on screen with lower-left of maze as origin (browsers use top-left)
            let originTile = task.painter.tiles[0][0];
            let originTileRect, mouseX, mouseY;
            $(document).on("mousemove.recordMouse", (event) => {
                originTileRect = originTile.getBoundingClientRect()
                mouseX = (event.pageX - originTileRect.left)/trialparams.TILE_SIZE
                mouseY = (originTileRect.bottom - event.pageY)/trialparams.TILE_SIZE
                mouseMoveData.push({
                    mouseX, mouseY,
                    pageX: event.pageX, pageY: event.pageY,
                    time: Date.now() - startTime
                })
            })
        }

        function deactivateHovering() {
            task.painter.tiles.map((tile) => {
                $(tile[0]).off("mousemove")
                $(tile[0]).off("mouseenter")
                $(tile[0]).off("mouseleave")
                if (tile.isObstacle) {
                    $(tile[0]).attr('fill', 'white')
                }
            })
            $(document).off("mousemove.recordMouse")
        }

        function removeNonWalls(task_array) {
            let ignoreFeatures = ["0", "1", "2", "3", "4", "5", "6", "7", "G", "S"];
            let new_array = []
            let row;
            for (var y = 0; y < task_array.length; y++) {
                row = [];
                for (var x = 0; x < task_array[0].length; x++) {
                    if (ignoreFeatures.includes(task_array[y][x])) {
                        row.push('.')
                    }
                    else {
                        row.push(task_array[y][x])
                    }
                }
                new_array.push(row.join(''))
            }
            return new_array
        }

        function randomMaskLike(task_array) {
            let new_array = []
            let row;
            for (var y = 0; y < task_array.length; y++) {
                row = [];
                for (var x = 0; x < task_array[0].length; x++) {
                    if (Math.random () < .6) {
                        row.push('.')
                    }
                    else {
                        row.push('0')
                    }
                }
                new_array.push(row.join(''))
            }
            return new_array
        }

        //DEBUGGING FUNCTION
        function renderMouseMoves() {
            let maxtime = trialData['mouseMoveData'][trialData['mouseMoveData'].length - 1].time;
            let color;
            let startColor = [51, 51, 255];
            let endColor = [255, 153, 51];
            trialData['mouseMoveData'].map((move) => {
                let time = move.time;
                color = startColor.map((c, ci) => ((endColor[ci] - c)*(time/maxtime) + c)).join(',')
                $("body").append(`<div id="mousedot" style="display: inline; position: fixed; z-index: 99999; left: -5px; top: -5px; background: rgb(${color}); border-radius: 100%; opacity: 0.7; width: 10px; height: 10px; transform: translate3d(${move.pageX}px, ${move.pageY}px, 0px);"></div>`)
            })
        }
        window.renderMouseMoves = renderMouseMoves;
        window.task = task;
    });

    return plugin;
})();
