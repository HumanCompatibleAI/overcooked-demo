// Persistent network connection that will be used to transmit real-time data
var socket = io();

var config;
var lobbyWaitTime = 300000;

/* * * * * * * * * * * * * 
 * Socket event handlers *
 * * * * * * * * * * * * */

window.intervalID = -1;
window.ellipses = -1;
window.lobbyTimeout = -1;
window.ackInterval = -1;

socket.on('waiting', function(data) {
    try {
        // Show game lobby
        $('#game-over').hide();
        $("#overcooked").empty();
        $('#lobby').show();
        if (!data.in_game) {
            if (window.intervalID === -1) {
                // Occassionally ping server to try and join
                window.intervalID = setInterval(function() {
                    socket.emit('join', {"game_name" : "psiturk"});
                }, 1000);
            }
        }
        if (window.lobbyTimeout === -1) {
            // Waiting animation
            window.ellipses = setInterval(function () {
                var e = $("#ellipses").text();
                $("#ellipses").text(".".repeat((e.length + 1) % 10));
            }, 500);
            // Timeout to leave lobby if no-one is found
            window.lobbyTimeout = setTimeout(function() {
                socket.emit('leave', {});
            }, config.lobbyWaitTime)
        }
    } catch (err) {
        if (window.ackInterval !== -1) {
            clearInterval(window.ackInterval);
            window.ackInterval = -1;
        }
    }
});

socket.on('creation_failed', function(data) {
    try {
        // Tell user what went wrong
        let err = data['error']
        $("#overcooked").empty();
        $('#overcooked').append(`<h4>Sorry, game creation code failed with error: ${JSON.stringify(err)}</>`);
        $("error-exit").show();

        // Let parent window (psiturk) know error occurred
        window.top.postMessage({ name : "error", error : "creation failed"}, "*");
    } catch (err) {
        let data = JSON.stringify({});
        let error = JSON.stringify(err);
        window.top.postMessage({ name : "error", data : data, error : error }, "*");
    }
});

socket.on('start_game', function(data) {
    try {
        // Hide game-over and lobby, show game title header
        if (window.intervalID !== -1) {
            clearInterval(window.intervalID);
            window.intervalID = -1;
        }
        if (window.lobbyTimeout !== -1) {
            clearInterval(window.ellipses);
            clearTimeout(window.lobbyTimeout);
            window.lobbyTimeout = -1;
            window.ellipses = -1;
        }
        graphics_config = {
            container_id : "overcooked",
            start_info : data.start_info
        };
        $("#overcooked").empty();
        $('#game-over').hide();
        $('#lobby').hide();
        $('#reset-game').hide();
        $('#game-title').show();
        enable_key_listener();
        graphics_start(graphics_config);
    } catch (err) {
        if (window.ackInterval !== -1) {
            clearInterval(window.ackInterval);
            window.ackInterval = -1;
        }
    }
});

socket.on('reset_game', function(data) {
    try {
        graphics_end();
        disable_key_listener();
        $("#overcooked").empty();
        $("#reset-game").show();
        setTimeout(function() {
            $("#reset-game").hide();
            graphics_config = {
                container_id : "overcooked",
                start_info : data.state
            };
            graphics_start(graphics_config);
            enable_key_listener();

            // Propogate game stats to parent window (psiturk)
            window.top.postMessage({ name : "data", data : data.data, done : false}, "*");
        }, data.timeout);
    } catch (err) {
        let data = JSON.stringify({});
        let error = JSON.stringify(err);
        window.top.postMessage({ name : "error", data : data, error : error }, "*");
    }
});

socket.on('state_pong', function(data) {
    // Draw state update
    drawState(data['state']);
});

socket.on('end_game', function(data) {
    try {
        // Hide game data and display game-over html
        graphics_end();
        disable_key_listener();
        $('#game-title').hide();
        $('#game-over').show();
        $("#overcooked").empty();

        // Game ended unexpectedly
        if (data.status === 'inactive') {
            $("#error").show();
            $("#error-exit").show();
        }

        // Propogate game stats to parent window with psiturk code
        window.top.postMessage({ name : "data", data : data.data, done : true }, "*");
    } catch (err) {
        let data = JSON.stringify({});
        let error = JSON.stringify(err);
        window.top.postMessage({ name : "error", data : data, error : error }, "*");
    }
});

socket.on('end_lobby', function() {
    try {
        // Display join game timeout text
        $("#finding_partner").text(
            "We were unable to find you a partner."
        );
        $("#error-exit").show();

        // Stop trying to join
        clearInterval(window.intervalID);
        clearInterval(window.ellipses);
        window.intervalID = -1;

        // Let parent window (psiturk) know what happened
        window.top.postMessage({ name : "timeout" }, "*");
    } catch (err) {
        let data = JSON.stringify({});
        let error = JSON.stringify(err);
        window.top.postMessage({ name : "error", data : data, error : error }, "*");
    }
});

socket.on("game_error", function(data) {
    try {
        // Hide game-over and lobby, show game title header
        if (window.intervalID !== -1) {
            clearInterval(window.intervalID);
            window.intervalID = -1;
        }
        if (window.lobbyTimeout !== -1) {
            clearInterval(window.ellipses);
            clearTimeout(window.lobbyTimeout);
            window.lobbyTimeout = -1;
            window.ellipses = -1;
        }

        // Game crashed
        graphics_end();
        disable_key_listener();
        $('#game-title').hide();
        $('#game-over').show();
        $("#overcooked").empty();
        $('#lobby').hide();
        $("#error").show();
        $("#error-exit").show();

        // Propogate game stats to parent window with psiturk code
        let overcooked_data = JSON.stringify({});
        if (typeof data.data !== 'undefined') {
            overcooked_data = data.data;
        }
        window.top.postMessage({ name : "error", data : overcooked_data }, "*");
    } catch (err) {
        let data = JSON.stringify({});
        let error = JSON.stringify(err);
        window.top.postMessage({ name : "error", data : data, error : error }, "*");
    }
});

socket.on("server_error", function(data) {
    try {
        // Hide game-over and lobby, show game title header
        if (window.intervalID !== -1) {
            clearInterval(window.intervalID);
            window.intervalID = -1;
        }
        if (window.lobbyTimeout !== -1) {
            clearInterval(window.ellipses);
            clearTimeout(window.lobbyTimeout);
            window.lobbyTimeout = -1;
            window.ellipses = -1;
        }

        if (window.ackInterval !== -1) {
            clearInterval(window.ackInterval);
            window.ackInterval = -1;
        }

        // Something has gone horribly wrong!
        socket.disconnect();
        graphics_end();
        disable_key_listener();
        $('#game-title').hide();
        $('#game-over').show();
        $("#overcooked").empty();
        $('#lobby').hide();
        $("#error").show();
        $("#error-exit").show();

        // Propogate game stats to parent window with psiturk code
        let overcooked_data = JSON.stringify({});
        if (typeof data.data !== 'undefined') {
            overcooked_data = data.data;
        }
        window.top.postMessage({ name : "error", data : overcooked_data }, "*");
    } catch (err) {
        let data = JSON.stringify({});
        let error = JSON.stringify(err);
        window.top.postMessage({ name : "error", data : data, error : error }, "*");
    }
});

socket.on("disconnect", function(data) {
    if (window.ackInterval !== -1) {
        clearInterval(window.ackInterval);
        window.ackInterval = -1;
    }
})


/* * * * * * * * * * * * * * 
 * Game Key Event Listener *
 * * * * * * * * * * * * * */

function enable_key_listener() {
    $(document).on('keydown', function(e) {
        if (e.originalEvent.repeat) { // Holding down key only counts as one keypress
            return;
        }
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


/* * * * * * * * * * * * 
 * Game Initialization *
 * * * * * * * * * * * */

socket.on("connect", function() {
    try {
        // set configuration variables
        set_config();

        // Start ack function in background
        if (config.ack_timeout !== -1) {
            window.ackInterval = setInterval(ack_function, config.ack_timeout);
        }

        // Config for this specific game
        let uid = $('#uid').text();
        let params = JSON.parse(JSON.stringify(config.experimentParams));
        params.psiturk_uid = uid;
        let data = {
            "params" : params,
            "game_name" : "psiturk"
        };

        // create (or join if it exists) new game
        socket.emit("join", data);
    } catch (err) {
        let data = JSON.stringify({});
        let error = JSON.stringify(err);
        window.top.postMessage({ name : "error", data : data, error : error }, "*");
    }
});


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

var set_config = function() {
    config = JSON.parse($("#config").text());
    config.ack_timeout = JSON.parse($("#ack-interval").text());
}

var ack_function = function() {
    // Propogate game stats to parent window (psiturk)
    window.top.postMessage({ name : "ack" }, "*");
}
