import * as Overcooked from "overcook"
let OvercookedGame = Overcooked.OvercookedGame.OvercookedGame;
let OvercookedMDP = Overcooked.OvercookedMDP;
let Direction = OvercookedMDP.Direction;
let Action = OvercookedMDP.Action;
let [NORTH, SOUTH, EAST, WEST] = Direction.CARDINAL;
let [STAY, INTERACT] = [Direction.STAY, Action.INTERACT];

export default class OvercookedSinglePlayerTask{
    constructor ({
        container_id,
	player_index,
        npc_policies,
        start_grid = [
                'XXXXXPXX',
                'O     2O',
                'T1     T',
                'XXXDPSXX'
            ],
        TIMESTEP = 200,
        MAX_TIME = 20, //seconds
        init_orders=['onion'],
        always_serve='onion',
        completion_callback = () => {console.log("Time up")},
        timestep_callback = (data) => {},
        DELIVERY_REWARD = 5
    }) {
        //NPC policies get called at every time step
        if (typeof(npc_policies) === 'undefined') {
            npc_policies = {
                1:
                    (function () {
                        let action_loop = [
                            SOUTH, WEST, NORTH, EAST
                        ];
                        let ai = 0;
                        let pause = 4;
                        return (s) => {
                            let a = STAY;
                            if (ai % pause === 0) {
                                a = action_loop[ai/pause];
                            }
                            ai += 1;
                            ai = ai % (pause*action_loop.length);
                            return a
                        }
                    })()
            }
        }
        this.npc_policies = npc_policies;
	this.player_index = player_index;

	let player_colors = {};
	player_colors[this.player_index] = 'green';
	player_colors[1 - this.player_index] = 'blue';

        this.game = new OvercookedGame({
            start_grid,
            container_id,
            assets_loc: "assets/",
            ANIMATION_DURATION: TIMESTEP*.9,
            tileSize: 80,
            COOK_TIME: 20,
            explosion_time: Number.MAX_SAFE_INTEGER,
            DELIVERY_REWARD: DELIVERY_REWARD,
            always_serve: always_serve,
            player_colors: player_colors
        });
        this.init_orders = init_orders;
        console.log("Single player");

        this.TIMESTEP = TIMESTEP;
        this.MAX_TIME = MAX_TIME;
        this.time_left = MAX_TIME;
        this.cur_gameloop = 0;
        this.score = 0;
        this.completion_callback = completion_callback;
        this.timestep_callback = timestep_callback;
    }

    init() {
        this.game.init();

        this.start_time = new Date().getTime();
        this.state = this.game.mdp.get_start_state(this.init_orders);
        this.game.drawState(this.state);
        this.joint_action = [STAY, STAY];

        this.gameloop = setInterval(() => {
	    for (let npc_index in this.npc_policies) {
		let npc_a = this.npc_policies[npc_index](this.state, this.game);
		this.joint_action[npc_index] = npc_a;
	    }
            let  [[next_state, prob], reward] =
                this.game.mdp.get_transition_states_and_probs({
                    state: this.state,
                    joint_action: this.joint_action
                });

            //update next round
            this.game.drawState(next_state);
            this.score += reward;
            this.game.drawScore(this.score);
            let time_elapsed = (new Date().getTime() - this.start_time)/1000;
            this.time_left = Math.round(this.MAX_TIME - time_elapsed);
            this.game.drawTimeLeft(this.time_left);

            //record data
            this.timestep_callback({
                state: this.state,
                joint_action: this.joint_action,
                next_state: next_state,
                reward: reward,
                time_left: this.time_left,
                score: this.score,
                time_elapsed: time_elapsed,
                cur_gameloop: this.cur_gameloop,
                client_id: undefined,
                is_leader: undefined,
                partner_id: undefined,
                datetime: +new Date()
            });

            //set up next timestep
            this.state = next_state;
            this.joint_action = [STAY, STAY];
            this.cur_gameloop += 1;
            this.activate_response_listener();

            //time run out
            if (this.time_left < 0) {
                this.time_left = 0;
                this.close();
            }
        }, this.TIMESTEP);
        this.activate_response_listener();
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
            let action;
            switch(e.which) {
                case 37: // left
                action = WEST;
                break;

                case 38: // up
                action = NORTH;
                break;

                case 39: // right
                action = EAST;
                break;

                case 40: // down
                action = SOUTH;
                break;

                case 32: //space
                action = INTERACT;
                break;

                default: return; // exit this handler for other keys
            }
            e.preventDefault(); // prevent the default action (scroll / move caret)

            this.joint_action[this.player_index] = action;
            this.disable_response_listener();
        });
    }

    disable_response_listener () {
        $(document).off('keydown');
    }
}
