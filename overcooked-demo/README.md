# Overcooked Demo
<p align="center">
<img src="https://i.imgur.com/Rk2Hp55.png" >
</p>

A web application where humans can play Overcooked with trained AI agents.

## Installation

Building the server image requires [Docker](https://docs.docker.com/get-docker/)

## Usage

The server can be deployed locally using the driver script included in the repo. To run the production server, use the command
```bash
./up.sh production
```

In order to build and run the development server, which includes a deterministic scheduler and helpful debugging logs, run
```bash
./up.sh
```

After running one of the above commands, navigate to https://localhost:8080 

### Converting models to overcooked-demo format

To convert Tensorflow models to a format in which they can be used by overcooked-demo, we used [tensorflow-js](https://github.com/tensorflow/tfjs) to convert our Tensorflow models saved with `simple_save` to models that could be served in the browser.

In particular, the way we converted the models in [Human Aware RL](https://github.com/HumanCompatibleAI/human_aware_rl) was by using `simple_save` [with this output format](https://github.com/HumanCompatibleAI/human_aware_rl/blob/master/human_aware_rl/ppo/ppo.py#L222) and then running `convert_model_to_web.sh` as documented in [the README](https://github.com/HumanCompatibleAI/human_aware_rl#converting-models-to-js-format).

### Issues

We have sometimes found the animation to break & behave weirdly (e.g. skip timesteps). This is usually caused by updates to the overcooked gridoworld code (such as switching branches or updating). Uninstalling both `overcooked_ai_js` and `overcooked-demo` and reinstalling them usually fixes the issue (simply restarting one's computer might help too).

### Updating gh-pages

To update gh-pages, remember that it might be necessary to link the overcooked_js repo again (if changes were made there too). Additionally, due to an [issue](https://github.com/HumanCompatibleAI/overcooked-demo/issues/14), one must go through all instances of paths containing "assets" in the demo.js and replay.js files and update them to "static/assets".

If you run into a bug getting something to work on the gh-pages branch, it's easier to first solve the issue locally, and then by following the step above it should also work on the gh-pages website.
