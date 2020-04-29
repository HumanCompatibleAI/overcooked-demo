import * as tf from '@tensorflow/tfjs-core';

import * as Overcooked from "overcooked"; 
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

export default function getOvercookedPolicy(model_type, layout_name, playerIndex, argmax) {
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
			let [result, shape] = game.mdp.featurize_state(state, playerIndex);
			let state_tensor = tf.tensor(result, shape);
			let action_tensor = model.execute(state_tensor);
			let action_probs = action_tensor.arraySync()[0];
			let action_index; 
			if (argmax == true) {
				action_index = argmax(action_probs);
				
			}
			else {
				// will happen if argmax == false or if argmax == undefined
				action_index = sampleIndexFromCategorical(action_probs)
			}

			return Action.INDEX_TO_ACTION[action_index];
	    });
	});
    });
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
