// Persistent network connection that will be used to transmit real-time data
var socket = io();

var paused = true;
var play_direction = 1;
var timesteps_per_second = 30;
var timesteps_per_render = 1;
var states = [];
var terrain = [];
var current_frame = 0;
var last_frame_idx = 0;
var replay_loop;

var overcooked_container_id = "#overcooked"
var timestep_slider_id = "#timestep-slider-container";
var trajectories_file_input_id = "#trajectoriesFile";
var trajectory_idx_input_id = "#trajectoryIdx";
var timesteps_per_render_input_id = "#timestepsPerRender";
var timesteps_per_second_input_id = "#timestepsPerSecond";
var objects_ids_to_show_on_load_traj = [
    "#replay-keys-desc",
    "#timesteps-per-second-container",
    "#timesteps-per-render-container",
    "#trajectory-idx-container"]

function get_selected_trajectory_filename(){
    filename = $(trajectories_file_input_id).children("option:selected").val();
    if (filename){
        filename = filename + ".json";
    }
    return filename;
}

function set_trajectory_idx(value){
    $(trajectory_idx_input_id).val(value);
}

function get_trajectory_idx(){
    return $(trajectory_idx_input_id).val();
}

function send_trajectory_selected_event(filename, trajectory_idx){
    if (filename){ // empty filename is on the top of the list and means no trajectory selected
        socket.emit("trajectory_selected", {
            "trajectory_file": filename,
            "trajectory_idx": trajectory_idx
        });
    }
}

function update_timesteps_per_render() {
    timesteps_per_render = $(timesteps_per_render_input_id).val();
    if (!paused) {
        start_auto_play();
    }
}

function update_timesteps_per_second() {
    timesteps_per_second = $(timesteps_per_second_input_id).val();
    if (!paused) {
        start_auto_play();
    }
}

function render_current_frame(){
    drawState(states[current_frame]);
}

function replay_step(){
    current_frame = current_frame + play_direction*timesteps_per_render;
    if (current_frame >= last_frame_idx){
        current_frame = last_frame_idx;
        render_current_frame();
        if (play_direction > 0){
            end_auto_play();
            paused = true;
        }

    }
    else if (current_frame <= 0)
    {
        current_frame = 0
        render_current_frame();
        if (play_direction < 0){
            end_auto_play();
            paused = true;
        }
    }
    else {
        render_current_frame();
    }
    $(timestep_slider_id).slider("value", current_frame);
}

function start_auto_play(){
    end_auto_play();
    replay_step();
    replay_loop = setInterval(replay_step, (timesteps_per_render/timesteps_per_second)*1000);
}

function end_auto_play(){
    if (typeof replay_loop !== 'undefined'){
        clearInterval(replay_loop);
    }
}


$(function() {
    $(trajectories_file_input_id).change(function () {
        var trajectory_idx = 0;
        set_trajectory_idx(trajectory_idx);
        send_trajectory_selected_event(get_selected_trajectory_filename(), trajectory_idx);
    });
});

$(function() {
    $(trajectory_idx_input_id).change(function () {
        send_trajectory_selected_event(get_selected_trajectory_filename(), get_trajectory_idx());
    });
});


$(function() {
    $(timesteps_per_second_input_id).change(update_timesteps_per_second);
});

$(function() {
    $(timesteps_per_render_input_id).change(update_timesteps_per_render);
});


socket.on('replay_trajectory', function(data) {
    end_auto_play();
    paused = true;

    $(overcooked_container_id).empty();
    objects_ids_to_show_on_load_traj.forEach(function (item, index){
        $(item).show();
    });
    update_timesteps_per_render();
    update_timesteps_per_second();
    graphics_start({
        container_id : overcooked_container_id.substring(1), // skip "#" character
        start_info : data.start_info
    });
    states = data.states;
    last_frame_idx = states.length-1
    $(timestep_slider_id).slider({
        min: 0,
        max: last_frame_idx,
        slide: function( event, ui ) {
            current_frame = ui.value;
            render_current_frame();
        }
      });
    
    $(timestep_slider_id).slider( "option", "value", 0);
    $(trajectory_idx_input_id).attr({
        "max" : data.max_trajectory_idx
    });
});


$(document).on("keydown", e => {
    switch (e.which) {
        case 37:
            // left
            play_direction = -1;
            paused = false;
            start_auto_play();
            break;

        case 39:
            // right
            play_direction = +1;
            paused = false;
            start_auto_play();
            break;

        case 32:
            //space
            if (paused) {
                start_auto_play();
                
            } else {
                end_auto_play();
            }
            paused = !paused;
            break;
        default:
            return; // exit this handler for other keys
    }
    e.preventDefault(); // prevent the default action (scroll / move caret)
});

