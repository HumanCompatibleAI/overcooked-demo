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

var ack_function = function() {
    // Propogate game stats to parent window (psiturk)
    window.top.postMessage({ name : "ack" }, "*");
}