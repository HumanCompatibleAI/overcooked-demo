# Relative path to where all static pre-trained agents are stored on server
AGENT_DIR = None

# Maximum allowable game time (in seconds)
MAX_GAME_TIME = None

# Maximum number of frames per second a game is allowed to run at
MAX_FPS = None

def _configure(max_game_time, agent_dir, max_fps):
    global AGENT_DIR, MAX_GAME_TIME, MAX_FPS
    MAX_GAME_TIME = max_game_time
    AGENT_DIR = agent_dir
    MAX_FPS = max_fps