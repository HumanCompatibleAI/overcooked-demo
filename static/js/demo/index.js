import $ from "jquery"
import _ from "lodash"
// import GameServerIO from "./js/gameserver-io.js"
// import OvercookedInteractiveTask from "./js/overcooked-task";
import OvercookedSinglePlayerTask from "./js/overcooked-single";
import getOvercookedPolicy from "./js/load_tf_model.js";

import * as Overcooked from "overcook"
let OvercookedMDP = Overcooked.OvercookedMDP;
let Direction = OvercookedMDP.Direction;
let Action = OvercookedMDP.Action;
let [NORTH, SOUTH, EAST, WEST] = Direction.CARDINAL;
let [STAY, INTERACT] = [Direction.STAY, Action.INTERACT];

// Parameters
let PARAMS = {
    MAIN_TRIAL_TIME: 60, //seconds
    TIMESTEP_LENGTH: 150, //milliseconds
    DELIVERY_POINTS: 5,
    PLAYER_INDEX: 1,  // Either 0 or 1
    MODEL_TYPE: 'ppo_bc'  // Either ppo_bc, ppo_sp, or pbt
};

/***********************************
      Main trial order
 ************************************/


let layouts = {
    "Cramped Room":[
        "XXPXX",
        "O  2O",
        "X1  X",
        "XDXSX"
    ],
    "Asymmetric Advantages":[
        "XXXXXXXXX",
        "O XSXOX S",
        "X   P 1 X",
        "X2  P   X",
        "XXXDXDXXX"
    ],
    "Coordination Ring":[
        "XXXPX",
        "X 1 P",
        "D2X X",
        "O   X",
        "XOSXX"
    ],
    "Counter Circuit":[
        "XXXPPXXX",
        "X      X",
        "D XXXX S",
        "X2    1X",
        "XXXOOXXX"
    ],
    "Forced Coordination": [
        "XXXPX",
        "O X1P",
        "O2X X",
        "D X X",
        "XXXSX"
    ]
};

let agent_layout_names = {
    "Cramped Room": "cramped_room",
    "Asymmetric Advantages": "asymmetric_advantages",
    "Coordination Ring": "coordination_ring",
    "Counter Circuit": "random0",
    "Forced Coordination": "random3"
};

$(document).ready(() => {
    let AGENT_INDEX = 1 - PARAMS.PLAYER_INDEX;
    var setup_exp_pages = function () {

        /***********************************
               Set up websockets server
         ***********************************/
        // let HOST = "https://lit-mesa-15330.herokuapp.com/".replace(/^http/, "ws");
        // let gameserverio = new GameServerIO({HOST});

        let layout_name = 'Cramped Room';
	let agent_layout_name = agent_layout_names[layout_name];
	let layout = layouts[layout_name];

	getOvercookedPolicy(PARAMS.MODEL_TYPE, agent_layout_name, AGENT_INDEX).then(function(npc_policy) {
	    let npc_policies = {};
	    npc_policies[AGENT_INDEX] = npc_policy;
            let game = new OvercookedSinglePlayerTask({
                container_id: "overcooked",
		player_index: PARAMS.PLAYER_INDEX,
                start_grid : layout,
		npc_policies: npc_policies,
                TIMESTEP : PARAMS.TIMESTEP_LENGTH,
                MAX_TIME : PARAMS.MAIN_TRIAL_TIME, //seconds
                init_orders: ['onion'],
                always_serve: 'onion',
                completion_callback: () => {
		    console.log("Time up");
                },
                timestep_callback: (data) => {
                    data.layout_name = layout_name;
                    data.layout = layouts[layout_name];
                },
                DELIVERY_REWARD: PARAMS.DELIVERY_POINTS
            });
            $("#overcooked").css("text-align", "center");
            game.init();
        });

    };

    /*******************
     * Run Task
     ******************/
    setup_exp_pages();
});
