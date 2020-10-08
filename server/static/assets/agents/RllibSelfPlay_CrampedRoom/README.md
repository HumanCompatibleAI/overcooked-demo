# Example Directory for Pre-trained Rllib Agent

## Structure

* `agent`  
  * `agent`
  * `agent.tune_metadata`
  * `config.pkl`

Note that the file names must match EXACTLY the names and relative structure as above. The agent name is only determined and reflected in the parent directory name.

In the future, the naming convenction will probably be more flexible, but for now it is very strict to simplify serialization logic

## Training the Agent

A directory with the structure above can be trained with the [human_aware_rl](https://github.com/HumanCompatibleAI/human_aware_rl) repo. 

Please follow the [conda environment setup guide](https://github.com/HumanCompatibleAI/human_aware_rl#conda-environment-setup) to setup `harl_rllib` conda env. 

After `harl_rllib` is successfully installed and activated, please run something along the line of

```
(harl_rllib) $ python human_aware_rl/ppo/ppo_rllib_client.py with experiment_name="MyAgent"
```

This might create a directory such as  `~/ray_results/MyAgent_0_2020-09-24_01-24-43m6jg7brh/checkpoint_<i>`. Note the timestamp and id will vary.

For reproducibility, the command used to generate this sepcific `RllibSelfPlay_CrampedRoom` agent is
```
(harl_rllib) $ python human_aware_rl/ppo/ppo_rllib_client.py with num_workers=16 train_batch_size=12800 sgd_minibatch_size=8000 num_training_iters=300 evaluation_interval=20 use_phi=False entropy_coeff_start=0.2 entropy_coeff_end=0.0005 num_sgd_iter=8 lr=1e-3 seeds=[0]
```
And we are using `checkpoint_300`


## Moving the Agent into Demo

You can move this agent into Overcooked-Demo by running
```
cd  <Overcooked-Demo-Root>/server/static/assets/agents/
mkdir RllibMyAgent
```
Note that all rllib agnet directory names must match the regex pattern `/rllib.*/i`

Now copy over the appropriate files

```
cp -r ~/ray_results/MyAgent_0_2020-09-24_01-24-43m6jg7brh/checkpoint_<i> ./RllibMyAgent/agent
```

And then rename the necessary files

```
cd ./RllibMyAgent/agent
mv checkpoint_<i> agent
mv checkoint_<i>.tune_metadata agent.tune_metadata
```

Relaunching the Overcooked-Demo server, you should now see `RllibMyAgent` in the dropdown of available agents

## Layout Compatibility

Please ensure that agents trained on layout `<X>` are only run on layout `<X>`. Attempting to run such an agent on layout `<Y>` will either result in very poor performance, or, if observation dimensions are mismatched, the thread executing the agent's actions will fail silently and the agent will remain stationary for the entire duration of the game! We recommend including the compatible layout names in the agent name, for example `RllibPPOSelfPlay_CounterCircuit` is a name of one of our trained agents. 
