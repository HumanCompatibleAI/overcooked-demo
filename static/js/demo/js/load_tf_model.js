import * as tf from '@tensorflow/tfjs-core';

import * as Overcooked from "overcook"; 
let OvercookedGame = Overcooked.OvercookedGame.OvercookedGame;
let OvercookedMDP = Overcooked.OvercookedMDP;
let Direction = OvercookedMDP.Direction;
let Action = OvercookedMDP.Action;
let [NORTH, SOUTH, EAST, WEST] = Direction.CARDINAL;
let [STAY, INTERACT] = [Direction.STAY, Action.INTERACT];
import {loadGraphModel} from '@tensorflow/tfjs-converter';


function sampleIndexFromCategorical(probas) {
    // Stolen from: https://stackoverflow.com/questions/8877249/generate-random-integers-with-probabilities
    let randomNum = Math.random(); 
    let accumulator = 0; 
    let lastProbaIndex = probas.length - 1; 

    for (var i = 0;  i < lastProbaIndex; i++) {
	accumulator += probas[i]; 
	if (randomNum < accumulator) {
	    return i;
	}
    }
    return lastProbaIndex;
}

export default function getOvercookedPolicy(model_type, layout_name, playerIndex, use_argmax) {
    // Returns a Promise that resolves to a policy
    if (model_type == "human") {
	return new Promise(function(resolve, reject) {
	    resolve(null);
	});
    }
    
    const modelPromise = loadGraphModel('assets/' + model_type + '_' + layout_name + '_agent/model.json');

    return modelPromise.then(function (model) {
	return new Promise(function(resolve, reject) {
	    resolve(function (state, game) {
		let action_tensor = model.execute(preprocessState(state, game, playerIndex));
		let action_probs = action_tensor.arraySync()[0];
		let action_index; 
		if (use_argmax == true) {
		    action_index = argmax(action_probs);
		}
		else {
		    // will happen if use_argmax == false or if use_argmax == undefined
		    action_index = sampleIndexFromCategorical(action_probs)
		}

		return Action.INDEX_TO_ACTION[action_index];
	    });
	});
    });
}

const BASE_FEATURE_INDICES = {
    "P": 10,
    "X": 11,
    "O": 12,
    "D": 13,
    "S": 14
};

// The soup numbers are duplicated in preprocessState
const VARIABLE_FEATURE_INDICES = {
    "onions_in_pot": 15,
    "onions_cook_time": 16,
    "onion_soup_loc": 17,
    "dish": 18,
    "onion": 19
};

function preprocessState(state, game, playerIndex) {
    // All of our models have a batch size of 30, but we only want to predict on
    // a single state, so we put zeros everywhere else.
    let terrain = game.mdp.terrain_mtx;
    let shape = [30, terrain[0].length, terrain.length, 20];
    let result = constant(0, shape);

    function handle_object(obj) {
	let [x, y] = obj.position;
	if (obj.name === 'soup') {
	    let [soup_type, num_onions, cook_time] = obj.state;
	    if (terrain[y][x] === 'P') {
    		result[0][x][y][15] = num_onions;
    		result[0][x][y][16] = Math.min(cook_time, 20);
	    } else {
    		result[0][x][y][17] = 1;
	    }
	} else {
	    let feature_index = VARIABLE_FEATURE_INDICES[obj.name];
    	    result[0][x][y][feature_index] = 1;
	}
    }

    for (let i = 0; i < state.players.length; i++) {
	let player = state.players[i];
	let [x, y] = player.position;
	let orientation = Direction.DIRECTION_TO_INDEX[player.orientation];
	if (playerIndex === i) {
	    result[0][x][y][0] = 1;
	    result[0][x][y][2 + orientation] = 1;
	} else {
	    result[0][x][y][1] = 1;
	    result[0][x][y][6 + orientation] = 1;
	}

	if (player.has_object()) {
	    handle_object(player.held_object);
	}
    }

    let pos_dict = game.mdp._get_terrain_type_pos_dict();
    for (let ttype in BASE_FEATURE_INDICES) {
	let t_index = BASE_FEATURE_INDICES[ttype];
        for (let i in pos_dict[ttype]) {
            let [x, y] = pos_dict[ttype][i];
	    result[0][x][y][t_index] = 1;
        }
    }

    for (let i in state.objects) {
	let obj = state.objects[i];
	handle_object(obj);
    }
    return tf.tensor(result, shape);
}

function constant(element, shape) {
    function helper(i) {
	let size = shape[i];
	if (i === shape.length - 1) {
	    return Array(size).fill(element);
	}
	return Array(size).fill().map(() => helper(i+1));
    }
    return helper(0);
}

function argmax(array) {
    let bestIndex = 0;
    let bestValue = array[bestIndex];
    for (let i = 1; i < array.length; i++) {
	if (array[i] > bestValue) {
	    bestIndex = i;
	    bestValue = array[i];
	}
    }
    return bestIndex;
}
