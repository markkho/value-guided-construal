export let makeid = (len) => {
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

    for ( var i=0; i < len; i++ ){
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text
}

export function FailedAttentionCheckException(message, redirectLink) {
    this.message = message;
    this.redirectLink = redirectLink;
}

function GlobalErrorHandler() {
    this.name = "geh"
    this.errorHandler = console.log
    let self = this;
    this.setHandler = function (handler) {
        self.errorHandler = handler;
    }
    this.handle = function (func) {
        return async function () {
            try {
                await func.apply(this, arguments)
            }
            catch (e) {
                self.errorHandler(e)
            }
        }
    }
}

export function isNumber(n) { return !isNaN(parseFloat(n)) && !isNaN(n - 0) }

// A single error handler for any async function
export let errors = new GlobalErrorHandler()
