/* * * * * * 
 * Globals *
 * * * * * */

var lobbyWaitTime = 300000;
window.ellipses = -1;
window.lobbyTimeout = -1;
window.ackInterval = -1;

/* * * * * * * * * * * * * 
 * Socket event handlers *
 * * * * * * * * * * * * */

socket.on('waiting', function(data) {
    try {
        // Show game lobby
        console.log("Waiting!");
        $('#game-over').hide();
        $("#game").empty();
        $('#lobby').show();
        if (!data.in_game) {
            if (window.intervalID === -1) {
                console.log("Creating join piong");
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
        $("#game").empty();
        $('#game').append(`<h4>Sorry, game creation code failed with error: ${JSON.stringify(err)}</>`);
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
            container_id : "game",
            start_info : data.start_info
        };
        $("#game").empty();
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
        $("#their-turn").hide();
        $("#our-turn").hide();
        $("#reset-game").show();
        setTimeout(function() {
            $("#reset-game").hide();
            graphics_config = {
                container_id : "game",
                start_info : data.state
            };
            $("#game").empty();
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

socket.on('end_game', function(data) {
    try {
        // Hide game data and display game-over html
        graphics_end();
        disable_key_listener();
        $("#their-turn").hide();
        $("#our-turn").hide();
        $('#game-title').hide();
        $('#game-over').show();
        $("#game").empty();

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
        console.log("Game Error!");
        console.log(JSON.stringify(data));
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
        $("#their-turn").hide();
        $("#our-turn").hide();
        $('#game-title').hide();
        $('#game-over').show();
        $("#game").empty();
        $('#lobby').hide();
        $("#error").show();
        $("#error-exit").show();

        // Propogate game stats to parent window with psiturk code
        let game_data = JSON.stringify({});
        if (typeof data.data !== 'undefined') {
            game_data = data.data;
        }
        window.top.postMessage({ name : "error", data : game_data }, "*");
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
        $("#their-turn").hide();
        $("#our-turn").hide();
        $('#game-title').hide();
        $('#game-over').show();
        $("#game").empty();
        $('#lobby').hide();
        $("#error").show();
        $("#error-exit").show();

        // Propogate game stats to parent window with psiturk code
        let game_data = JSON.stringify({});
        if (typeof data.data !== 'undefined') {
            game_data = data.data;
        }
        window.top.postMessage({ name : "error", data : game_data }, "*");
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


/* * * * * * * * * * * * 
 * Game Initialization *
 * * * * * * * * * * * */

socket.on("connect", function() {
    try {
        // Set global user is (same as ID stored in game-state server-side), used for determining whose turn it is
        user_id = socket.id;
        
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
