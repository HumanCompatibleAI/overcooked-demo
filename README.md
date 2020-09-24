# Overcooked Demo
<p align="center">
<img src="./server/static/images/browser_view.png" >
</p>

A web application where humans can play Overcooked with trained AI agents.

* [Installation](#installation)
* [Usage](#usage)
* [Dependencies](#dependencies)
* [Using Pre-trained Agents](#using-pre-trained-agents)
* [Updating Overcooked_ai](#updating-overcooked_ai)
* [Configuration](#configuration)
* [Legacy Code](#legacy-code)

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

After running one of the above commands, navigate to http://localhost

In order to kill the production server, run
```bash
./down.sh
```

## Dependencies

The Overcooked-Demo server relies on both the [overcooked-ai](https://github.com/HumanCompatibleAI/overcooked_ai) and [human-aware-rl](https://github.com/HumanCompatibleAI/human_aware_rl) repos. The former contains the game logic, the latter contains the rl training code required for managing agents. Both repos are automatically cloned and installed in the Docker builds.

The branch of `overcooked_ai` and `human_aware_rl` imported in both the development and production servers can be specified by the `OVERCOOKED_BRANCH` and `HARL_BRANCH` environment variables, respectively. For example, to use the branch `foo` from `overcooked-ai` and branch `bar` from `human_aware_rl`, run
```bash
OVERCOOKED_BRANCH=foo HARL_BRANCH=bar ./up.sh
```
The default branch for both repos is currently `master`.

## Using Pre-trained Agents

Overcooked-Demo can dynamically load pre-trained agents provided by the user. In order to use a pre-trained agent, a pickle file should be added to the `agents` directory. The final structure will look like `static/assets/agents/<agent_name>/agent.pickle`. Note, to use the pre-defined rllib loading routine, the agent directory name must start with 'rllib', and contain the appropriate rllib checkpoint, config, and metadata files. For more detailed info and instructions see the [RllibDummy](server/static/assets/agents/RllibDummy/) example agent.

If a more complex or custom loading routing is necessary, one can subclass the `OvercookedGame` class and override the `get_policy` method, as done in [DummyOvercookedGame](server/game.py#L420). Make sure the subclass is properly imported [here](server/app.py#L5)

## Updating Overcooked_ai
This repo was designed to be as flexible to changes in overcooked_ai as possible. To change the branch used, use the `OVERCOOKED_BRANCH` environment variable shown above.

Changes to the JSON state representation of the game will require updating the JS graphics. At the highest level, a graphics implementation must implement the functions `graphics_start`, called at the start of each game, `graphics_end`, called at the end of each game, and `drawState`, called at every timestep tick. See [dummy_graphcis.js](server/graphics/dummy_graphics.js) for a barebones example.

The graphics file is dynamically loaded into the docker container and served to the client. Which file is loaded is determined by the `GRAPHICS` environment variable. For example, to server `dummy_graphics.js` one would run
```bash
GRAPHICS=dummy_graphics.js ./up.sh
```
The default graphics file is currently `overcooked_graphics_v2.1.js`


## Configuration

Basic game settings can be configured by changing the values in [config.json](server/config.json)

## Legacy Code

For legacy code compatible with the Neurips2019 submission please see [this](https://github.com/HumanCompatibleAI/overcooked-demo/tree/legacy) branch of this repo. 