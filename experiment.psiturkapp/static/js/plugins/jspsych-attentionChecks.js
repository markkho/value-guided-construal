jsPsych.plugins["reCAPTCHA"] = (function() {
    var plugin = {};
    plugin.info = {
        name: 'reCAPTCHA',
        parameters: {}
    };
    plugin.trial = async function(display_element, trial) {
        display_element.innerHTML = `<div id='myrecaptcha'></div>`
        psiturk.recordUnstructuredData("captchaStarted", "true")
        psiturk.saveData()
        grecaptcha.render(
            "myrecaptcha",
            {
                sitekey: "6LchQbwaAAAAAA71YvpgGvbHmkH0Y3mASmrELdhn",
                theme: "light",
                callback: response => {
                    console.log('passed')
                    psiturk.recordUnstructuredData("captchaCompleted", "true")
                    psiturk.saveData()
                    jsPsych.finishTrial()
                },
                "expired-callback": response => {
                    console.log('expired')
                    console.log(response)
                }
            }
        )
    };

    return plugin;
})()
