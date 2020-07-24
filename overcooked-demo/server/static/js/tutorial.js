// Persistent network connection that will be used to transmit real-time data
var socket = io();



var tutorial_params;

var tutorial_instructions = [
    `
    <p>Your goal here is to cook and deliver soups in order to earn reward. Notice how your partner is busily churning out soups</p>
    <p>See if you can copy his actions in order to cook and deliver the appropriate soup</p>
    <p><b>Note</b>: only recipes in the <b>All Orders</b> field will earn reward. Thus, you must cook a soup with <b>exactly</b> 3 onions</p>
    <p>You will advance only when you have delivered the appropriate soup</p>
    <p>Good luck!</p>
    `,
    `
    <p>Oh no! Your partner has made a grave mistake! He has mistakingly placed two onions in the pot</p>
    <p>This is an issue because no recipe on the <b>All Orders</b> list can started with 2 onions</p>
    <p>See if you can remedy the situation and cook a recipe that is indeed valid</p>
    <p><b>Note:</b> You cannot remove ingredients from the pot. You can, however, cook any soup you like, even if it's not in <b>All Orders</b>...</p>
    <p>You will advance only when you have delivered a valid soup<p>
    <p>Good Luck!</p>
    `,
    `
    <p>One last mechanic: <b>Bonus Orders</b>. In addition to the <b>All Orders</b> list, recipes in <b>Bonus Orders</b> are worth extra points!</p>
    <p>Your goal here is to cook and deliver a bonus order</p>
    <p>Even though you can earn reward for other orders, you will advance only when you have delivered a bonus order</p>
    <p>Good Luck!</p>
    `
];

var curr_tutorial_phase;

// Read in game config provided by server
$(function() {
    tutorial_params = JSON.parse($('#config').text())
    console.log(`tutorial params: ${JSON.stringify(tutorial_params)}`);
});

/* * * * * * * * * * * * * * * * 
 * Button click event handlers *
 * * * * * * * * * * * * * * * */

$(function() {
    $('#try-again').click(function () {
        data = {
            "params" : tutorial_params,
            "game_name" : "tutorial"
        };
        socket.emit("join", data);
    });
});



/* * * * * * * * * * * * * 
 * Socket event handlers *
 * * * * * * * * * * * * */

socket.on('creation_failed', function(data) {
    // Tell user what went wrong
    let err = data['error']
    $("#overcooked").empty();
    $('#overcooked').append(`<h4>Sorry, tutorial creation code failed with error: ${JSON.stringify(err)}</>`);
    $('#try-again').show();
});

socket.on('start_game', function(data) {
    console.log('start game');
    curr_tutorial_phase = 0;
    graphics_config = {
        container_id : "overcooked",
        start_info : data
    };
    $("#overcooked").empty();
    $('#game-over').hide();
    $('#try-again').hide();
    $('#game-title').text(`Tutorial in Progress, Phase ${curr_tutorial_phase}/3`);
    $('#game-title').show();
    $('#tutorial-intructions').append(tutorial_instructions[curr_tutorial_phase]);
    $('#tutorial-intructions').show();
    enable_key_listener();
    graphics_start(graphics_config);
});

socket.on('reset_game', function(data) {
    console.log('reset game');
    curr_tutorial_phase++;
    graphics_end();
    disable_key_listener();
    $("#overcooked").empty();
    $('#tutorial-intructions').empty();
    $("#tutorial-intructions").append(tutorial_instructions[curr_tutorial_phase]);
    $('#game-title').text(`Tutorial in Progress, Phase ${curr_tutorial_phase}/3`);
    graphics_config = {
        container_id : "overcooked",
        start_info : data.state
    };
    graphics_start(graphics_config);
    enable_key_listener();
});

socket.on('state_pong', function(data) {
    // Draw state update
    drawState(data['state']);
});

socket.on('end_game', function(data) {
    console.log("end game");
    // Hide game data and display game-over html
    graphics_end();
    disable_key_listener();
    $('#game-title').hide();
    $('#tutorial-intructions').hide();
    $('#game-over').show();
    
    // Game ended unexpectedly
    if (data.status === 'inactive') {
        $('#error-exit').show();
    }
    // Propogate game stats to parent window with psiturk code
    window.top.postMessage({ name : "tutorial-done" }, "*");
});


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

/* * * * * * * * * * * * 
 * Game Initialization *
 * * * * * * * * * * * */

socket.on("connect", function() {
    // Config for this specific game
    let data = {
        "params" : tutorial_params,
        "game_name" : "tutorial"
    };

    // create (or join if it exists) new game
    socket.emit("join", data);
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