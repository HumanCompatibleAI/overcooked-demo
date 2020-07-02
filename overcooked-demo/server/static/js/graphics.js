var TIMESTEP_DURATION = 200;

var DIRECTION_TO_NAME = {
    '0,-1': 'NORTH',
    '0,1': 'SOUTH',
    '1,0': 'EAST',
    '-1,0': 'WEST'
};

var scene_config = {
    player_colors : {0: 'green', 1: 'blue'},
    tileSize : 80,
    animation_duration : TIMESTEP_DURATION * .9,
    show_post_cook_time : false,
    cook_time : 20
};

var game_config = {
    type: Phaser.WEBGL,
    parent: "overcooked",
    pixelArt: true,
    audio: {
        noAudio: true
    }
};

var graphics;

function drawState(state) {
    graphics.set_state(state);
};

function graphics_start(start_info) {
    graphics = new GraphicsManager(game_config, scene_config, start_info);
};

function graphics_end() {
    graphics.game.renderer.destroy();
    graphics.game.loop.stop();
    graphics.game.destroy();
}

class GraphicsManager {
    constructor(game_config, scene_config, start_info) {
        scene_config.terrain = start_info.terrain;
        scene_config.start_state = start_info.state;
        game_config.scene = new OvercookedScene(scene_config);
        game_config.gameWidth = scene_config.tileSize*scene_config.terrain[0].length;
        game_config.gameHeight = scene_config.tileSize*scene_config.terrain.length;
        this.game = new Phaser.Game(game_config);
    }

    set_state(state) {
        this.game.scene.getAt(0).set_state(state);
    }
}

class OvercookedScene extends Phaser.Scene {
    constructor(config) {
        super({key: "PlayGame"});
        this.state = config.start_state.state;
        this.score = config.start_state.score;
        this.time = config.start_state.time;
        this.player_colors = config.player_colors;
        this.terrain = config.terrain;
        this.tileSize = config.tileSize;
        this.animation_duration = config.animation_duration;
        this.show_post_cook_time = config.show_post_cook_time;
        this.cook_time = config.cook_time
    }

    set_state(state) {
        this.state = state.state;
        this.score = state.score;
        this.time = state.time;
    }

    preload() {
        this.load.atlas("tiles",
            "./assets/terrain.png",
            "./assets/terrain.json");
        this.load.atlas("chefs",
            "./assets/chefs.png",
            "./assets/chefs.json");
        this.load.atlas("objects",
            "./assets/objects.png",
            "./assets/objects.json");
    }

    create() {
        this.sprites = {};
        this.drawLevel();
        this._drawState(curr_state, this.sprites);
    }

    update() {
        if (typeof(this.state) !== 'undefined') {
            this._drawState(this.state, this.sprites);
        }
        if (typeof(this.score) !== 'undefined') {
            this._drawScore(this.score, this.sprites);
        }
        if (typeof(this.time) !== 'undefined') {
            this._drawTimeLeft(this.time, this.sprites);
        }
    }
    drawLevel() {
        //draw tiles
        let terrain_to_img = {
            ' ': 'floor.png',
            'X': 'counter.png',
            'P': 'pot.png',
            'O': 'onions.png',
            'T': 'tomatoes.png',
            'D': 'dishes.png',
            'S': 'serve.png'
        };
        let pos_dict = this.terrain;
        for (let ttype in pos_dict) {
            if (!pos_dict.hasOwnProperty(ttype)) {continue}
            for (let i = 0; i < pos_dict[ttype].length; i++) {
                let [x, y] = pos_dict[ttype][i];
                let tile = this.add.sprite(
                    tileSize * x,
                    tileSize * y,
                    "tiles",
                    terrain_to_img[ttype]
                );
                tile.setDisplaySize(tileSize, tileSize);
                tile.setOrigin(0);
            }
        }
    }
    _drawState (state, sprites) {
        sprites = typeof(sprites) === 'undefined' ? {} : sprites;

        //draw chefs
        sprites['chefs'] =
            typeof(sprites['chefs']) === 'undefined' ? {} : sprites['chefs'];
        for (let pi = 0; pi < state.players.length; pi++) {
            let chef = state.players[pi];
            let [x, y] = chef.position;
            let dir = DIRECTION_TO_NAME[chef.orientation];
            let held_obj = chef.held_object;
            if (typeof(held_obj) !== 'undefined') {
                if (held_obj.name === 'soup') {
                    held_obj = "-soup-"+held_obj.state[0];
                }
                else {
                    held_obj = "-"+held_obj.name;
                }
            }
            else {
                held_obj = "";
            }
            if (typeof(sprites['chefs'][pi]) === 'undefined') {
                let chefsprite = this.add.sprite(
                    this.tileSize*x,
                    this.tileSize*y,
                    "chefs",
                    `${dir}${held_obj}.png`
                );
                chefsprite.setDisplaySize(tileSize, tileSize);
                chefsprite.depth = 1;
                chefsprite.setOrigin(0);
                let hatsprite = this.add.sprite(
                    tileSize*x,
                    tileSize*y,
                    "chefs",
                    `${dir}-${this.player_colors[pi]}hat.png`
                );
                hatsprite.setDisplaySize(tileSize, tileSize);
                hatsprite.depth = 2;
                hatsprite.setOrigin(0);
                sprites['chefs'][pi] = {chefsprite, hatsprite};
            }
            else {
                let chefsprite = sprites['chefs'][pi]['chefsprite'];
                let hatsprite = sprites['chefs'][pi]['hatsprite'];
                chefsprite.setFrame(`${dir}${held_obj}.png`);
                hatsprite.setFrame(`${dir}-${this.player_colors[pi]}hat.png`);
                this.tweens.add({
                    targets: [chefsprite, hatsprite],
                    x: this.tileSize*x,
                    y: this.tileSize*y,
                    duration: this.animation_duration,
                    ease: 'Linear',
                    onComplete: (tween, target, player) => {
                        target[0].setPosition(this.tileSize*x, this.tileSize*y);
                        //this.animating = false;
                    }
                })
            }
        }

        //draw environment objects
        if (typeof(sprites['objects']) !== 'undefined') {
            for (let objpos in sprites.objects) {
                let {objsprite, timesprite} = sprites.objects[objpos];
                objsprite.destroy();
                if (typeof(timesprite) !== 'undefined') {
                    timesprite.destroy();
                }
            }
        }
        sprites['objects'] = {};

        for (let objpos in state.objects) {
            if (!state.objects.hasOwnProperty(objpos)) { continue }
            let obj = state.objects[objpos];
            let [x, y] = obj.position;
            let terrain_type = this.terrain;
            let spriteframe, souptype, n_ingredients;
            let cooktime = "";
            if ((obj.name === 'soup') && (terrain_type === 'P')) {
                [souptype, n_ingredients, cooktime] = obj.state;

                // select pot sprite
                if (cooktime < this.cook_time) {
                    spriteframe =
                        `soup-${souptype}-${n_ingredients}-cooking.png`;
                }
                else {
                    spriteframe = `soup-${souptype}-cooked.png`;
                }
                let objsprite = this.add.sprite(
                    this.tileSize*x,
                    this.tileSize*y,
                    "objects",
                    spriteframe
                );
                objsprite.setDisplaySize(this.tileSize, this.tileSize);
                objsprite.depth = 1;
                objsprite.setOrigin(0);
                let objs_here = {objsprite};

                // show time accordingly
                let show_time = true;
                if ((cooktime > this.mdp.COOK_TIME) && !this.show_post_cook_time) {
                    show_time = false;
                }
                if (show_time) {
                    let timesprite =  this.add.text(
                        this.tileSize*(x+.5),
                        this.tileSize*(y+.6),
                        String(cooktime),
                        {
                            font: "25px Arial",
                            fill: "red",
                            align: "center",
                        }
                    );
                    timesprite.depth = 2;
                    objs_here['timesprite'] = timesprite;
                }

                sprites['objects'][objpos] = objs_here
            }
            else if (obj.name === 'soup') {
                [souptype, n_ingredients, cooktime] = obj.state;
                spriteframe = `soup-${souptype}-dish.png`;
                let objsprite = this.add.sprite(
                    this.tileSize*x,
                    this.tileSize*y,
                    "objects",
                    spriteframe
                );
                objsprite.setDisplaySize(this.tileSize, this.tileSize);
                objsprite.depth = 1;
                objsprite.setOrigin(0);
                sprites['objects'][objpos] = {objsprite};
            }
            else {
                if (obj.name === 'onion') {
                    spriteframe = "onion.png";
                }
                else if (obj.name === 'tomato') {
                    spriteframe = "tomato.png";
                }
                else if (obj.name === 'dish') {
                    spriteframe = "dish.png";
                }
                let objsprite = this.add.sprite(
                    this.tileSize*x,
                    this.tileSize*y,
                    "objects",
                    spriteframe
                );
                objsprite.setDisplaySize(this.tileSize, this.tileSize);
                objsprite.depth = 1;
                objsprite.setOrigin(0);
                sprites['objects'][objpos] = {objsprite};
            }
        }

        //draw order list
        if (state.order_list !== null) {
            let order_list = "Orders: "+state.order_list.join(", ");
            if (typeof(sprites['order_list']) !== 'undefined') {
                sprites['order_list'].setText(order_list);
            }
            else {
                sprites['order_list'] = this.add.text(
                    5, 45, order_list,
                    {
                        font: "20px Arial",
                        fill: "yellow",
                        align: "left"
                    }
                )
            }
        }
        
    }

    _drawScore(score, sprites) {
        score = "Score: "+score;
        if (typeof(sprites['score']) !== 'undefined') {
            sprites['score'].setText(score);
        }
        else {
            sprites['score'] = this.add.text(
                5, 25, score,
                {
                    font: "20px Arial",
                    fill: "yellow",
                    align: "left"
                }
            )
        }
    }

    _drawTimeLeft(time_left, sprites) {
        time_left = "Time Left: "+time_left;
        if (typeof(sprites['time_left']) !== 'undefined') {
            sprites['time_left'].setText(time_left);
        }
        else {
            sprites['time_left'] = this.add.text(
                5, 5, time_left,
                {
                    font: "20px Arial",
                    fill: "yellow",
                    align: "left"
                }
            )
        }
    }
}

