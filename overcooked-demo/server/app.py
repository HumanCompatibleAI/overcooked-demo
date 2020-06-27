import os
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__, template_folder=os.path.join('static', 'templates'))
socketio = SocketIO(app, cors_allowed_origins="*")

app.config['DEBUG'] = os.getenv('FLASK_ENV', 'production') == 'development'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/instructions')
def instructions():
    return render_template('instructions.html')

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8080))
    socketio.run(app, host=host, port=port)