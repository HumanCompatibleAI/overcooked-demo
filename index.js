var express = require('express');
var app = express();
var fs = require('fs');
var bodyParser = require('body-parser')

app.set('view engine', 'ejs');
app.use(express.static('static'))
app.use(bodyParser.json({limit: '10mb'}))

app.get('/', function(req, res) {
    res.render("demo");
});

app.get('/replay', function(req, res) {
    res.render("replay");
});

app.get('/instructions', function(req, res) {
    res.render("instructions");
});

app.post('/save_trajectory', function(req, res) {
    // NOTE: This method for saving trajectories in a directory is not currently used anymore
    
    let startTime = req.body.start_time;
    let gameType = req.body.game_type;
    
    // Looks like all the internal objects are getting stored as strings rather than actual arrays or objects
    // So it looks like Bodyparser only parses the top levl keys, and keeps everything on the lower level as strings rather 
    // than processing it recursively 

    let parsed_trajectory_data = {
	"ep_states": [[]], 
	"ep_rewards": [[]], 
	"ep_actions": [[]], 
	"mdp_params": []
    }
    parsed_trajectory_data['mdp_params'][0] = req.body.trajectory_data.mdp_params[0]; 
    ["ep_states", "ep_rewards", "ep_actions"].forEach(function(key, key_index) {
	req.body.trajectory_data[key][0].forEach(function(item, index) {
	    parsed_trajectory_data[key][0].push(JSON.parse(item))
	})
    })
    let fileName = "trajectories/" + startTime + "_" + gameType + ".json";
    fs.writeFile(fileName, JSON.stringify(parsed_trajectory_data), function(err) {
	if (err) {
	    res.status(404).send('Trajectory not saved');
      	    return;
	}
	res.send("Trajectory saved")
    })
})

console.log("You can now open overcooked-demo at http://localhost:8766");

app.listen(8766);
