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
    DELIVERY_POINTS: 20,
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
    ], 
    "test_layout": [
    "XXPXX", 
    "O  2O", 
    "T1  T", 
    "XDPSX"
    ]
};

let game;

function startGame(endOfGameCallback) {
    let AGENT_INDEX = 1 - PARAMS.PLAYER_INDEX;
    /***********************************
          Set up websockets server
    ***********************************/
    // let HOST = "https://lit-mesa-15330.herokuapp.com/".replace(/^http/, "ws");
    // let gameserverio = new GameServerIO({HOST});

    let players = [$("#playerZero").val(), $("#playerOne").val()]
    console.log(players);
    if (players[0] == 'human' && players[1] == 'human')
    {
        console.log("Got inside If statement")
        $("#overcooked").html("<h3>Sorry, we can't support humans as both players.  Please make a different dropdown selection and hit Enter</h3>"); 
        endOfGameCallback();
        return;
    } 
    let layout_name = $("#layout").val();
    let layout = layouts[layout_name];
    $("#overcooked").empty();
    getOvercookedPolicy(players[0], layout_name, 0).then(function(npc_policy_zero) {
        getOvercookedPolicy(players[1], layout_name, 1).then(function(npc_policy_one) {
            let player_index = null; 
            let npc_policies = {0: npc_policy_zero, 1: npc_policy_one}; 
            if (npc_policies[0] == null) {
                player_index = 0; 
                npc_policies = {1: npc_policy_one}; 
            }
            if (npc_policies[1] == null) {
                player_index = 1; 
                npc_policies = {0: npc_policy_zero}; 
            }
            game = new OvercookedSinglePlayerTask({
                container_id: "overcooked",
                player_index: player_index,
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
    startGame(enableEnter);
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
