/* * * * * * 
 * Globals *
 * * * * * */

// Persistent network connection that will be used to transmit real-time data
var socket = io();
var user_id;

// Global state pertaiing to whose turn it is
var turn_change;
var is_our_turn;

// Determines which type of game we're playing
var game_name = config.game_name;

// TODO: These values should come from server
var numColumns = 7;
var validActions = [0, 1, 2, 3, 4, 5, 6];

window.intervalID = -1;




/* * * * * * * * * * * * * * 
 * Game Key Event Listener *
 * * * * * * * * * * * * * */

function enable_key_listener() {
    $(document).on('keydown', function(e) {
        if (e.originalEvent.repeat) { // Holding down key only counts as one keypress
            return;
        }

        // Get number pressed, 1-9
        let keyNum = e.which - 48;

        // Convert to C4 action
        let action = keyNum - 1;
        if (!validActions.includes(action)) {
            // Not a valid action on this board
            return;
        }

        // Send action to game server
        action = action.toString();
        e.preventDefault();
        socket.emit('action', { 'action' : action });
    });
};

function disable_key_listener() {
    $(document).off('keydown');
};




/* * * * * * * * * * * * * 
 * Socket event handlers *
 * * * * * * * * * * * * */

socket.on('state_pong', function(data) {
    // Update turn state if whose turn it is just changed
    let local_is_our_turn = data['state']['active_player_id'] == user_id;
    turn_change = local_is_our_turn != is_our_turn;
    is_our_turn = local_is_our_turn;
    if (turn_change) {
        updateTurn();
    }
    // Draw state update
    drawState(data['state']);
});