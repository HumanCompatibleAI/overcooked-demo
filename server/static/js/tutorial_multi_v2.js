// Persistent network connection that will be used to transmit real-time data
var socket = io();



var config;

var tutorial_instructions = () => [
    `
    <p>Mechanic: <b>Delivery</b></p>
    <p>Your goal here is to cook and deliver soups in order to earn reward. Notice how your partner is busily churning out soups</p>
    <p>See if you can copy his actions in order to cook and deliver the appropriate soup</p>
    <p><b>Note</b>: only recipes in the <b>All Orders</b> field will earn reward. Thus, you must cook a soup with <b>exactly</b> 3 onions</p>
    <p>You are the  <b>blue cook</b> in this game</p>
    <p><b>You will advance only when you have delivered a valid 3-onion soup</b></p>
    <p>Good luck!</p>
    <br></br>
    `,
    `
    <p>Mechanic: <b>Improper Soup</b></p>
    <p>Oh no! Your partner has made a grave mistake! He has mistakingly <b>started cooking</b> when there are only two onions in the pot</p>
    <p>This is an issue because 2-onion is not a valid recipe, and delivering it will incur no reward</p>
    <p>However, the only pot you have access to is currently blocked by this invalid soup! And you cannot add onion to a cooking/cooked soup</p>
    <p>See if you can remedy the situation and cook a recipe that is indeed valid</p>
    <p>You are the  <b>blue cook</b> in this game</p>
    <p><b>You will advance only when you have delivered a valid 3-onion soup</b></p>
    <p>Good Luck!</p>
    <br></br>
    `,
    `
    <p>Mechanic: <b>Counter Usage</b></p>
    <p>Your partner is again back again busily busting out onion soups, except this time, something is different...</p>
    <p>The map has changed, and the resources are very limited on the new map. You and your partner must work together to finish cooking </p>
    <p>Your goal here is to cooperate with your partner and deliver a fully cooked valid soup</p>
    <p>You are the  <b>blue cook</b> in this game</p>
    <p><b>You will advance only when you have delivered a valid 3-onion soup</b></p>
    <br></br>
    `,
    `
    <p>Mechanic: <b>Movement Collision</b></p>
    <p>Now you are in another new map where you and your partner need to work together in a very confined space</p>
    <p>Your partner tries to be helpful (with varying degrees of success), and you would need to work with them</p>
    <p>You can deduct the intended movement of your partner by <b>observing which way they are facing</b>:
        For example, if they are facing right, their last intended movement command was "moving right".
    </p>
    <p>Your goal here is to work with them to deliver a valid soup</p>
    <p>You are the  <b>blue cook</b> in this game</p>
    <p><b>You will advance only when you have delivered a valid 3-onion soup</b></p>
    <p>Good Luck!</p>
    <br></br>
    `
];

var tutorial_hints = () => [
    `
    <p>
        You can move up, down, left, and right using
        the <b>arrow keys</b>, and interact with objects
        using the <b>spacebar</b>.
      </p>
      <p>
        You can interact with objects by facing them and pressing
        <b>spacebar</b>. Here are some examples:
        <ul>
          <li>If you are holding nothing, you can pick up a dispensed item (onion/plate) by facing
            the dispenser area and pressing <b>spacebar</b>.
            <img class="center" src="static/images/onion_pickup.png" style="width:700px">
            <img class="center" src="static/images/dish_pickup.png" style="width:700px">
          </li>
          <li>If you are holding an onion and facing a pot that is not full,
            and press <b>spacebar</b>, you will put the onion in the pot.
            <img class="center" src="static/images/onion_drop_init.png" style="width:700px">
            <img class="center" src="static/images/onion_drop_more.png" style="width:700px">
          </li>
          <li>If you are holding nothing and facing a pot that is non-empty,
            and press <b>spacebar</b>, you will begin cooking a soup.
            <img class="center" src="static/images/start_cooking.png" style="width:700px">
          </li>
          <li>If you are holding a plate and facing a pot with a fully cooked soup
            and press <b>spacebar</b>, you will pick up the fully cooked soup with the plate.
            <img class="center" src="static/images/soup_pickup.png" style="width:700px">
          </li>
          <li>If you are holding a fully cooked soup and facing a serving station
            and press <b>spacebar</b>, you will serve the fully cooked soup.
            <img class="center" src="static/images/serving.png" style="width:700px">
          </li>
          <li>If you are holding an item (an onion, a plate, or a cooked soup), are facing an empty counter,
            and press <b>spacebar</b>, you put the item on the counter.
            <img class="center" src="static/images/counter_drop_onion.png" style="width:700px">
            <img class="center" src="static/images/counter_drop_dish.png" style="width:700px">
          </li>
          <li>If you are not holding anything, are facing an occupied counter with an item (an onion, a plate, or a cooked soup),
            and press <b>spacebar</b>, you pick up the item from the counter.
            <img class="center" src="static/images/counter_pickup_soup.png" style="width:700px">
          </li>
        </ul>
      </p>

      <p>
        Common mistakes:
        <ul>
          <li>If you are holding an item, you cannot pick up anything from the dispensers or the counters
            <img class="center" src="static/images/invalid_pickup_dispenser.png" style="width:700px">
            <img class="center" src="static/images/invalid_pickup_counter.png" style="width:700px">
          </li>
          <li>You cannot add an an onion to the pot once cooking starts.
            <img class="center" src="static/images/invalid_onion_drop.png" style="width:700px">
          </li>
          <li>You cannot pick up a soup while it is still cooking in the pot.
            <img class="center" src="static/images/invalid_soup_pickup.png" style="width:700px">
          </li>
        </ul>
      </p>
    `,
    `
    <p>Once a soup starts cooking in a pot, you cannot add/remove ingredients, even if the soup is invalid</p>
    <p>You can, however, dish the invalid soup to empty the pot, and then cook any soup you like</p>
    <br>
    <br>
    <p>
        You can interact with objects by facing them and pressing
        <b>spacebar</b>. Here are some examples:
        <ul>
          <li>If you are holding nothing, you can pick up a dispensed item (onion/plate) by facing
            the dispenser area and pressing <b>spacebar</b>.
            <img class="center" src="static/images/onion_pickup.png" style="width:700px">
            <img class="center" src="static/images/dish_pickup.png" style="width:700px">
          </li>
          <li>If you are holding an onion and facing a pot that is not full,
            and press <b>spacebar</b>, you will put the onion in the pot.
            <img class="center" src="static/images/onion_drop_init.png" style="width:700px">
            <img class="center" src="static/images/onion_drop_more.png" style="width:700px">
          </li>
          <li>If you are holding nothing and facing a pot that is non-empty,
            and press <b>spacebar</b>, you will begin cooking a soup.
            <img class="center" src="static/images/start_cooking.png" style="width:700px">
          </li>
          <li>If you are holding a plate and facing a pot with a fully cooked soup
            and press <b>spacebar</b>, you will pick up the fully cooked soup with the plate.
            <img class="center" src="static/images/soup_pickup.png" style="width:700px">
          </li>
          <li>If you are holding a fully cooked soup and facing a serving station
            and press <b>spacebar</b>, you will serve the fully cooked soup.
            <img class="center" src="static/images/serving.png" style="width:700px">
          </li>
          <li>If you are holding an item (an onion, a plate, or a cooked soup), are facing an empty counter,
            and press <b>spacebar</b>, you put the item on the counter.
            <img class="center" src="static/images/counter_drop_onion.png" style="width:700px">
            <img class="center" src="static/images/counter_drop_dish.png" style="width:700px">
          </li>
          <li>If you are not holding anything, are facing an occupied counter with an item (an onion, a plate, or a cooked soup),
            and press <b>spacebar</b>, you pick up the item from the counter.
            <img class="center" src="static/images/counter_pickup_soup.png" style="width:700px">
          </li>
        </ul>
      </p>

      <p>
        Common mistakes:
        <ul>
          <li>If you are holding an item, you cannot pick up anything from the dispensers or the counters
            <img class="center" src="static/images/invalid_pickup_dispenser.png" style="width:700px">
            <img class="center" src="static/images/invalid_pickup_counter.png" style="width:700px">
          </li>
          <li>You cannot add an an onion to the pot once cooking starts.
            <img class="center" src="static/images/invalid_onion_drop.png" style="width:700px">
          </li>
          <li>You cannot pick up a soup while it is still cooking in the pot.
            <img class="center" src="static/images/invalid_soup_pickup.png" style="width:700px">
          </li>
        </ul>
      </p>

    `,
    `
    <p>
        You can interact with a counter by facing them and pressing
        <b>spacebar</b>. Here are some examples:
        <ul>
          <li>If you are holding an item (an onion, a plate, or a cooked soup), are facing an empty counter,
            and press <b>spacebar</b>, you put the item on the counter.
            <img class="center" src="static/images/counter_drop_onion.png" style="width:700px">
            <img class="center" src="static/images/counter_drop_dish.png" style="width:700px">
          </li>
          <li>If you are not holding anything, are facing an occupied counter with an item (an onion, a plate, or a cooked soup),
            and press <b>spacebar</b>, you pick up the item from the counter.
            <img class="center" src="static/images/counter_pickup_soup.png" style="width:700px">
          </li>
        </ul>
      </p>
    `,
    `
    <p>
        Note that as you and your partner are moving around the kitchen,
        the two of you <u><b>cannot occupy the same location</b></u>.
        <ul>
          <li> Valid movement: attempt to move into empty spaces will succeed
            <img class="center" src="static/images/move_valid.png" style="width:700px">
          </li>
          <li> Invalid movement: attempt to move into your partner will not succeed (and result in no change in location)
            <img class="center" src="static/images/move_invalid.png" style="width:700px">
          </li>
        </ul>
      </p>
     `
]

var curr_tutorial_phase;

// Read in game config provided by server
$(function() {
    config = JSON.parse($('#config').text());
    tutorial_instructions = tutorial_instructions();
    tutorial_hints = tutorial_hints();
    $('#quit').show();
});

/* * * * * * * * * * * * * * * * 
 * Button click event handlers *
 * * * * * * * * * * * * * * * */

$(function() {
    $('#try-again').click(function () {
        data = {
            "params" : config['tutorialParams'],
            "game_name" : "tutorial"
        };
        socket.emit("join", data);
        $('try-again').attr("disable", true);
    });
});

$(function() {
    $('#show-hint').click(function() {
        let text = $(this).text();
        let new_text = text === "Show Hint" ? "Hide Hint" : "Show Hint";
        $('#hint-wrapper').toggle();
        $(this).text(new_text);
    });
});

$(function() {
    $('#quit').click(function() {
        socket.emit("leave", {});
        $('quit').attr("disable", true);
        window.location.href = "./";
    });
});

$(function() {
    $('#finish').click(function() {
        $('finish').attr("disable", true);
        window.location.href = "./";
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
    $('#try-again').attr("disabled", false);
});

socket.on('start_game', function(data) {
    curr_tutorial_phase = 0;
    graphics_config = {
        container_id : "overcooked",
        start_info : data.start_info
    };
    $("#overcooked").empty();
    $('#game-over').hide();
    $('#try-again').hide();
    $('#try-again').attr('disabled', true)
    $('#hint-wrapper').hide();
    $('#show-hint').text('Show Hint');
    $('#game-title').text(`Tutorial in Progress, Phase ${curr_tutorial_phase}/${tutorial_instructions.length}`);
    $('#game-title').show();
    $('#tutorial-instructions').append(tutorial_instructions[curr_tutorial_phase]);
    $('#instructions-wrapper').show();
    $('#hint').append(tutorial_hints[curr_tutorial_phase]);
    enable_key_listener();
    graphics_start(graphics_config);
});

socket.on('reset_game', function(data) {
    curr_tutorial_phase++;
    graphics_end();
    disable_key_listener();
    $("#overcooked").empty();
    $('#tutorial-instructions').empty();
    $('#hint').empty();
    $("#tutorial-instructions").append(tutorial_instructions[curr_tutorial_phase]);
    $("#hint").append(tutorial_hints[curr_tutorial_phase]);
    $('#game-title').text(`Tutorial in Progress, Phase ${curr_tutorial_phase + 1}/${tutorial_instructions.length}`);
    
    let button_pressed = $('#show-hint').text() === 'Hide Hint';
    if (button_pressed) {
        $('#show-hint').click();
    }
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
    // Hide game data and display game-over html
    graphics_end();
    disable_key_listener();
    $('#game-title').hide();
    $('#instructions-wrapper').hide();
    $('#hint-wrapper').hide();
    $('#show-hint').hide();
    $('#game-over').show();
    $('#quit').hide();
    
    if (data.status === 'inactive') {
        // Game ended unexpectedly
        $('#error-exit').show();
        // Propogate game stats to parent window with psiturk code
        window.top.postMessage({ name : "error" }, "*");
    } else {
        // Propogate game stats to parent window with psiturk code
        window.top.postMessage({ name : "tutorial-done" }, "*");
    }

    $('#finish').show();
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
        "params" : config['tutorialParams'],
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