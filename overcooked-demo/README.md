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

In order to kill the production server, run
```bash
./down.sh
```

The branch of `overcooked_ai` imported in both the development and production server can be specified by the `OVERCOOKED_BRANCH` build arg in docker-compose.development.yml and docker-compose.production.yml, respectively

## Using Pre-trained Agents

Overcooked-Demo can dynamically load pre-trained agents provided by the user. In order to use a pre-trained agent, a pickle file should be added to the `agents` directory. The final structure will look like `static/assets/agents/<agent_name>/agent.pickle`

If a more complex loading routing is necessary, one can subclass the `OvercookedGame` class and override the `get_policy` method, as done in [DummyOvercookedGame](server/game.py#L420)


