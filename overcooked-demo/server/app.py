import os, pickle, queue, atexit
from utils import ThreadSafeSet, ThreadSafeDict
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from game import DummyGame

### Thoughts -- where I'll log potential issues/ideas as they come up
# Right now, if one user 'join's before other user's 'join' finishes, they won't end up in same game

###########
# Globals #
###########

# Maximum number of games that can run concurrently. Contrained by available memory
MAX_GAMES = 10

# Global queue of available IDs. This is how we synch game creation and keep track of how many games are in memory
FREE_IDS = queue.Queue(maxsize=MAX_GAMES)

# Bitmap that indicates whether ID is currently in use. Game with ID=i is "freed" by setting FREE_MAP[i] = True
FREE_MAP = ThreadSafeDict()

# Initialize our ID tracking data
for i in range(MAX_GAMES):
    FREE_IDS.put(i)
    FREE_MAP[i] = True

# Mapping of game-id to game objects
GAMES = ThreadSafeDict()

# Set of games IDs that are currently being played
ACTIVE_GAMES = ThreadSafeSet()

# Queue of games IDs that are waiting for additional players to join. Note that some of these IDs might
# be stale (i.e. if FREE_MAP[id] = True)
WAITING_GAMES = queue.Queue()

# Mapping of user id's to the current game (room) they are in
USER_ROOMS = ThreadSafeDict()





#######################
# Flask Configuration #
#######################

# Create and configure flask app
app = Flask(__name__, template_folder=os.path.join('static', 'templates'))
socketio = SocketIO(app, cors_allowed_origins="*")
app.config['DEBUG'] = os.getenv('FLASK_ENV', 'production') == 'development'




#################################
# Global Coordination Functions #
#################################

def try_create_game(**kwargs):
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
        game = DummyGame(id=curr_id, **kwargs)
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
    # User tracking
    for user_id in game.players:
        leave_curr_room(user_id)

    # Socketio tracking
    socketio.close_room(game.id)

    # Game tracking
    FREE_MAP[game.id] = True
    FREE_IDS.put(game.id)
    del GAMES[game.id]

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

def get_waiting_game():
    """
    Return a pointer to a waiting game, if one exists

    Note: The use of a queue ensures that no two threads will ever receive the same pointer, unless
    the waiting game's ID is re-added to the WAITING_GAMES queue
    """
    try:
        waiting_id = WAITING_GAMES.get(block=False)
        while FREE_MAP[waiting_id]:
            waiting_id = WAITING_GAMES.get(block=False)
    except queue.Empty:
        return None
    else:
        return get_game(waiting_id)

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
        return
    
    # Acquire this game's lock to ensure all global state updates are atomic
    with game.lock:
        # Update socket state maintained by socketio
        leave_room(game.id)

        # Update user data maintained by this app
        leave_curr_room(user_id)

        # Update game state maintained by game object
        game.remove_player(user_id)

        # Rebroadcast data and handle cleanup based on the transition caused by leaving
        if game.id in ACTIVE_GAMES and not game.is_empty():
            # Active -> Waiting
            ACTIVE_GAMES.remove(game.id)
            emit('end_game', room=game.id)
            cleanup_game(game)
        elif game.id in ACTIVE_GAMES and game.is_empty():
            # Active -> Empty
            ACTIVE_GAMES.remove(game.id)
            cleanup_game(game)
        elif not game.is_empty():
            # Waiting -> Waiting
            emit('waiting', room=game.id)
        else:
            # Waiting -> Empty
            cleanup_game(game)

def _create_game(user_id, params={}):
    game, err = try_create_game(**params)
    if not game:
        emit("creation_failed", { "error" : pickle.dumps(err) })
        return
    with game.lock:
        game.players.append(user_id)
        join_room(game.id)
        set_curr_room(user_id, game.id)
        if game.is_full():
            game.activate()
            ACTIVE_GAMES.add(game.id)
            emit('start_game', room=game.id)
            socketio.start_background_task(play_game, game)
        else:
            WAITING_GAMES.put(game.id)
            emit('waiting', room=game.id)

def _ensure_consistent_state():
    """
    Simple sanity checks of invariants on global state data

    Let ACTIVE be the set of all active game IDs, GAMES be the set of all existing
    game IDs, and WAITING be the set of all waiting (non-stale) game IDs. Note that
    a game could be in the WAITING_GAMES queue but no longer exist (indicated by 
    the FREE_MAP)

    - Intersection of WAITING and ACTIVE games must be empty set
    - Union of WAITING and ACTIVE must be equal to GAMES
    - id \in FREE_IDS => FREE_MAP[id] 
    """
    waiting_games = set()
    active_games = set()
    all_games = set(GAMES)

    for game_id in list(FREE_IDS.queue):
        assert FREE_MAP[game_id], "Freemap in inconsistent state"

    for game_id in list(WAITING_GAMES.queue):
        if not FREE_MAP[game_id]:
            waiting_games.add(game_id)

    for game_id in ACTIVE_GAMES:
        active_games.add(game_id)

    assert waiting_games.union(active_games) == all_games, "WAITING union ACTIVE != ALL"

    assert not waiting_games.intersection(active_games), "WAITING intersect ACTIVE != EMPTY"


######################
# Application routes #
######################

# Hitting each of these endpoints creates a brand new socket that is closed 
# at after the server response is received. Standard HTTP protocol

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/instructions')
def instructions():
    return render_template('instructions.html')

@app.route('/debug')
def debug():
    # TODO: Figure out if it is worth it to make this entire endpoint atomic
    resp = {}
    games = []
    active_games = []
    waiting_games = []
    users = []
    free_ids = []
    free_map = {}
    for game_id in ACTIVE_GAMES:
        game = get_game(game_id)
        active_games.append({"id" : game_id, "state" : game.get_state()})

    for game_id in list(WAITING_GAMES.queue):
        game = get_game(game_id)
        game_state = None if FREE_MAP[game_id] else game.get_state()
        waiting_games.append({ "id" : game_id, "state" : game_state})

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

    # Retrieve current game if one exists
    curr_game = get_curr_game(user_id)
    if curr_game:
        # Cannot create if currently in a game
        return
    
    params = data.get('params', {})
    _create_game(user_id, params)
    

@socketio.on('join')
def on_join(data):
    user_id = request.sid

    # Retrieve current game if one exists
    curr_game = get_curr_game(user_id)
    if curr_game:
        # Cannot join if currently in a game
        return
    
    # Retrieve a currently open game if one exists
    game = get_waiting_game()

    if not game:
        # No available game was found so create a default game
        _create_game(user_id)
        return
    
    with game.lock:
        join_room(game.id)
        set_curr_room(user_id, game.id)
        game.players.append(user_id)
            
        if game.is_full():
            # Game is ready to begin play
            game.activate()
            ACTIVE_GAMES.add(game.id)
            emit('start_game', room=game.id)
            socketio.start_background_task(play_game, game)
        else:
            # Still need to keep waiting for players
            WAITING_GAMES.put(game.id)
            emit('waiting', room=game.id)

@socketio.on('leave')
def on_leave(data):
    user_id = request.sid
    _leave_game(user_id)
    emit('end_game')


@socketio.on('connect')
def on_connect():
    # Currently a no-op, user authentification would happen here if necessary
    pass

@socketio.on('disconnect')
def on_disconnect():
    # Ensure game data is properly cleaned-up in case of unexpected disconnect
    user_id = request.sid
    _leave_game(user_id)




# Exit handler for server
def on_exit():
    # Force-terminate all games on server termination
    for game_id in GAMES:
        socketio.emit('end_game', room=game_id)




#############
# Game Loop #
#############

def play_game(game, fps=30):
    """
    Asynchronously apply real-time game updates and broadcast state to all clients currently active
    in the game. Note that this loop must be initiated by a parallel thread for each active game

    game (Game object):     Stores relevant game state. Note that the game id is the same as to socketio
                            room id for all clients connected to this game
    fps (int):              Number of game ticks that should happen every second
    """
    done = False
    while not done:
        with game.lock:
            done = game.tick()
        socketio.emit('state_pong', { "state" : game.get_state() }, room=game.id)
        socketio.sleep(1/fps)
    socketio.emit('end_game', room=game.id)
    with game.lock:
        ACTIVE_GAMES.remove(game.id)
        cleanup_game(game)



if __name__ == '__main__':
    # Dynamically parse host and port from environment variables (set by docker build)
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8080))

    # Attach exit handler to ensure graceful shutdown
    atexit.register(on_exit)

    # https://localhost:8080 is external facing address regardless of build environment
    socketio.run(app, host=host, port=port)