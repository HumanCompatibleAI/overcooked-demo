import * as Overcooked from "overcook"
let OvercookedGame = Overcooked.OvercookedGame.OvercookedGame;
let OvercookedMDP = Overcooked.OvercookedMDP;
let Direction = OvercookedMDP.Direction;
let Action = OvercookedMDP.Action;
let PlayerState = OvercookedMDP.PlayerState; 
let OvercookedState = OvercookedMDP.OvercookedState; 
let ObjectState = OvercookedMDP.ObjectState;

let [NORTH, SOUTH, EAST, WEST] = Direction.CARDINAL;
let [STAY, INTERACT] = [Direction.STAY, Action.INTERACT];

function state_obj(state_dict) {
    let object_dict = {}
    if (state_dict['objects'].length > 0) {
        state_dict['objects'].forEach(function (item, index) {
            object_dict[item['position']] = object_obj(item)
            })
        }
    state_dict['objects'] = object_dict

    return new OvercookedState({
        players: [player_obj(state_dict['players'][0]), player_obj(state_dict['players'][1])], 
        objects: state_dict['objects'], 
        order_list: state_dict['order_list']
    })


}

function player_obj(player_dict) {
    if (player_dict['held_object'] == null) {
        player_dict['held_object'] = undefined
    }
    else {
        player_dict['held_object'] = object_obj(player_dict['held_object'])
     }
     return new PlayerState({
        position: player_dict['position'], 
        orientation: player_dict['orientation'], 
        held_object: player_dict['held_object']
     })
    }

function object_obj(object_dict) {
    if (object_dict['state'] == null) {
        object_dict['state'] = undefined;
    }
    return new ObjectState(
        {name: object_dict['name'],
        position: object_dict['position'], 
        state: object_dict['state']
        })
}

function lookup_actions(actions_arr) {
    let actions = []; 
    actions_arr.forEach(function (item, index) {
        if (item == "interact") {
            item = INTERACT; 
        }
        if (item == "stay") {
            item = STAY;
        }
        actions.push(item);
    }
        )
    return actions;
    
}
export default class OvercookedTrajectoryReplay{
    constructor ({
        container_id,
        trajectory,
        start_grid = [
                'XXXXXPXX',
                'O     2O',
                'T1     T',
                'XXXDPSXX'
            ],
        MAX_TIME = 1, //seconds
        init_orders=['onion'],
        always_serve='onion',
        completion_callback = () => {console.log("Time up")},
        timestep_callback = (data) => {},
        DELIVERY_REWARD = 5
    }) {


    // Instead of loading in NPC policies, we're going to want to load in a trajectory
    // NPC policies get called at every time step

	let player_colors = {};
	player_colors[0] = 'green';
	player_colors[1] = 'blue';

    this.game = new OvercookedGame({
        start_grid,
        container_id,
        assets_loc: "assets/",
        ANIMATION_DURATION: 200*.9,
        tileSize: 80,
        COOK_TIME: 20,
        explosion_time: Number.MAX_SAFE_INTEGER,
        DELIVERY_REWARD: DELIVERY_REWARD,
        always_serve: always_serve,
        player_colors: player_colors
    });
    this.init_orders = init_orders;
    console.log("Trajectory replay");
    this.state_action_traj = trajectory.state_action_traj;
    this.MAX_TIME = MAX_TIME;
    this.time_left = MAX_TIME;
    this.cur_gameloop = 0;
    this.score = 0;
    this.completion_callback = completion_callback;
    this.timestep_callback = timestep_callback;
    this.total_timesteps = this.state_action_traj.length - 1;
    this.paused = false;
    this.keyboard_paused = false;
    this.last_step_time = new Date().getTime();
    this.seconds_per_step = 1;
    this.max_steps = 60;
    this.speed_play = 0;
    this.speed_seconds_per_step = 0.1; 
    }


    init() {
        this.game.init();

        this.start_time = new Date().getTime();

        // What type is a state? How do you construct one from raw data?  How do you. 
        // get a state's component elements? These will all be important for doing the trajectory replay
        
 
        this.gameloop = setInterval(() => {
            if (this.cur_gameloop > this.total_timesteps) {
                this.close()
            }
            if (this.cur_gameloop < 0) {
                this.cur_gameloop = 0;
            }
            if (this.paused == false && this.keyboard_paused == false) {
                this.disable_response_listener()
                this.last_step_time = new Date().getTime();
                let state_dict = this.state_action_traj[this.cur_gameloop][1]
                this.state = state_obj(state_dict)
                console.log("Drawing state: ")
                console.log(this.state)
                this.game.drawState(this.state);
                let actions_arr = this.state_action_traj[this.cur_gameloop][0]; 
                console.log(actions_arr);
                this.joint_action = lookup_actions(actions_arr);
                // read the two player actions out of the trajectory 
                // Do a transition and get the next state and reward. 
                let  [[next_state, prob], reward] =
                    this.game.mdp.get_transition_states_and_probs({
                        state: this.state,
                        joint_action: this.joint_action
                    });
                // If the state and reward don't match what's in the trajectory file, warn or 
                // die or something. 
                // update next round
                console.log("Game mechanic next state: ")
                console.log(next_state)
                // this.game.drawState(next_state);
                // this.score += reward;
                // this.game.drawScore(this.score);
                this.time_left = this.max_steps - this.cur_gameloop
                this.game.drawTimeLeft(this.time_left);

                //record data
                this.timestep_callback({
                    state: this.state,
                    joint_action: this.joint_action,
                    next_state: next_state,
                    reward: reward,
                    time_left: this.time_left,
                    score: this.score,
                    time_elapsed: this.cur_gameloop,
                    cur_gameloop: this.cur_gameloop,
                    client_id: undefined,
                    is_leader: undefined,
                    partner_id: undefined,
                    datetime: +new Date()
                });
                //set up next timestep
                this.paused = true
                this.activate_response_listener();
            }
            let seconds_since_step = (new Date().getTime() - this.last_step_time)/1000; 
            if (this.keyboard_paused == false) {
                if (this.speed_play < 0 && seconds_since_step > this.speed_seconds_per_step) {
                this.paused = false;
                this.cur_gameloop -= 1;
                }
                else if (this.speed_play > 0 && seconds_since_step > this.speed_seconds_per_step) {
                    this.paused = false;
                    this.cur_gameloop += 1;
                }
                else if (this.speed_play == 0 && seconds_since_step > this.seconds_per_step) {
                    this.paused = false;
                    this.cur_gameloop += 1;
                }
            }
            

            //time run out
            if (this.time_left < 0) {
                this.time_left = 0;
                this.close();
                }
        }, this.TIMESTEP);
        //By default it seems like we'd want to remove the response listener 
        // But we could maybe also keep a response listener that takes in the keys Left and Right 
        // And if it gets left it regresses the state, and if it gets. right, it progresses the state
        //this.activate_response_listener();
    }

    close () {
        if (typeof(this.gameloop) !== 'undefined') {
            clearInterval(this.gameloop);
        }
        this.game.close();
        this.disable_response_listener();
        this.completion_callback();
    }

    activate_response_listener () {
        $(document).on("keydown", (e) => {
            console.log(e)
            switch(e.which) {
                case 37: // left
                this.cur_gameloop -= 1;
                this.speed_play = -1; 
                this.paused = false; 
                break;

                case 39: // right
                this.cur_gameloop += 1;
                this.speed_play = +1; 
                this.paused = false; 
                break;

                case 32: //space
                if (this.keyboard_paused) {
                    this.keyboard_paused = false;
                    console.log("Unpausing")
                }
                else {
                    this.keyboard_paused = true;
                    console.log("Pausing")
                }
                
                break;

                default: return; // exit this handler for other keys
            }
            e.preventDefault(); // prevent the default action (scroll / move caret)
        });

    $(document).on("keyup", (e) => {
        if (e.which == 37 || e.which == 39) {
            this.speed_play = 0; 
        }
        
    }); 
    }

    disable_response_listener () {
        $(document).off('keydown');
    }
}
