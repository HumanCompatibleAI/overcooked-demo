import $ from "jquery"
import _ from "lodash"
// import GameServerIO from "./js/gameserver-io.js"
// import OvercookedInteractiveTask from "./js/overcooked-task";
import OvercookedSinglePlayerTask from "./js/overcooked-single";
import getOvercookedPolicy from "./js/load_tf_model.js";
import OvercookedTrajectoryReplay from "./js/overcooked-replay.js";

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
    "cramped_room":[
        "XXPXX",
        "O  2O",
        "X1  X",
        "XDXSX"
    ],
    "asymmetric_advantages":[
        "XXXXXXXXX",
        "O XSXOX S",
        "X   P 1 X",
        "X2  P   X",
        "XXXDXDXXX"
    ],
    "coordination_ring":[
        "XXXPX",
        "X 1 P",
        "D2X X",
        "O   X",
        "XOSXX"
    ],
    "random0":[
        "XXXPX",
        "O X1P",
        "O2X X",
        "D X X",
        "XXXSX"
    ],
    "random3": [
        "XXXPPXXX",
        "X      X",
        "D XXXX S",
        "X2    1X",
        "XXXOOXXX"
    ]
};

let game;
let replayer;
function replayGame(){
    // make sure the game metadata matches what's 
    // in the trajectory file
    $.getJSON("assets/test_traj.json", function(trajectory_data) {
        replayer = new OvercookedTrajectoryReplay({
            container_id: "overcooked", 
            trajectory: trajectory_data, 
            start_grid: layouts["cramped_room"],
            MAX_TIME : PARAMS.MAIN_TRIAL_TIME, //seconds
            init_orders: ['onion'],
            always_serve: 'onion',
            completion_callback: () => {
            console.log("Time up");
            endOfGameCallback();
            },
            DELIVERY_REWARD: PARAMS.DELIVERY_POINTS

        })
        replayer.init()
    });
    

}

function startGame(endOfGameCallback) {
    let AGENT_INDEX = 1 - PARAMS.PLAYER_INDEX;
    /***********************************
          Set up websockets server
    ***********************************/
    // let HOST = "https://lit-mesa-15330.herokuapp.com/".replace(/^http/, "ws");
    // let gameserverio = new GameServerIO({HOST});

    let model_type = $("#agent").val();
    let layout_name = $("#layout").val();
    let layout = layouts[layout_name];

    getOvercookedPolicy(model_type, layout_name, AGENT_INDEX).then(function(npc_policy) {
	let npc_policies = {};
	npc_policies[AGENT_INDEX] = npc_policy;
	$("#overcooked").empty();
    game = new OvercookedSinglePlayerTask({
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
    	endOfGameCallback();
        },
        DELIVERY_REWARD: PARAMS.DELIVERY_POINTS
        });
    game.init();
    });
}

function endGame() {
    game.close();
}

// Handler to be added to $(document) on keydown when a game is not in
// progress, that will then start the game when Enter is pressed.
function startGameOnEnter(e) {
    // Do nothing for keys other than Enter
    if (e.which !== 13) {
	return;
    }

    disableEnter();
    // Reenable enter handler when the game ends
    //startGame(enableEnter);
    replayGame()
}

function enableEnter() {
    $(document).keydown(startGameOnEnter);
    $("#control").html("<p>Press enter to begin!</p>");
}

function disableEnter() {
    $(document).off("keydown");
    $("#control").html('<button id="reset" type="button" class="btn btn-primary">Reset</button>');
    $("#reset").click(endGame);
}

$(document).ready(() => {
    enableEnter();
});
