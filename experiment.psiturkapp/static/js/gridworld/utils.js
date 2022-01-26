
export function product(elements) {
    /*copied from cartesian-product module*/
    if (!Array.isArray(elements)) {
        throw new TypeError();
    }

    var end = elements.length - 1,
        result = [];

    function addTo(curr, start) {
        var first = elements[start],
            last = (start === end);

        for (var i = 0; i < first.length; ++i) {
            var copy = curr.slice();
            copy.push(first[i]);

            if (last) {
                result.push(copy);
            } else {
                addTo(copy, start + 1);
            }
        }
    }

    if (elements.length) {
        addTo([], 0);
    } else {
        result.push([]);
    }
    return result;
}

export function sum(nums) {
    return nums.reduce((tot, n) => tot + n, 0)
}

export function choose(elements, probs) {
    if (!Array.isArray(elements)) {
    	let keys = Object.keys(elements);
        probs = keys.map((e) => elements[e]);
        elements = keys;
    }
    if (Math.abs(sum(probs) - 1) > 1e-2) {
        console.log("Probability does not sum to 1")
    }
    let t = Math.random();
    let cum = 0;
    for (let i = 0; i < probs.length; i++) {
        cum += probs[i];
        if (cum >= t) {
            return elements[i]
        }
    }
}

export function fromPairs(pairs) {
  return pairs.reduce((obj, p) => {
    obj[p[0]] = p[1];
    return obj
  }, {})
}

