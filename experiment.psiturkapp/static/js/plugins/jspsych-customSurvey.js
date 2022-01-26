import {FailedAttentionCheckException, errors} from "../exputils.js"

jsPsych.plugins["CustomSurvey"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'CustomSurvey',
        parameters: {}
    };
    class Question {
        constructor(question_id, question_params) {
            this.id = question_id;
            this.question_params = question_params;
            this.complete = false
        }
        isRequired() {
            return false
        }
        requireCorrect() {
            return false
        }
        response() {
            return "NO RESPONSE"
        }
        check() {
            if (!this.isRequired() && !this.requireCorrect()) {
                return true
            }
            $(`#${this.id}`).css("border", "");
            $(`#${this.id} .msg`).remove();
            if (this.isRequired() && !this.hasResponse()) {
                $(`#${this.id}`).prepend("<div class='msg' style='color:red'><b>Required</b></div>");
                $(`#${this.id}`).css("border", "red 2px solid")
                return false
            }
            if (this.requireCorrect() && !this.isCorrect()) {
                $(`#${this.id}`).prepend("<div class='msg' style='color:red'><b>This is incorrect</b></div>");
                $(`#${this.id}`).css("border", "red 2px solid")
                return false
            }
            return true
        }
        record(trialData) {
            let name = this.name || this.id;
            trialData[name] = this.response(); //send object with other data
        }
    }

    class TextQuestion extends Question {
        constructor(question_id, question_params) {
            question_params = Object.assign({
                prompt: "TEXT"
            }, question_params)
            super(question_id, question_params)
            this.html = `
                <div id="${question_id}" class="jspsych-customsurvey-instructions">${question_params.prompt}</div>
            `;
        }
    }

    class TextboxQuestion extends Question {
        constructor(question_id, question_params) {
            question_params = Object.assign({
                prompt: "TEXTBOX",
                value: "",
                required: false,
                requreCorrect: false,
                correctResponse: undefined,
                rows: 1,
                columns: 50
            }, question_params)
            super(question_id, question_params)
            this.name = question_params.name || question_id
            let input_el = question_params.rows === 1 ?
                `<input type="text" name="${this.name}" size="${question_params.columns}" value="${question_params.value}"></input>` :
                `<textarea name="${this.name}" cols="${question_params.columns}" rows="${question_params.rows}">${question_params.value}</textarea>`;
            this.required = question_params.required;

            this.html = `
            <div id="${question_id}" class="jspsych-survey-text-question" style="margin: 2em 0em;">
                <p class="jspsych-survey-text">${question_params.prompt}${this.required ? "<span style='color:red'>*</span>" : ""}</p>
                ${input_el}
            </div>`
        }
        response() {
            return $(`#${this.id} :input`)[0].value;
        }
        hasResponse() {
            return this.response() !== ""
        }
        isCorrect() {
            return this.response() === this.question_params.correct
        }
        requireCorrect() {
            return this.question_params.requireCorrect
        }
        isRequired() {
            return this.question_params.required
        }
    }

    class MultiplechoiceQuestion extends Question {
        constructor(question_id, question_params) {
            question_params = Object.assign({
                prompt: "MULTIPLE CHOICE",
                horizontal: false,
                required: false,
                options: ["A", "B", "C"],
                correct: "A",
                requireCorrect: false,
                maxAttempts: 3,
                name: "Q"+parseInt(Math.random()*100)
            }, question_params)
            super(question_id, question_params)
            this.name = question_params.name || question_id
            var question_classes = ['jspsych-survey-multi-choice-question'];
            if (question_params.horizontal) {
                question_classes.push('jspsych-survey-multi-choice-horizontal');
            }
            this.required = question_params.required || false;
            let radiobuttons = [];
            for (var j = 0; j < question_params.options.length; j++) {
                var option_id_name = `${question_id}-${j}`;
                let option_id = `${question_id}-${j}`;
                let option_text = question_params.options[j]

                radiobuttons.push(`
                    <div id="${option_id_name}" class="jspsych-survey-multi-choice-option">
                        <label class="jspsych-survey-multi-choice-text">
                            <input type="radio" name="${this.name}" value="${option_text}">
                            ${option_text}
                        </label>
                    </div>
                `)
            }
            this.html = `
                <div id="${question_id}" class="${question_classes.join(' ')}">
                    <p class="jspsych-survey-multi-choice-text survey-multi-choice">${question_params.prompt} ${this.required ? "<span style='color:red'>*</span>" : ""}</p>
                    ${radiobuttons.join('\n')}
                </div>
            `
        }
        response() {
            let response = $(`#${this.id} input[name=${this.name}]:checked`);
            if (response.length === 0) {
                return
            }
            return response[0].value
        }
        hasResponse() {
            return typeof(this.response()) !== "undefined"
        }
        isCorrect() {
            return this.response() === this.question_params.correct
        }
        requireCorrect() {
            return this.question_params.requireCorrect
        }
        isRequired() {
            return this.question_params.required
        }
    }

    //likert response
    //     if (question_params.type === 'likert') {
    //         // add question
    //         html += '<label class="jspsych-survey-likert-statement">' + question_params.prompt + '</label>';
    //         // add options
    //         var width = 100 / question_params.labels.length;
    //         var options_string = '<ul class="jspsych-survey-likert-opts" data-radio-group="Q' + i + '">';
    //         for (var j = 0; j < question_params.labels.length; j++) {
    //             options_string += '<li style="width:' + width + '%"><input type="radio" name="Q' + i + '" value="' + j + '"';
    //             if(question_params.required){
    //               options_string += ' required';
    //             }
    //             options_string += '><label class="jspsych-survey-likert-opt-label">' + question_params.labels[j] + '</label></li>';
    //         }
    //         options_string += '</ul>';
    //         html += options_string;
    //     }
    // }
    plugin.trial = errors.handle(async function(display_element, trial) {
        const startTime = Date.now();
        //default values for trial
        trial = Object.assign({
            preamble: "",
            maxAttempts: 10000,
            failSurveyRedirect: "https://app.prolific.co/submissions/complete?cc=2FACC063",
        	continue_wait_time: 5000,
        }, trial)
        let trialData = {};

        //css for multiple choice, likert,
        display_element.innerHTML = `<style id="jspsych-customsurvey-css"></style><div id="customsurvey"><div>${trial.preamble}</div></div><div style="padding-bottom:50px"><button id="continue" class="jspsych-btn">Continue</button></div>`;
        var cssstr =
          //multi-choice
          ".jspsych-survey-multi-choice-question { margin-top: 2em; margin-bottom: 2em}"+
          ".jspsych-survey-multi-choice-text span.required {color: darkred;}"+
          ".jspsych-survey-multi-choice-horizontal .jspsych-survey-multi-choice-text {  text-align: center;}"+
          ".jspsych-survey-multi-choice-option { line-height: 2; }"+
          ".jspsych-survey-multi-choice-horizontal .jspsych-survey-multi-choice-option {  display: inline-block;  margin-left: 1em;  margin-right: 1em;  vertical-align: top;}"+
          // "label.jspsych-survey-multi-choice-text input[type='radio'] {margin-right: 1em;}"+
          //likert
          ".jspsych-survey-likert-statement { display:block; font-size: 16px; padding-top: 40px; margin-bottom:10px; }"+
          ".jspsych-survey-likert-opts { list-style:none; width:100%; margin:0; padding:0 0 35px; display:block; font-size: 14px; line-height:1.1em; }"+
          ".jspsych-survey-likert-opt-label { line-height: 1.1em; color: #444; }"+
          ".jspsych-survey-likert-opts:before { content: ''; position:relative; top:11px; /*left:9.5%;*/ display:block; background-color:#efefef; height:4px; width:100%; }"+
          ".jspsych-survey-likert-opts:last-of-type { border-bottom: 0; }"+
          ".jspsych-survey-likert-opts li { display:inline-block; /*width:19%;*/ text-align:center; vertical-align: top; }"+
          ".jspsych-survey-likert-opts li input[type=radio] { display:block; position:relative; top:0; left:50%; margin-left:-6px; }"
        display_element.querySelector('#jspsych-customsurvey-css').innerHTML = cssstr;

        //render questions
        let questions = trial.questions.map((question_params, i) => {
            let question_id = `surveyelement-${i}`;
            if (question_params.type === 'text') {
                return new TextQuestion(question_id, question_params)
            }
            else if (question_params.type === 'textbox') {
                return new TextboxQuestion(question_id, question_params)
            }
            else if (['multiple-choice', 'multi-choice', 'MC', 'mc'].includes(question_params.type)) {
                return new MultiplechoiceQuestion(question_id, question_params)
            }
            else {
                throw "Unknown question type"
            }
        });
        questions.map((q) => {
            $("#customsurvey").append(q.html)
        })

        let attempts = 0;
        async function onContinue() {
            attempts += 1;
            let allCheck = questions.map((q) => q.check()).every(e => e);
            if (!allCheck) {
                if (attempts >= trial.maxAttempts) {
                    questions.map(q => q.record(trialData))
                    jsPsych.finishTrial(trialData)
                    throw new FailedAttentionCheckException(
                        `<div class='jspsych-content'>
                            Maximum attempts exceeded.
                        </div>`,
                        trial.failSurveyRedirect
                    )
                }
                return
            }
            questions.map(q => q.record(trialData))
            jsPsych.finishTrial({data: trialData})
        }
        onContinue = errors.handle(onContinue);
        $("#continue").click(onContinue);
    });
    return plugin;
})();


jsPsych.plugins["SaveGlobalStore"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'SaveGlobalStore',
        parameters: {}
    };
    plugin.trial = errors.handle(async function(display_element, trial) {
        jsPsych.finishTrial({data: JSON.parse(JSON.stringify(window.globalExpStore))})
    });
    return plugin;
})();
