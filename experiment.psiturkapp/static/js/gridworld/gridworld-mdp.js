import {product, choose, fromPairs} from "./utils.js"

let rot90 = function(v, n) {
    n = typeof(n) === 'undefined' ? 1 : n;
    for (let i = 0; i < n+1; i++) {
        v = [-v[1], v[0]]
    }
    return v
};

let ACTION_CODES = {
    '>': [1, 0],
    '<': [-1,0],
    'v': [0,-1],
    '^': [0, 1],
    'x': [0, 0]
};

export class GridWorldMDP {
    constructor ({
        gridworld_array,
        feature_array,
        init_state,
        absorbing_states = [],
        absorbing_features = [],
        feature_rewards = {},
        feature_transitions = {
            'j': {
                '2forward': 1.0
            }
        },
        wall_features = ["#"],
        step_cost = 0,

        include_wait = false
    }) {
        if (typeof(feature_array) === 'undefined') {
            feature_array = gridworld_array;
        }
        this.height = feature_array.length;
        this.width = feature_array[0].length;

        this.states = product([_.range(this.width), _.range(this.height)]);
        this.walls = [];
        // absorbing_states = _.cloneDeep(absorbing_states);
        absorbing_states = JSON.parse(JSON.stringify(absorbing_states));
        this.state_features = this.states.map((s) => {
            let [x, y] = s;
            let f = feature_array[this.height - y - 1][x];
            if (wall_features.includes(f)) {
                this.walls.push(s);
            }
            if (_.includes(absorbing_features, f)) {
                absorbing_states.push(s)
            }
            return [s, f]
        });
        this.state_features = fromPairs(this.state_features);
        this.absorbing_states = absorbing_states.map(String);
        this.include_wait = include_wait;
        if (include_wait) {
			this.actions = ['^', 'v', '<', '>', 'x'];
		}
		else {
			this.actions = ['^', 'v', '<', '>'];
		}
		this.terminal_state = [-1, -1];

        this.feature_rewards = feature_rewards;
        this.feature_transitions = feature_transitions;
        this.step_cost = step_cost;
        this.wall_features = wall_features;
    }

    is_wall(state) {
        return this.wall_features.includes(this.state_features[state])
    }

    on_grid(s) {
        return [
            Math.max(Math.min(s[0], this.width-1), 0),
            Math.max(Math.min(s[1], this.height-1), 0)
        ]
    }

    get_typed_transition_func(name) {
        return {
            '2forward': (s, a) => {
                let ns0 = this.on_grid([s[0]+a[0], s[1]+a[1]]);
                let ns1 = this.on_grid([s[0]+a[0]*2, s[1]+a[1]*2]);
                if (this.is_wall(ns0)) {
                    return s
                }
                else if (this.is_wall(ns1)) {
                    return ns0
                }
                return ns1
            },
            'forward': (s, a) => {
                let ns = this.on_grid([s[0]+a[0], s[1]+a[1]]);
                if (this.is_wall(ns)) {
                    return s
                }
                return ns
            }
        }[name]
    }

    transition ({state, action}) {
        if (typeof(state) === 'string') {
            state = state.split(",").map(parseInt);
        }
        let [x, y] = state;
        action = ACTION_CODES[action];

        //non-standard transitions, otherwise default transition
        let ns;
        let f = this.state_features[state];
        let fs = Object.keys(this.feature_transitions);
        if (_.includes(fs, f)) {
            let f_trans = choose(this.feature_transitions[f]);
            ns = this.get_typed_transition_func(f_trans)(state, action)
        }
        else {
            ns = this.get_typed_transition_func('forward')(state, action)
        }
        return ns
    }

    reward ({
        state,
        action,
        nextstate
    }) {
        // let ns_type = _.get(this.state_features, String(nextstate));
        let ns_type = this.state_features[String(nextstate)];
        let r = this.feature_rewards[ns_type];
        r = typeof(r) !== 'undefined' ? r : 0;
        // let r = _.get(this.feature_rewards, ns_type, 0);
        r += this.step_cost;
        return r
    }

    is_absorbing(state) {
        state = String(state);
        return _.includes(this.absorbing_states, state);
    }
}