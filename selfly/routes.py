# routes.py
import os
from flask import Blueprint, render_template, request, redirect, url_for, session, abort, send_from_directory, current_app, jsonify
from functools import wraps
from database import get_user_by_username, get_user_by_id, add_new_user, get_user_directories, get_db_connection, check_for_users, get_all_users, delete_user, update_user_password, update_user_admin_status, get_setting, add_setting
from werkzeug.utils import secure_filename
from PIL import Image # For image metadata
import requests # For uploading to external services
import base64 # For Base64 encoding for ImageBB

# Create a Blueprint for the main routes
main_bp = Blueprint('main', __name__)

# --- Utility Functions ---

def allowed_file(filename):
    """Check if a file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    """A decorator to protect routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """A decorator to protect routes that only admins can access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_user_by_id(session.get('user_id'))
        if not user or not user['is_admin']:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

# Helper function to render templates with common context
def render_page(template, **kwargs):
    username = None
    is_admin = False
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            username = user['username']
            is_admin = bool(user['is_admin'])
    return render_template(template, username=username, is_admin=is_admin, **kwargs)

def get_user_media(user_id):
    """Scans the user's directories and returns a list of media files."""
    user_media = []
    user_dirs = get_user_directories(user_id)
    if not user_dirs:
        return []

    photo_dir = user_dirs['photo_dir']
    if photo_dir and os.path.exists(photo_dir):
        for filename in os.listdir(photo_dir):
            if allowed_file(filename) and not filename.endswith(('mp4', 'mov', 'avi')):
                user_media.append(filename)

    video_dir = user_dirs['video_dir']
    if video_dir and os.path.exists(video_dir):
        for filename in os.listdir(video_dir):
            if allowed_file(filename) and filename.endswith(('mp4', 'mov', 'avi')):
                user_media.append(filename)
    
    # Reverse the list to show the most recent files first
    return sorted(user_media, reverse=True)


# --- Routes ---

@main_bp.route('/')
def home():
    """Redirects to the dashboard if logged in, otherwise to login."""
    if check_for_users() == 0:
        return redirect(url_for('main.first_admin_signup'))
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)
        if user and user['password'] == password:
            session['user_id'] = user['id']
            return redirect(url_for('main.dashboard'))
        else:
            return render_page('login.html', error='Invalid credentials.')
    return render_page('login.html')

@main_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles user sign up."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        photo_dir = request.form['photo_dir']
        video_dir = request.form['video_dir']
        if add_new_user(username, password, photo_dir, video_dir):
            user = get_user_by_username(username)
            session['user_id'] = user['id']
            return redirect(url_for('main.dashboard'))
        else:
            return render_page('signup.html', error='Username already exists.')
    return render_page('signup.html')

@main_bp.route('/first-admin-signup', methods=['GET', 'POST'])
def first_admin_signup():
    """Handles the initial signup for the first user, who is automatically an admin."""
    if check_for_users() > 0:
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        photo_dir = request.form['photo_dir']
        video_dir = request.form['video_dir']
        if add_new_user(username, password, photo_dir, video_dir, is_admin=True):
            user = get_user_by_username(username)
            session['user_id'] = user['id']
            return redirect(url_for('main.dashboard'))
        else:
            return render_page('first_admin_signup.html', error='Username already exists.')
    return render_page('first_admin_signup.html')

@main_bp.route('/logout')
@login_required
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user_id', None)
    return redirect(url_for('main.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Displays the user's uploaded files from their configured directories."""
    # We will only load the first page of files here
    files = get_user_media(session['user_id'])
    
    # Determine the number of files per page
    per_page = 20
    first_page_files = files[:per_page]
    has_more = len(files) > per_page

    return render_page('dashboard.html', files=first_page_files, has_more=has_more)

@main_bp.route('/api/media')
@login_required
def api_media():
    """API endpoint for endless scrolling, returning a paginated list of media."""
    user_id = session['user_id']
    all_files = get_user_media(user_id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    start = (page - 1) * per_page
    end = start + per_page
    
    paginated_files = all_files[start:end]

    has_more = end < len(all_files)
    
    return jsonify({
        'files': paginated_files,
        'has_more': has_more
    })

@main_bp.route('/api/metadata/<filename>')
@login_required
def get_metadata(filename):
    """API endpoint to get metadata for a specific image file."""
    user = get_user_by_id(session['user_id'])
    user_dirs = get_user_directories(user['id'])
    
    # Check if the file is a photo
    if not filename.endswith(('png', 'jpg', 'jpeg', 'gif')):
        abort(400, description="Invalid file type for metadata.")

    # Get the file path
    file_path = os.path.join(user_dirs['photo_dir'], filename)
    if not os.path.exists(file_path):
        abort(404)

    # Use Pillow to get image metadata
    try:
        with Image.open(file_path) as img:
            metadata = {
                'Filename': filename,
                'Dimensions': f"{img.width}x{img.height}",
                'Format': img.format,
                'Mode': img.mode,
                'Size': f"{os.path.getsize(file_path) / (1024 * 1024):.2f} MB",
            }
            # You can add more metadata here if needed
            return jsonify(metadata)
    except Exception as e:
        current_app.logger.error(f"Error reading metadata for {filename}: {e}")
        abort(500, description="Could not read file metadata.")


@main_bp.route('/api/upload-public/<filename>', methods=['POST'])
@login_required
def upload_public(filename):
    """
    API endpoint to upload a file to a public, free image host (ImageBB) and return the link.
    WARNING: This makes the image public.
    """
    user = get_user_by_id(session['user_id'])
    user_dirs = get_user_directories(user['id'])

    file_path = os.path.join(user_dirs['photo_dir'], filename)
    if not os.path.exists(file_path):
        abort(404)
        
    # Open the file and encode it in Base64
    try:
        with open(file_path, 'rb') as f:
            encoded_string = base64.b64encode(f.read()).decode('utf-8')
        
        # ImageBB API endpoint and API key
        api_key = get_setting('imagebb_api_key')
        if not api_key:
            abort(500, description="ImageBB API key not configured. Please set it in admin settings.")

        api_url = f"https://api.imgbb.com/1/upload?key={api_key}"
        
        # Send the Base64 encoded image to ImageBB
        payload = {'image': encoded_string}
        response = requests.post(api_url, data=payload)
        response.raise_for_status() # Raise an exception for bad status codes

        result = response.json()
        if result['success']:
            public_link = result['data']['url']
            return jsonify({'public_link': public_link})
        else:
            current_app.logger.error(f"ImageBB upload failed: {result.get('error', {}).get('message', 'Unknown error')}")
            abort(500, description="Failed to upload image to public service.")
            
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Failed to upload {filename} to ImageBB: {e}")
        abort(500, description="Failed to upload image to public service.")


@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    """Handles file uploads by saving them to the user's configured directory."""
    user = get_user_by_id(session['user_id'])
    user_dirs = get_user_directories(user['id'])
    if not user_dirs:
        abort(500, description="User directories not configured.")
        
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        
        # Determine the correct directory based on file type
        if filename.endswith(('mp4', 'mov', 'avi')):
            upload_dir = user_dirs['video_dir']
        else:
            upload_dir = user_dirs['photo_dir']
            
        if upload_dir and os.path.exists(upload_dir):
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            return redirect(url_for('main.dashboard'))
        else:
            abort(500, description="Upload directory not found or configured.")

    return render_page('upload.html')

@main_bp.route('/media/<path:filename>')
@login_required
def serve_media(filename):
    """Serves media files directly from the configured directories."""
    user = get_user_by_id(session['user_id'])
    user_dirs = get_user_directories(user['id'])
    if not user_dirs:
        abort(403)
    
    photo_dir = user_dirs['photo_dir']
    video_dir = user_dirs['video_dir']

    # Check if the file is in the user's photo or video directory
    if photo_dir and os.path.exists(os.path.join(photo_dir, filename)):
        return send_from_directory(photo_dir, filename)
    elif video_dir and os.path.exists(os.path.join(video_dir, filename)):
        return send_from_directory(video_dir, filename)
    
    # If the file is not found in the user's directories, return 404
    abort(404)

@main_bp.route('/view/<path:filename>')
@login_required
def view_media(filename):
    """Displays a single photo or video."""
    user = get_user_by_id(session['user_id'])
    user_dirs = get_user_directories(user['id'])
    if not user_dirs:
        abort(403)

    photo_dir = user_dirs['photo_dir']
    video_dir = user_dirs['video_dir']
    
    # Check if the user has permissions to view the file
    is_owner = (photo_dir and os.path.exists(os.path.join(photo_dir, filename))) or \
               (video_dir and os.path.exists(os.path.join(video_dir, filename)))
    
    if not is_owner and not user['is_admin']:
        abort(403)
        
    return render_page('view_media.html', filename=filename)

@main_bp.route('/delete/<path:filename>')
@login_required
def delete_file(filename):
    """Deletes a file if the user has permission."""
    user = get_user_by_id(session['user_id'])
    if not user:
        abort(403)

    user_dirs = get_user_directories(user['id'])
    if not user_dirs:
        abort(403)
        
    photo_dir = user_dirs['photo_dir']
    video_dir = user_dirs['video_dir']

    # Check if the user is the owner or an admin
    file_path = None
    if photo_dir and os.path.exists(os.path.join(photo_dir, filename)):
        file_path = os.path.join(photo_dir, filename)
    elif video_dir and os.path.exists(os.path.join(video_dir, filename)):
        file_path = os.path.join(video_dir, filename)
        
    if file_path and (user['is_admin'] or os.path.dirname(file_path) in [photo_dir, video_dir]):
        os.remove(file_path)
    else:
        abort(403) # Forbidden
            
    return redirect(url_for('main.dashboard'))

@main_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Displays a simple admin page with a list of all uploads from all configured directories."""
    all_photos = []
    # Find all users and their directories
    users = get_all_users()
    for user_row in users:
        user_dirs = get_user_directories(user_row['id'])
        if user_dirs:
            if user_dirs['photo_dir'] and os.path.exists(user_dirs['photo_dir']):
                for filename in os.listdir(user_dirs['photo_dir']):
                    if allowed_file(filename) and not filename.endswith(('mp4', 'mov', 'avi')):
                        all_photos.append({'filename': filename, 'username': user_row['username']})
            if user_dirs['video_dir'] and os.path.exists(user_dirs['video_dir']):
                for filename in os.listdir(user_dirs['video_dir']):
                    if allowed_file(filename) and filename.endswith(('mp4', 'mov', 'avi')):
                        all_photos.append({'filename': filename, 'username': user_row['username']})
    
    return render_page('admin.html', photos=all_photos, all_users=users)

@main_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    """Displays a page for admin-level settings."""
    if request.method == 'POST':
        imagebb_api_key = request.form.get('imagebb_api_key')
        add_setting('imagebb_api_key', imagebb_api_key)
        return redirect(url_for('main.admin_dashboard'))

    current_api_key = get_setting('imagebb_api_key')
    return render_page('admin_settings.html', current_api_key=current_api_key)


@main_bp.route('/admin/create_user', methods=['POST'])
@login_required
@admin_required
def create_user_admin():
    username = request.form['username']
    password = request.form['password']
    photo_dir = request.form['photo_dir']
    video_dir = request.form['video_dir']
    is_admin = 'is_admin' in request.form
    add_new_user(username, password, photo_dir, video_dir, is_admin)
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/delete_user/<int:user_id>')
@login_required
@admin_required
def delete_user_admin(user_id):
    if user_id != session['user_id']: # Prevent an admin from deleting themselves
        delete_user(user_id)
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/change_password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def change_password_admin(user_id):
    new_password = request.form['new_password']
    update_user_password(user_id, new_password)
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/toggle_admin/<int:user_id>')
@login_required
@admin_required
def toggle_admin_status(user_id):
    user = get_user_by_id(user_id)
    if user:
        new_status = not user['is_admin']
        update_user_admin_status(user_id, new_status)
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/api-docs')
def api_docs():
    """Displays a simple API documentation page."""
    return render_page('api_docs.html')
