// Persistent network connection that will be used to transmit real-time data
var socket = io();

// used in render_event_chart.js
require.config({
    paths: {
        "d3": "static/lib/d3.v5.min",
        "jquery": "static/lib/jquery.min",
        "jquery-ui": "static/lib/jquery-ui.min"
        }
});

// control replaying variables
var graphics_is_started = false;
var paused = true;
var play_direction = 1;
var timesteps_per_second = 30;
var timesteps_per_render = 1;
var states = [];
var trajectory_chart_events = [];
var trajectory_chart_settings = [];
var terrain = [];
var current_frame = 0;
var last_frame_idx = 0;
var replay_loop;


// selectors for trajectory selections
var trajectories_file_input = "#trajectoriesFile";
var trajectory_idx_input = "#trajectoryIdx";
var objects_to_show_on_load_traj = [
    "#trajectory-idx-container",
    "#show-replay-container",
    "#show-trajectory-chart-container",
    trajectory_display_options
];

// selectors for replay control
var timestep_slider = "#timestep-slider-container";
var timesteps_per_render_input = "#timestepsPerRender";
var timesteps_per_second_input = "#timestepsPerSecond";
var enable_replay_checkbox = "#showReplay";
var replay_options = ".replay-option-container";
var overcooked_replay_container = "#overcooked";
var replay_containers = [overcooked_replay_container, timestep_slider, replay_options];

// selectors for chart control
var enable_trajectory_chart_checkbox = "#showTrajectoryChart";
var enable_trajectory_chart_legend_checkbox = "#showTrajectoryChartLegend"
var trajectory_chart_options = ".trajectory-chart-option-container";
var trajectory_chart = "#trajectory-chart";
var trajectory_chart_legend = "#trajectory-chart-legend";

// other selectors
var trajectory_display_options = ".trajectory-display-option-container";


//jquery utils functions
function is_checked(selector){
    return $(selector).is(":checked");
}

function show_many(selectors){
    selectors.forEach(function (selector, index){
        $(selector).show();
    });
}

function hide_many(selectors){
    selectors.forEach(function (selector, index){
        $(selector).hide();
    });
}

function show_or_hide_many_depended_on_checkbox(selectors, checkbox_selector){
    if (is_checked(checkbox_selector)){
        show_many(selectors);
    }
    else{
        hide_many(selectors);
    }

}



// replay params control methods
function get_selected_trajectory_filename(){
    filename = $(trajectories_file_input).children("option:selected").val();
    if (filename){
        filename = filename + ".json";
    }
    return filename;
}

function set_trajectory_idx(value){
    $(trajectory_idx_input).val(value);
}

function get_trajectory_idx(){
    return $(trajectory_idx_input).val();
}

function update_timesteps_per_render() {
    timesteps_per_render = $(timesteps_per_render_input).val();
    if (!paused) {
        start_auto_play();
    }
}

function update_timesteps_per_second() {
    timesteps_per_second = $(timesteps_per_second_input).val();
    if (!paused) {
        start_auto_play();
    }
}



// main replay functions methods
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
    $(timestep_slider).slider("value", current_frame);
}

function start_auto_play(){
    if (is_checked(enable_replay_checkbox)){
        end_auto_play();
        replay_step();
        replay_loop = setInterval(replay_step, (timesteps_per_render/timesteps_per_second)*1000);
    }
   
}

function end_auto_play(){
    if (typeof replay_loop !== 'undefined'){
        clearInterval(replay_loop);
    }
}



// socket communication utils
function send_trajectory_selected_event(filename, trajectory_idx){
    if (filename){ // empty filename is on the top of the list and means no trajectory selected
        socket.emit("trajectory_selected", {
            "trajectory_file": filename,
            "trajectory_idx": trajectory_idx
        });
    }
}



// event listeners for trajectory selection
$(function() {
    $(trajectories_file_input).change(function () {
        var trajectory_idx = 0;
        set_trajectory_idx(trajectory_idx);
        send_trajectory_selected_event(get_selected_trajectory_filename(), trajectory_idx);
    });
});

$(function() {
    $(trajectory_idx_input).change(function () {
        send_trajectory_selected_event(get_selected_trajectory_filename(), get_trajectory_idx());
    });
});

socket.on('replay_trajectory', function(data) {
    end_auto_play();
    paused = true;

    $(overcooked_replay_container).empty();

    show_many(objects_to_show_on_load_traj);
    show_or_hide_many_depended_on_checkbox(replay_containers, enable_replay_checkbox);
    show_or_hide_many_depended_on_checkbox([trajectory_chart_options, trajectory_chart, trajectory_chart_legend], enable_trajectory_chart_checkbox);

    
    update_timesteps_per_render();
    update_timesteps_per_second();
    if (graphics_is_started){
        graphics_end();
        graphics_is_started = false;
    }

    graphics_start({
        container_id : overcooked_replay_container.substring(1), // skip "#" character
        start_info : data.start_info
    });
    graphics_is_started = true;

    states = data.states;
    trajectory_chart_events = data.trajectory_chart_events;
    trajectory_chart_settings = data.trajectory_chart_settings;
    last_frame_idx = states.length-1;
   
    $(trajectory_chart).empty();
    $(trajectory_chart_legend).empty();
    render_event_chart(trajectory_chart_events, trajectory_chart, trajectory_chart_legend, trajectory_chart_settings);
    require(['d3', "jquery", "jquery-ui"], function(d3, jQuery, jQueryUI) {
        $(timestep_slider).slider({
            min: 0,
            max: last_frame_idx,
            value: 0,
            slide: function( event, ui ) {
                current_frame = ui.value;
                render_current_frame();
            }
          });
    });

    $(trajectory_idx_input).attr({
        "max" : data.max_trajectory_idx
    });    

});



// event listeners for control of replay
$(function() {
    $(enable_replay_checkbox).change(function () {
        if (is_checked(enable_replay_checkbox)){
            show_many(replay_containers);
        }
        else
        {
            hide_many(replay_containers);
            paused = true;
            end_auto_play();
        };

    });
});

$(function() {
    $(enable_trajectory_chart_checkbox).change(function () {
        if (is_checked(enable_trajectory_chart_checkbox)){
            $(trajectory_chart).show();
            show_or_hide_many_depended_on_checkbox([trajectory_chart_legend], 
                enable_trajectory_chart_legend_checkbox);
        }
        else {
            hide_many([trajectory_chart, trajectory_chart_legend]);
        }
    });
});

$(function() {
    $(timesteps_per_second_input).change(update_timesteps_per_second);
});

$(function() {
    $(timesteps_per_render_input).change(update_timesteps_per_render);
});



// event listeners for chart control
$(function() {
    $(enable_trajectory_chart_checkbox).change(function () {
        show_or_hide_many_depended_on_checkbox([trajectory_chart_options], enable_trajectory_chart_checkbox);
    });
});
$(function() {
    $(enable_trajectory_chart_legend_checkbox).change(function () {
        show_or_hide_many_depended_on_checkbox([trajectory_chart_legend], 
            enable_trajectory_chart_legend_checkbox)
    });
});



// keyboard event listeners
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
