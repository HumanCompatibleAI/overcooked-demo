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



