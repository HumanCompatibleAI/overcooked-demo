// Persistent network connection that will be used to transmit real-time data
var socket = io();

/* * * * * * * * * * * * * * * * 
 * Button click event handlers *
 * * * * * * * * * * * * * * * */

$(function() {
    $('#create').click(function () {
        params = arrToJSON($('form').serializeArray());
        params.layouts = [params.layout]
        data = {
            "params" : params,
            "game_name" : "overcooked"
        };
        socket.emit("create", data);
    });
});

$(function() {
    $('#join').click(function() {
        socket.emit("join", {});
    });
});

$(function() {
    $('#leave').click(function() {
        socket.emit('leave', {});
    });
});





/* * * * * * * * * * * * * 
 * Socket event handlers *
 * * * * * * * * * * * * */

window.intervalID = -1;

socket.on('waiting', function(data) {
    // Show game lobby
    $('#game-over').hide();
    $('#instructions').hide();
    $("#overcooked").empty();
    $('#lobby').show();
    $('#join').hide();
    $('#create').hide();
    $('#leave').show();
    if (window.intervalID === -1) {
        window.intervalID = setInterval(function() {
            socket.emit('join', {});
        }, 1000);
    }
});

socket.on('creation_failed', function(data) {
    // Tell user what went wrong
    let err = data['error']
    $("#overcooked").empty();
    $('#overcooked').append(`<h4>Sorry, game creation code failed with error: ${JSON.stringify(err)}</>`);
});

socket.on('start_game', function(data) {
    // Hide game-over and lobby, show game title header
    if (window.intervalID !== -1) {
        clearInterval(window.intervalID);
        window.intervalID = -1;
    }
    graphics_config = {
        container_id : "overcooked",
        start_info : data
    };
    $("#overcooked").empty();
    $('#game-over').hide();
    $('#lobby').hide();
    $('#join').hide();
    $('#create').hide();
    $("#instructions").hide();
    $('#leave').show();
    $('#game-title').show();
    enable_key_listener();
    graphics_start(graphics_config);
});

socket.on('reset_game', function(data) {
    graphics_end();
    disable_key_listener();
    $("#overcooked").empty();
    $("#reset-game").show();
    setTimeout(function() {
        $("reset-game").hide();
        graphics_config = {
            container_id : "overcooked",
            start_info : data.state
        };
        graphics_start(graphics_config);
        enable_key_listener();
    }, data.timeout);
});

socket.on('state_pong', function(data) {
    // Draw state update
    drawState(data['state']);
});

socket.on('end_game', function(data) {
    // Hide game data and display game-over html
    graphics_end();
    disable_key_listener();
    $('#game-title').hide();
    $('#game-over').show();
    $("#join").show();
    $("#create").show();
    $("#instructions").show();
    $("#leave").hide();
    
    // Game ended unexpectedly
    if (data.status === 'inactive') {
        $('#error-exit').show();
    }
});

socket.on('end_lobby', function() {
    // Hide lobby
    $('#lobby').hide();
    $("#join").show();
    $("#create").show();
    $("#leave").hide();
    $("#instructions").hide();

    // Stop trying to join
    clearInterval(window.intervalID);
    window.intervalID = -1;
})


/* * * * * * * * * * * * * * 
 * Game Key Event Listener *
 * * * * * * * * * * * * * */

function enable_key_listener() {
    $(document).on('keydown', function(e) {
        let action = 'STAY'
        switch (e.which) {
            case 37: // left
                action = 'LEFT';
                break;

            case 38: // up
                action = 'UP';
                break;

            case 39: // right
                action = 'RIGHT';
                break;

            case 40: // down
                action = 'DOWN';
                break;

            case 32: //space
                action = 'SPACE';
                break;

            default: // exit this handler for other keys
                return; 
        }
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
