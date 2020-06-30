import os, pickle, queue
from utils import ThreadSafeSet, ThreadSafeDict
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from game import DummyGame

# Maximum number of games that can run concurrently. Contrained by available memory
MAX_GAMES = 10

FREE_IDS = queue.Queue(maxsize=MAX_GAMES)
FREE_MAP = ThreadSafeDict()

for i in range(MAX_GAMES):
    FREE_IDS.put(i)
    FREE_MAP[i] = True

# Mapping of game-id to game objects
GAMES = ThreadSafeDict()

# Set of games IDs that are currently being played
ACTIVE_GAMES = ThreadSafeSet()

# Queue of games IDs that are waiting for additional players to join
WAITING_GAMES = queue.Queue()

# Mapping of user id's to the current game (room) they are in
USER_ROOMS = ThreadSafeDict()

app = Flask(__name__, template_folder=os.path.join('static', 'templates'))
socketio = SocketIO(app, cors_allowed_origins="*")
app.config['DEBUG'] = os.getenv('FLASK_ENV', 'production') == 'development'

def try_create_game(**kwargs):
    try:
        curr_id = FREE_IDS.get(block=False)
        assert FREE_MAP[curr_id], "Current id is already in use"
    except queue.Empty:
        err = RuntimeError("Server at max capacity")
        return None, err
    except Exception as e:
        return None, e
    else:
        game = DummyGame(id=curr_id, **kwargs)
        GAMES[game.id] = game
        FREE_MAP[game.id] = False
        return game, None

def cleanup_game(game):
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
    try:
        waiting_id = WAITING_GAMES.get(block=False)
        while FREE_MAP[waiting_id]:
            waiting_id = WAITING_GAMES.get(block=False)
    except queue.Empty:
        return None
    else:
        return get_game(waiting_id)

def  _leave_game(user_id):
    game = get_curr_game(user_id)

    if not game:
        return
    with game.lock:
        leave_room(game.id)
        leave_curr_room(user_id)
        game.remove_player(user_id)
        if game.id in ACTIVE_GAMES and not game.is_empty():
            # Active -> Waiting
            ACTIVE_GAMES.remove(game.id)
            emit('end_game', room=game.id)
            cleanup_game(game)
        elif game.id in ACTIVE_GAMES and game.is_empty():
            # Active -> Empty
            ACTIVE_GAMES.remove(game.id)
            emit('end_game', room=game.id)
            cleanup_game(game)
        elif not game.is_empty():
            # Waiting -> Waiting
            emit('waiting', room=game.id)
        else:
            # Waiting -> Empty
            emit('end_game', room=game.id)
            cleanup_game(game)



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

@app.route('/debuglobby')
def debug_lobby():
    resp = {}
    games = []
    active_games = []
    waiting_games = []
    for game_id in ACTIVE_GAMES:
        game = get_game(game_id)
        active_games.append(game.get_state())
        games.append(game.get_state())

    for game_id in list(WAITING_GAMES.queue):
        game = get_game(game_id)
        waiting_games.append(game.get_state())
        games.append(game.get_state())
    
    resp['active_games'] = active_games
    resp['waiting_games'] = waiting_games
    resp['all_games'] = games
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
    params = data.get('params', {})
    game, err = try_create_game(**params)
    if not game:
        emit("creation_failed", { "error" : pickle.dumps(err) })
        return
    with game.lock:
        game.players.append(user_id)
        join_room(game.id)
        set_curr_room(user_id, game.id)
        print("game players", game.players)
        print("is game full? ", game.is_full())
        if game.is_full():
            game.activate()
            ACTIVE_GAMES.add(game.id)
            emit('start_game', room=game.id)
            socketio.start_background_task(play_game, game)
        else:
            WAITING_GAMES.put(game.id)
            emit('waiting', room=game.id)

@socketio.on('join')
def on_join(data):
    user_id = request.sid
    game = get_waiting_game()
    if not game:
        emit('waiting')
        return
    
    with game.lock:
        join_room(game.id)
        set_curr_room(user_id, game.id)
        game.players.append(user_id)
            
        if game.is_full():
            game.activate()
            ACTIVE_GAMES.add(game.id)
            emit('start_game', room=game.id)
            socketio.start_background_task(play_game, game)
        else:
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
    cleanup_game(game)



if __name__ == '__main__':
    # Dynamically parse host and port from environment variables (set by docker build)
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8080))

    # https://localhost:8080 is external facing address regardless of build environment
    socketio.run(app, host=host, port=port)