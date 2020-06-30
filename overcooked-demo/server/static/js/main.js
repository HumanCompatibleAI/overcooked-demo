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
})





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
});

socket.on('creation_failed', function(data) {
    // Tell user what went wrong
    let err = data['error']
    $('#overcooked').append(`<h4>Sorry, game creation code failed with error: ${err}</>`);
});

socket.on('start_game', function() {
    // Hide game-over and lobby, show game title header
    $('#game-over').hide();
    $('#lobby').hide();
    $('#join').hide();
    $('#create').hide();
    $('#leave').show();
    $('#game-title').show();
});

socket.on('state_pong', function(data) {
    console.log("state update")
    // Draw state update
    $("#overcooked").empty();
    $("#overcooked").append(`<h4>Current active players ${data['state']['players']}\nCurrent tick: ${data['state']['count']}</>`);
});

socket.on('end_game', function() {
    // Hide game data and display game-over html
    $('#game-title').hide();
    $('#game-over').show();
    $("#overcooked").empty();
    $("#join").show();
    $("#create").show();
    $("#leave").hide();
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
