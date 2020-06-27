# Overcooked Demo
<p align="center">
<img src="https://i.imgur.com/Rk2Hp55.png" >
</p>

A web application where humans can play Overcooked with trained AI agents.

## Installation

First, install `node` and `npm`, and ensure that you have set up the [overcooked_ai repository](https://github.com/HumanCompatibleAI/overcooked_ai).
Also, install browserify globally, by calling: 

    $ npm install -g browserify

Clone the repo:

    $ git clone https://github.com/HumanCompatibleAI/overcooked-demo.git
    $ cd overcooked-demo

Install using `npm`:

    overcooked-demo $ npm install

Link to the javascript version of the environment code ([this](https://github.com/HumanCompatibleAI/overcooked_ai/tree/master/overcooked_ai_js)). Linking will warn you about vulnerabilities in `overcooked_ai_js`.

    overcooked-demo $ npm link /path/to/overcooked_ai_js/

(If you installed `overcooked_ai` and `overcooked-demo` in the same directory, then you would run `npm link ../overcooked_ai/overcooked_ai_js/`.)

Then build the code:

    overcooked-demo $ npm run build

At this point the code should be ready to run. Start the server with

    overcooked-demo $ node index.js

at which point you should be able to load the website in any browser by going to [http://localhost:8766](http://localhost:8766). At the root directory, you can play the game against pre-trained agents, or watch these agents play each other. At [http://localhost:8766/replay](http://localhost:8766/replay), you can watch replays of fixed trajectories.

If you intend to develop further, we recommend using `nodemon` to avoid having to manually restart the server after making changes:

    $ npm install -g nodemon

Then run the server with `nodemon index.js`.

### Converting models to overcooked-demo format

To convert Tensorflow models to a format in which they can be used by overcooked-demo, we used [tensorflow-js](https://github.com/tensorflow/tfjs) to convert our Tensorflow models saved with `simple_save` to models that could be served in the browser.

In particular, the way we converted the models in [Human Aware RL](https://github.com/HumanCompatibleAI/human_aware_rl) was by using `simple_save` [with this output format](https://github.com/HumanCompatibleAI/human_aware_rl/blob/master/human_aware_rl/ppo/ppo.py#L222) and then running `convert_model_to_web.sh` as documented in [the README](https://github.com/HumanCompatibleAI/human_aware_rl#converting-models-to-js-format).

### Issues

We have sometimes found the animation to break & behave weirdly (e.g. skip timesteps). This is usually caused by updates to the overcooked gridoworld code (such as switching branches or updating). Uninstalling both `overcooked_ai_js` and `overcooked-demo` and reinstalling them usually fixes the issue (simply restarting one's computer might help too).

### Updating gh-pages

To update gh-pages, remember that it might be necessary to link the overcooked_js repo again (if changes were made there too). Additionally, due to an [issue](https://github.com/HumanCompatibleAI/overcooked-demo/issues/14), one must go through all instances of paths containing "assets" in the demo.js and replay.js files and update them to "static/assets".

If you run into a bug getting something to work on the gh-pages branch, it's easier to first solve the issue locally, and then by following the step above it should also work on the gh-pages website.
