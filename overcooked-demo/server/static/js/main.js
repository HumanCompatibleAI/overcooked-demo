// Persistent network connection that will be used to transmit real-time data
var socket = io();

/* * * * * * * * * * * * * * * * 
 * Button click event handlers *
 * * * * * * * * * * * * * * * */

$(function() {
    $('#create').click(function () {
        params = arrToJSON($('form').serializeArray());
        socket.emit("create", params);
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

socket.on('waiting', function(data) {
    // Show game lobby
    $('#game-over').hide();
    $('#lobby').show();
    $('#join').hide();
    $('#create').hide();
    $('#leave').show();
    if (typeof window.intervalID === 'undefined'  || window.intervalID === null) {
        window.intervalID = setInterval(function() {
            socket.emit('join', {});
        }, 1000);
    }
});

socket.on('creation_failed', function(data) {
    // Tell user what went wrong
    let err = data['error']
    $('#overcooked').append(`<h4>Sorry, game creation code failed with error: ${err}</>`);
});

socket.on('start_game', function() {
    // Hide game-over and lobby, show game title header
    if (typeof window.intervalID !== 'undefined') {
        clearInterval(window.intervalID);
        window.intervalID = null;
    }
    $('#game-over').hide();
    $('#lobby').hide();
    $('#join').hide();
    $('#create').hide();
    $('#leave').show();
    $('#game-title').show();
    enable_key_listener();
    window.gameIntervalID = setInterval(game_loop, 200);
});

socket.on('state_pong', function(data) {
    // Draw state update
    $("#overcooked").empty();
    $("#overcooked").append(`<h4>Current game state: ${JSON.stringify(data['state'])}</>`);
});

socket.on('end_game', function() {
    // Hide game data and display game-over html
    $('#game-title').hide();
    $('#game-over').show();
    $("#overcooked").empty();
    $("#join").show();
    $("#create").show();
    $("#leave").hide();
    clearInterval(window.gameIntervalID);
    disable_key_listener();
});


/* * * * * * * * * * * * * * 
 * Game Key Event Listener *
 * * * * * * * * * * * * * */

window.action = "STAY";

function enable_key_listener() {
    $(document).on('keydown', function(e) {
        switch (e.which) {
            case 37: // left
                window.action = 'LEFT';
                break;

            case 38: // up
                window.action = 'UP';
                break;

            case 39: // right
                window.action = 'RIGHT';
                break;

            case 40: // down
                window.action = 'DOWN';
                break;

            case 32: //space
                window.action = 'SPACE';
                break;

            default: // exit this handler for other keys
                return; 
        }
        e.preventDefault();
        disable_key_listener();
    });
};

function disable_key_listener() {
    $(document).off('keydown');
};

function game_loop() {
    socket.emit('action', { "action" : window.action })
    window.action = "STAY";
    enable_key_listener();
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
