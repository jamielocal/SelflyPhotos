# app.py
from flask import Flask
from routes import main_bp
from database import init_db

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = 'changethistoasuperlongcomplexstringpleaseunlessitsalreadyonelol' # Change this to a random, complex string

# Define allowed file extensions for uploads
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

# Register the blueprint
app.register_blueprint(main_bp)

# Initialize the database
init_db()

# --- Entry Point for the Application ---
if __name__ == '__main__':
    app.run(debug=False, port=8000)
