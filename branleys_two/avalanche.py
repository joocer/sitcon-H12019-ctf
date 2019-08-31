from app import app, db
from app.models import User, Post
from waitress import serve

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}

serve(app, host='0.0.0.0', port=80)