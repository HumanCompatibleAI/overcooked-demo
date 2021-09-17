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

/* * * * * * * * * * * * * * * * 
 * Button click event handlers *
 * * * * * * * * * * * * * * * */

$(function() {
    $('#create').click(function () {
        params = arrToJSON($('form').serializeArray());
        params.layouts = [params.layout]
        data = {
            "params" : params,
            "game_name" : game_name,
            "create_if_not_found" : false
        };
        socket.emit("create", data);
        $('#waiting').show();
        $('#join').hide();
        $('#join').attr("disabled", true);
        $('#create').hide();
        $('#create').attr("disabled", true)
        $("#instructions").hide();
        $('#tutorial').hide();
    });
});

$(function() {
    $('#join').click(function() {
        socket.emit("join", {"game_name" : game_name});
        $('#join').attr("disabled", true);
        $('#create').attr("disabled", true);
    });
});

$(function() {
    $('#leave').click(function() {
        socket.emit('leave', {});
        $('#leave').attr("disabled", true);
    });
});





/* * * * * * * * * * * * * 
 * Socket event handlers *
 * * * * * * * * * * * * */

window.intervalID = -1;
window.spectating = true;

socket.on('connect', function(data) {
    user_id = socket.id;
});

socket.on('waiting', function(data) {
    // Show game lobby
    $('#error-exit').hide();
    $('#waiting').hide();
    $('#game-over').hide();
    $('#instructions').hide();
    $('#tutorial').hide();
    $("#game").empty();
    $('#lobby').show();
    $('#join').hide();
    $('#join').attr("disabled", true)
    $('#create').hide();
    $('#create').attr("disabled", true)
    $('#leave').show();
    $('#leave').attr("disabled", false);
    if (!data.in_game) {
        // Begin pinging to join if not currently in a game
        if (window.intervalID === -1) {
            window.intervalID = setInterval(function() {
                socket.emit('join', {"game_name" : game_name});
            }, 1000);
        }
    }
});

socket.on('creation_failed', function(data) {
    // Tell user what went wrong
    let err = data['error']
    $("#game").empty();
    $('#lobby').hide();
    $("#instructions").show();
    $('#tutorial').show();
    $('#waiting').hide();
    $('#join').show();
    $('#join').attr("disabled", false);
    $('#create').show();
    $('#create').attr("disabled", false);
    $('#game').append(`<h4>Sorry, game creation code failed with error: ${JSON.stringify(err)}</>`);
});

socket.on('start_game', function(data) {
    // Hide game-over and lobby, show game title header
    if (window.intervalID !== -1) {
        clearInterval(window.intervalID);
        window.intervalID = -1;
    }
    graphics_config = {
        container_id : "game",
        start_info : data.start_info
    };
    window.spectating = data.spectating;
    $('#error-exit').hide();
    $("#game").empty();
    $('#game-over').hide();
    $('#lobby').hide();
    $('#waiting').hide();
    $('#join').hide();
    $('#join').attr("disabled", true);
    $('#create').hide();
    $('#create').attr("disabled", true)
    $("#instructions").hide();
    $('#tutorial').hide();
    $('#leave').show();
    $('#leave').attr("disabled", false)
    $('#game-title').show();
    
    if (!window.spectating) {
        enable_key_listener();
    }
    
    graphics_start(graphics_config);
});

socket.on('reset_game', function(data) {
    graphics_end();
    if (!window.spectating) {
        disable_key_listener();
    }

    $("#their-turn").hide();
    $("#our-turn").hide();
    $("#reset-game").show();
    setTimeout(function() {
        $("#reset-game").hide();
        graphics_config = {
            container_id : "game",
            start_info : data.state
        };
        if (!window.spectating) {
            enable_key_listener();
        }
        $("#game").empty();
        graphics_start(graphics_config);
    }, data.timeout);
});

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

socket.on('end_game', function(data) {
    // Hide game data and display game-over html
    graphics_end();
    if (!window.spectating) {
        disable_key_listener();
    }
    $("#their-turn").hide();
    $("#our-turn").hide();
    $('#game-title').hide();
    $('#game-over').show();
    $("#join").show();
    $('#join').attr("disabled", false);
    $("#create").show();
    $('#create').attr("disabled", false)
    $("#instructions").show();
    $('#tutorial').show();
    $("#leave").hide();
    $('#leave').attr("disabled", true)
    
    // Game ended unexpectedly
    if (data.status === 'inactive') {
        $('#error-exit').show();
    }
});

socket.on("game_error", function(data) {
    // Hide game data and display error html
    graphics_end();
    if (!window.spectating) {
        disable_key_listener();
    }
    $("#their-turn").hide();
    $("#our-turn").hide();
    $('#lobby').hide();
    $('#waiting').hide();
    $('#game-title').hide();
    $('#game-over').show();
    $("#join").show();
    $('#join').attr("disabled", false);
    $("#create").show();
    $('#create').attr("disabled", false)
    $("#instructions").show();
    $('#tutorial').show();
    $("#leave").hide();
    $('#leave').attr("disabled", true)

    // Game ended unexpectedly
    console.log(data.error);
    $('#error-exit').show();
});

socket.on("server_error", function(data) {
    // Something has gone horribly wrong!
    socket.disconnect();
    graphics_end();
    if (!window.spectating) {
        disable_key_listener();
    }
    $("#their-turn").hide();
    $("#our-turn").hide();
    $('#lobby').hide();
    $('#waiting').hide();
    $('#game-title').hide();
    $('#game-over').show();
    $("#join").show();
    $('#join').attr("disabled", true);
    $("#create").show();
    $('#create').attr("disabled", true)
    $("#instructions").show();
    $('#tutorial').show();
    $("#leave").hide();
    $('#leave').attr("disabled", true)

    // Game ended unexpectedly
    $('#server-error').show();
    console.log(data.error);
});

socket.on('end_lobby', function() {
    // Hide lobby
    $('#lobby').hide();
    $("#join").show();
    $('#join').attr("disabled", false);
    $("#create").show();
    $('#create').attr("disabled", false)
    $("#leave").hide();
    $('#leave').attr("disabled", true)
    $("#instructions").show();
    $('#tutorial').show();

    // Stop trying to join
    clearInterval(window.intervalID);
    window.intervalID = -1;
})


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


/* * * * * * * * * * *
 * Utility Functions *
 * * * * * * * * * * */

var arrToJSON = function(arr) {
    let retval = {}
    for (let i = 0; i < arr.length; i++) {
        elem = arr[i];
        key = elem['name'];
        value = elem['value'];
        retval[key] = value;
    }
    return retval;
};

function updateAgents(layout) {
    let layout_to_agents = config.layout_to_agents
    agentOptions = "<option value=\"human\">Human Keyboard Input</option>"
    for (agentName of layout_to_agents[layout]) {
        agentOptions += "<option value=\"" + agentName + "\"> " + agentName  + "</option>";
    }
    document.getElementById("playerZero").innerHTML = agentOptions;
    document.getElementById("playerOne").innerHTML = agentOptions;
}

function updateTurn() {
    disable_key_listener();
    if (is_our_turn) {
        enable_key_listener();
        $("#their-turn").hide();
        $("#our-turn").show();
    } else {
        $("#their-turn").show();
        $("#our-turn").hide();
    }
}
