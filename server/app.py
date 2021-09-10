import os, traceback

# Import and patch the production eventlet server if necessary
if os.getenv('FLASK_ENV', 'production') == 'production':
    import eventlet
    eventlet.monkey_patch()

# All other imports must come after patch to ensure eventlet compatibility
import queue, atexit, json, logging, jsmin, copy
from threading import Lock
from collections import defaultdict
from concurrent_utils import ThreadSafeSet, ThreadSafeDict
from flask import Flask, render_template, jsonify, request, abort
from flask_socketio import SocketIO, join_room, leave_room, emit
from game.utils import GameError
from game.base import Game
from game import ConnectFourGame
import game as game_module


### Thoughts -- where I'll log potential issues/ideas as they come up
# Right now, if one user 'join's before other user's 'join' finishes, they won't end up in same game
# Could use a monitor on a conditional to block all global ops during calls to _ensure_consistent_state for debugging
# Could cap number of sinlge- and multi-player games separately since the former has much higher RAM and CPU usage

###########
# Globals #
###########

# Read in global config
CONF_PATH = os.getenv('CONF_PATH', 'config.json')
with open(CONF_PATH, 'r') as f:
    # Minify before parsing to remove comments
    CONFIG = json.loads(jsmin.jsmin(f.read()))

# Where errors will be logged
LOGFILE = CONFIG['logfile']

# Available layout names
LAYOUTS = CONFIG['layouts']

# Values that are standard across layouts
LAYOUT_GLOBALS = CONFIG['layout_globals']

# Maximum allowable game length (in seconds)
MAX_GAME_LENGTH = CONFIG['MAX_GAME_LENGTH']

# Path to where pre-trained agents will be stored on server
AGENT_DIR = CONFIG['AGENT_DIR']

# Maximum number of games that can run concurrently. Contrained by available memory and CPU
MAX_GAMES = CONFIG['MAX_GAMES']

# Frames per second cap for serving to client
MAX_FPS = CONFIG['MAX_FPS']

# Whether we should block non-psiturk traffic 
EXPERIMENT_MODE = CONFIG['EXPERIMENT_MODE']

# Referrer address of psiturk traffic
PSITURK_KEY = CONFIG['PSITURK_KEY']

# Default configuration for psiturk experiment
PSITURK_CONFIG = json.dumps(CONFIG['psiturk'])

# Default configuration for c4 psiturk experiment
C4_PSITURK_CONFIG = json.dumps(CONFIG['c4_psiturk'])

# Default configuration for tutorial
TUTORIAL_CONFIG = json.dumps(CONFIG['tutorial'])

# Global queue of available IDs. This is how we synch game creation and keep track of how many games are in memory
FREE_IDS = queue.Queue(maxsize=MAX_GAMES)

# Bitmap that indicates whether ID is currently in use. Game with ID=i is "freed" by setting FREE_MAP[i] = True
FREE_MAP = ThreadSafeDict()

# Initialize our ID tracking data
for i in range(MAX_GAMES):
    FREE_IDS.put(i)
    FREE_MAP[i] = True


# Mapping of string game names to corresponding classes
GAME_NAME_TO_CLS = {
    "c4" : ConnectFourGame,
    # "overcooked" : OvercookedGame,
    # "tutorial" : OvercookedTutorial,
    # "psiturk" : OvercookedPsiturk,
    # "psiturk_tutorial" : OvercookedTutorialPsiturk
}

GAME_TYPES = ThreadSafeSet(GAME_NAME_TO_CLS)

# Mapping of game-id to game objects
GAMES = ThreadSafeDict()

# Set of games IDs that are currently being played
ACTIVE_GAMES = ThreadSafeSet()

# Maps game type to Queue of games IDs that are waiting for additional players to join. Note that some of these IDs might
# be stale (i.e. if FREE_MAP[id] = True)
WAITING_GAMES = ThreadSafeDict()
for game_type in GAME_TYPES:
    WAITING_GAMES[game_type] = queue.Queue()

# Mapping of users to locks associated with the ID. Enforces user-level serialization
USERS = ThreadSafeDict()

# Mapping of user id's to the current game (room) they are in
USER_ROOMS = ThreadSafeDict()

# Sets global variables used by game.py
game_module._configure(MAX_GAME_LENGTH, AGENT_DIR, MAX_FPS)





#######################
# Flask Configuration #
#######################

# Create and configure flask app
app = Flask(__name__, template_folder=os.path.join('static', 'templates'))
# app.config['DEBUG'] = os.getenv('FLASK_ENV', 'production') == 'development'
app.config['DEBUG'] = False
socketio = SocketIO(app, cors_allowed_origins="*", logger=app.config['DEBUG'])


# Attach handler for logging errors to file
handler = logging.FileHandler(LOGFILE)
handler.setLevel(logging.ERROR)  
app.logger.addHandler(handler)  


#################################
# Global Coordination Functions #
#################################

def try_create_game(game_name ,**kwargs):
    """
    Tries to create a brand new Game object based on parameters in `kwargs`
    
    Returns (Game, Error) that represent a pointer to a game object, and error that occured
    during creation, if any. In case of error, `Game` returned in None. In case of sucess, 
    `Error` returned is None

    Possible Errors:
        - Runtime error if server is at max game capacity
        - Propogate any error that occured in game __init__ function
    """
    try:
        curr_id = FREE_IDS.get(block=False)
        assert FREE_MAP[curr_id], "Current id is already in use"
        game_cls = GAME_NAME_TO_CLS.get(game_name, ConnectFourGame)
        game = game_cls(id=curr_id, **kwargs)
    except queue.Empty:
        err = RuntimeError("Server at max capacity")
        return None, err
    except Exception as e:
        return None, e
    else:
        GAMES[game.id] = game
        FREE_MAP[game.id] = False
        return game, None

def cleanup_game(game):
    if FREE_MAP[game.id]:
        raise ValueError("Double free on a game")

    # User tracking
    for user_id in game.players:
        leave_curr_room(user_id)
    for user_id in game.spectators:
        leave_curr_room(user_id)

    # Socketio tracking
    socketio.close_room(game.id)

    # Game tracking
    FREE_MAP[game.id] = True
    FREE_IDS.put(game.id)
    del GAMES[game.id]

    if game.id in ACTIVE_GAMES:
        ACTIVE_GAMES.remove(game.id)

    try:
        if game.is_active():
            game.deactivate()
    except Exception:
        # TODO: figure out how to ensure the 'play_game' thread always exits
        pass

def get_game(game_id):
    return GAMES.get(game_id, None)

def get_curr_game(user_id):
    return get_game(get_curr_room(user_id))

def get_curr_room(user_id):
    return USER_ROOMS.get(user_id, None)

def set_curr_room(user_id, room_id):
    USER_ROOMS[user_id] = room_id

def leave_curr_room(user_id):
    del USER_ROOMS[user_id]

def get_waiting_game(game_type):
    """
    Return a pointer to a waiting game, if one exists

    Note: The use of a queue ensures that no two threads will ever receive the same pointer, unless
    the waiting game's ID is re-added to the WAITING_GAMES queue
    """
    try:
        waiting_id = WAITING_GAMES[game_type].get(block=False)
        while FREE_MAP[waiting_id]:
            waiting_id = WAITING_GAMES[game_type].get(block=False)
    except queue.Empty:
        return None
    else:
        return get_game(waiting_id)




##########################
# Socket Handler Helpers #
##########################

def  _leave_game(user_id):
    """
    Removes `user_id` from it's current game, if it exists. Rebroadcast updated game state to all 
    other users in the relevant game. 

    Leaving an active game force-ends the game for all other users, if they exist

    Leaving a waiting game causes the garbage collection of game memory, if no other users are in the
    game after `user_id` is removed
    """
    # Get pointer to current game if it exists
    game = get_curr_game(user_id)

    if not game:
        # Cannot leave a game if not currently in one
        return False
    
    try:
        # Acquire this game's lock to ensure all global state updates are atomic
        with game.lock:
            # Update socket state maintained by socketio
            leave_room(game.id)

            # Update user data maintained by this app
            leave_curr_room(user_id)

            # Update game state maintained by game object
            if user_id in game.players:
                game.remove_player(user_id)
            else:
                game.remove_spectator(user_id)
            
            # Whether the game was active before the user left
            was_active = game.id in ACTIVE_GAMES

            # Rebroadcast data and handle cleanup based on the transition caused by leaving
            if was_active and game.is_empty():
                # Active -> Empty
                game.deactivate()
            elif game.is_empty():
                # Waiting -> Empty
                cleanup_game(game)
            elif not was_active:
                # Waiting -> Waiting
                emit('waiting', { "in_game" : True }, room=game.id)
            elif was_active and game.is_ready():
                # Active -> Active
                pass
            elif was_active and not game.is_empty():
                # Active -> Waiting
                game.deactivate()

            return was_active

    except GameError as ge:
        emit("game_error", {"error" : traceback.format_exc()}, room=game.id)
        cleanup_game(game)
        return False

def _create_game(user_id, game_name, params={}):
    game, err = try_create_game(game_name, **params)
    if not game:
        emit("creation_failed", { "error" : err.__repr__() })
        return
    spectating = True
    try:
        with game.lock:
            if not game.is_full():
                spectating = False
                game.add_player(user_id)
            else:
                spectating = True
                game.add_spectator(user_id)
            join_room(game.id)
            set_curr_room(user_id, game.id)
            if game.is_ready():
                game.activate()
                ACTIVE_GAMES.add(game.id)
                emit('start_game', { "spectating" : spectating, "start_info" : game.to_json()}, room=game.id)
                socketio.start_background_task(play_game, game, game.fps)
            else:
                WAITING_GAMES[game_name].put(game.id)
                emit('waiting', { "in_game" : True }, room=game.id)
    except GameError as ge:
        emit("game_error", { "error" : traceback.format_exc() }, room=game.id)
        cleanup_game(game)




#####################
# Debugging Helpers #
#####################

def _ensure_consistent_state():
    """
    Simple sanity checks of invariants on global state data

    Let ACTIVE be the set of all active game IDs, GAMES be the set of all existing
    game IDs, and WAITING be the set of all waiting (non-stale) game IDs. Note that
    a game could be in the WAITING_GAMES queue but no longer exist (indicated by 
    the FREE_MAP)

    - Intersection of WAITING and ACTIVE games must be empty set
    - Union of WAITING and ACTIVE must be equal to GAMES
    - Union of WAITING[type_i] and WAITING[type_j] is empty set for i != j
    - id \in FREE_IDS => FREE_MAP[id] 
    - id \in ACTIVE_GAMES => Game in active state
    - id \in WAITING_GAMES => Game in inactive state
    """
    waiting_games = defaultdict(list)
    active_games = set()
    all_games = set(GAMES)

    for game_id in list(FREE_IDS.queue):
        assert FREE_MAP[game_id], "Freemap in inconsistent state"

    for game_name, q in WAITING_GAMES.items():
        for game_id in list(q.queue):
            if not FREE_MAP[game_id]:
                waiting_games[game_name].add(game_id)

    for game_id in ACTIVE_GAMES:
        active_games.add(game_id)

    assert set(waiting_games.values()).union(active_games) == all_games, "WAITING union ACTIVE != ALL"

    assert not set(waiting_games.values()).intersection(active_games), "WAITING intersect ACTIVE != EMPTY"

    assert all([get_game(g_id)._is_active for g_id in active_games]), "Active ID in waiting state"
    assert all([not get_game(g_id)._id_active for g_id in waiting_games]), "Waiting ID in active state"

    waiting_games_keys = list(waiting_games)
    for i in range(len(waiting_games_keys)):
        for j in range(i+1, len(waiting_games_keys)):
            key_i = waiting_games_keys[i]
            key_j = waiting_games_keys[j]
            assert not set(waiting_games[key_i]).union(waiting_games[key_j]), "WAITING id queues not disjoint"


def get_layout_to_agents():
    def _get_agents_names(layout):
        return [d for d in os.listdir(os.path.join(AGENT_DIR, layout)) if os.path.isdir(os.path.join(AGENT_DIR, layout, d))]
    layout_to_agent_names = {}
    for layout in LAYOUTS:
        layout_to_agent_names[layout] = _get_agents_names(layout) + _get_agents_names('all')
    return layout_to_agent_names


######################
# Application routes #
######################

# Hitting each of these endpoints creates a brand new socket that is closed 
# at after the server response is received. Standard HTTP protocol

@app.route('/')
def index():
    # Block all non-psiturk traffic if in experiment mode
    key = request.args.get('key', '')
    if EXPERIMENT_MODE and not key == PSITURK_KEY:
        abort(403)
    
    layout_to_agents = get_layout_to_agents()
    config = {
        "layouts" : LAYOUTS,
        "layout_to_agents" : layout_to_agents
    }
    return render_template('index.html', layouts=LAYOUTS, config=config)

@app.route('/psiturk')
def psiturk():
    # Block all non-psiturk traffic if in experiment mode
    key = request.args.get('key', '')
    if EXPERIMENT_MODE and not key == PSITURK_KEY:
        abort(403)
    
    uid = request.args.get("UID")
    ack_interval = request.args.get('ack_interval', -1)
    psiturk_config = request.args.get('config', copy.deepcopy(PSITURK_CONFIG))
    psiturk_config['uid'] = uid
    psiturk_config['ack_timeout'] = ack_interval
    return render_template('psiturk.html', config=psiturk_config)

@app.route('/instructions')
def instructions():
    # Block all non-psiturk traffic if in experiment mode
    key = request.args.get('key', '')
    if EXPERIMENT_MODE and not key == PSITURK_KEY:
        abort(403)

    psiturk = request.args.get('psiturk', False)
    return render_template('instructions.html', layout_conf=LAYOUT_GLOBALS, psiturk=psiturk)

@app.route('/c4')
def c4():
    # Block all non-psiturk traffic if in experiment mode
    key = request.args.get('key', '')
    if EXPERIMENT_MODE and not key == PSITURK_KEY:
        abort(403)
    
    layout_to_agents = get_layout_to_agents()
    config = {
        "foo" : "bar"
    }
    return render_template('c4.html', config=config)

@app.route('/c4psiturk')
def c4psiturk():
    # Block all non-psiturk traffic if in experiment mode
    key = request.args.get('key', '')
    if EXPERIMENT_MODE and not key == PSITURK_KEY:
        abort(403)

    uid = request.args.get("UID")
    ack_interval = request.args.get('ack_interval', -1)
    psiturk_config = request.args.get('config', copy.deepcopy(C4_PSITURK_CONFIG))
    psiturk_config['uid'] = uid
    psiturk_config['ack_timeout'] = ack_interval
    return render_template('c4_psiturk.html', config=psiturk_config)

@app.route('/tutorial')
def tutorial():
    # Block all non-psiturk traffic if in experiment mode
    key = request.args.get('key', '')
    if EXPERIMENT_MODE and not key == PSITURK_KEY:
        abort(403)
    
    uid = request.args.get("UID", "-1")
    psiturk = request.args.get('psiturk', False)
    ack_interval = request.args.get('ack_interval', -1)
    tutorial_config = request.args.get('config', copy.deepcopy(TUTORIAL_CONFIG))
    tutorial_config['uid'] = uid
    tutorial_config['psiturk'] = psiturk
    tutorial_config['ack_interval'] = ack_interval
    return render_template('tutorial.html', config=tutorial_config, psiturk=psiturk)

@app.route('/debug')
def debug():
    resp = {}
    games = []
    active_games = []
    waiting_games = defaultdict(list)
    users = []
    free_ids = []
    free_map = {}
    for game_id in ACTIVE_GAMES:
        game = get_game(game_id)
        active_games.append({"id" : game_id, "state" : game.to_json()})

    for game_type in WAITING_GAMES:
        for game_id in list(WAITING_GAMES[game_type].queue):
            game = get_game(game_id)
            game_state = None if FREE_MAP[game_id] else game.to_json()
            waiting_games[game_type].append({ "id" : game_id, "state" : game_state})

    for game_id in GAMES:
        games.append(game_id)

    for user_id in USER_ROOMS:
        users.append({ user_id : get_curr_room(user_id) })

    for game_id in list(FREE_IDS.queue):
        free_ids.append(game_id)

    for game_id in FREE_MAP:
        free_map[game_id] = FREE_MAP[game_id]

    
    resp['active_games'] = active_games
    resp['waiting_games'] = waiting_games
    resp['all_games'] = games
    resp['users'] = users
    resp['free_ids'] = free_ids
    resp['free_map'] = free_map
    return jsonify(resp)

@app.route('/health')
def health():
    return "Healthy!", 200


#########################
# Socket Event Handlers #
#########################

# Asynchronous handling of client-side socket events. Note that the socket persists even after the 
# event has been handled. This allows for more rapid data communication, as a handshake only has to 
# happen once at the beginning. Thus, socket events are used for all game updates, where more rapid
# communication is needed

@socketio.on('create')
def on_create(data):
    user_id = request.sid

    try:
        with USERS[user_id]:
            # Retrieve current game if one exists
            curr_game = get_curr_game(user_id)
            if curr_game:
                # Cannot create if currently in a game
                return
            
            params = data.get('params', {})
            game_name = data.get('game_name', 'overcooked')
            _create_game(user_id, game_name, params)
    except Exception as e:
        emit("server_error", { "error" : traceback.format_exc() })
    

@socketio.on('join')
def on_join(data):
    user_id = request.sid

    try:
        with USERS[user_id]:
            create_if_not_found = data.get("create_if_not_found", True)
            game_type = data.get('game_name', None)

            if not game_type or not game_type in GAME_TYPES:
                # User must provide valid game type
                return

            # Retrieve current game if one exists
            curr_game = get_curr_game(user_id)
            if curr_game:
                # Cannot join if currently in a game
                return
            
            # Retrieve a currently open game if one exists
            game = get_waiting_game(game_type)

            if not game and create_if_not_found:
                # No available game was found so create a game
                params = data.get('params', {})
                _create_game(user_id, game_type, params)
                return

            elif not game:
                # No available game was found so start waiting to join one
                emit('waiting', { "in_game" : False })
            else:
                try:
                    # Game was found so join it
                    with game.lock:

                        join_room(game.id)
                        set_curr_room(user_id, game.id)
                        game.add_player(user_id)
                            
                        if game.is_ready():
                            # Game is ready to begin play
                            game.activate()
                            ACTIVE_GAMES.add(game.id)
                            emit('start_game', { "spectating" : False, "start_info" : game.to_json()}, room=game.id)
                            socketio.start_background_task(play_game, game, game.fps)
                        else:
                            # Still need to keep waiting for players
                            WAITING_GAMES[game_type].put(game.id)
                            emit('waiting', { "in_game" : True }, room=game.id)
                except GameError as ge:
                    emit("game_error", { "error" : traceback.format_exc() }, room=game.id)
                    cleanup_game(game)
    except Exception as e:
        emit("server_error", { "error" : traceback.format_exc() })

@socketio.on('leave')
def on_leave(data):
    user_id = request.sid
    with USERS[user_id]:
        was_active = _leave_game(user_id)

        if was_active:
            emit('end_game', { "status" : Game.Status.DONE, "data" : {}})
        else:
            emit('end_lobby')

@socketio.on('action')
def on_action(data):
    user_id = request.sid
    action = data['action']

    game = get_curr_game(user_id)
    if not game:
        return
    
    game.enqueue_action(user_id, action)


@socketio.on('connect')
def on_connect():
    user_id = request.sid

    try:
        if user_id in USERS:
            return

        USERS[user_id] = Lock()
    except Exception as e:
        emit("server_error", { "error" : traceback.format_exc() })

@socketio.on('disconnect')
def on_disconnect():
    # Ensure game data is properly cleaned-up in case of unexpected disconnect
    user_id = request.sid

    try:
        if user_id not in USERS:
            return
        with USERS[user_id]:
            _leave_game(user_id)

        del USERS[user_id]
    except Exception as e:
        emit("server_error", { "error" : traceback.format_exc() })




# Exit handler for server
def on_exit():
    # Force-terminate all games on server termination
    for game_id in GAMES:
        socketio.emit('end_game', { "status" : Game.Status.INACTIVE, "data" : json.dumps(get_game(game_id).get_data()) }, room=game_id)




#############
# Game Loop #
#############

def play_game(game, fps=MAX_FPS):
    """
    Asynchronously apply real-time game updates and broadcast state to all clients currently active
    in the game. Note that this loop must be initiated by a parallel thread for each active game

    game (Game object):     Stores relevant game state. Note that the game id is the same as to socketio
                            room id for all clients connected to this game
    fps (int):              Number of game ticks that should happen every second
    """
    try:
        fps = min(fps, MAX_FPS)
        status = Game.Status.ACTIVE
        while status != Game.Status.DONE and status != Game.Status.INACTIVE:
            with game.lock:
                status = game.tick()
            if status == Game.Status.RESET:
                with game.lock:
                    data = game.get_data()
                socketio.emit('reset_game', { "state" : game.to_json(), "timeout" : game.reset_timeout, "data" : json.dumps(data)}, room=game.id)
                socketio.sleep(game.reset_timeout/1000)
            else:
                socketio.emit('state_pong', { "state" : game.get_state() }, room=game.id)
            socketio.sleep(1/fps)
        
        with game.lock:
            data = game.get_data()
            socketio.emit('end_game', { "status" : status, "data" : json.dumps(data) }, room=game.id)

            if status != Game.Status.INACTIVE:
                game.deactivate()
            cleanup_game(game)
    
    except GameError as ge:
        data = []

        # Try to recover any data possible
        try:
            data = game.get_data()
        except Exception:
            pass

        socketio.emit("game_error", {"error" : traceback.format_exc(), "data" : json.dumps(data) }, room=game.id)
        cleanup_game(game)
    except Exception as e:
        socketio.emit("server error", {"error" : traceback.format_exc() }, room=game.id)




if __name__ == '__main__':
    # Dynamically parse host and port from environment variables (set by docker build)
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 80))

    # Attach exit handler to ensure graceful shutdown
    atexit.register(on_exit)

    # https://localhost:80 is external facing address regardless of build environment
    socketio.run(app, host=host, port=port, log_output=app.config['DEBUG'])