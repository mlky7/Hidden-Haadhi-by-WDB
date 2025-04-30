from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_pymongo import PyMongo
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models.user import User
from app_config import Config
import os
import logging
import numpy as np
from PIL import Image
import io
import base64
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Add this configuration
UPLOAD_FOLDER = os.path.join('static', 'images', 'avatars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize MongoDB
try:
    mongo = PyMongo(app)
    mongo.db.command('ping')
    logger.info("MongoDB connection successful")
except Exception as e:
    logger.error(f"MongoDB connection failed: {str(e)}")
    raise

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(mongo.db, user_id)

# Add this at the top with other imports
KNOWN_LOCATIONS = {
    "abbey_falls": "Kodagu",
    "baba_budangiri": "Chikkamagaluru",
    "bangalore_palace": "Bangalore",
    "brindavan_gardens": "Mysore",
    "chamundi_hills": "Mysore",
    "cubbon_park": "Bangalore",
    "hebbe_falls": "Chikkamagaluru",
    "lalbagh": "Bangalore",
    "mullayanagiri": "Chikkamagaluru",
    "mysore_palace": "Mysore",
    "rajas_seat": "Kodagu",
    "st_philomenas_church": "Mysore",
    "vidhana_soudha": "Bangalore",
    "unknown": "Other"
}

# Load class indices
CLASS_INDICES = {
    "abbey_falls": 0,
    "baba_budangiri": 1,
    "bangalore_palace": 2,
    "brindavan_gardens": 3,
    "chamundi_hills": 4,
    "cubbon_park": 5,
    "hebbe_falls": 6,
    "lalbagh": 7,
    "mullayanagiri": 8,
    "mysore_palace": 9,
    "rajas_seat": 10,
    "st_philomenas_church": 11,
    "vidhana_soudha": 12,
    "unknown": 13
}

# Root route
@app.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        location = request.form.get('location', '')
        avatar_file = request.files.get('avatar')
        
        if User.get_by_email(mongo.db, email):
            flash('Email already registered')
            return redirect(url_for('register'))
        
        # Validate avatar file if provided
        if avatar_file and avatar_file.filename:
            if not allowed_file(avatar_file.filename):
                flash('Invalid file type for avatar')
                return redirect(url_for('register'))
        
        # Create user with avatar if provided
        User.create_user(
            mongo.db,
            name=name,
            email=email,
            password=password,
            location=location,
            avatar_file=avatar_file if avatar_file and avatar_file.filename else None
        )
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.get_by_email(mongo.db, email)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    gallery = mongo.db.gallery.find({'user_id': current_user.get_id()})
    return render_template('dashboard.html', user=current_user.user_data, gallery=gallery)

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No image uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})

    try:
        # Read and preprocess the image
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        
        # Save the original image data
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_data = f"data:image/jpeg;base64,{base64.b64encode(img_io.getvalue()).decode()}"
        
        # TODO: Replace this with your actual model prediction
        # Your model should now return index 13 for unknown landmarks
        prediction_index = None  # This should come from your model
        
        # Convert prediction index to landmark name
        prediction = None
        for landmark, idx in CLASS_INDICES.items():
            if idx == prediction_index:
                prediction = landmark
                break
        
        # If prediction is None or unknown
        if prediction is None or prediction == "unknown":
            prediction = "Unknown Landmark"
            location = "Other"
            confidence = "Low"
        else:
            location = KNOWN_LOCATIONS.get(prediction)
            confidence = "95.5%"  # Replace with actual confidence from model
        
        # Store in MongoDB
        mongo.db.gallery.insert_one({
            'user_id': current_user.get_id(),
            'image': img_data,
            'prediction': prediction,  # Store as "Unknown Landmark" for unknown places
            'confidence': confidence,
            'location': location,
            'timestamp': datetime.now()
        })
        
        return jsonify({
            'success': True,
            'prediction': prediction,
            'confidence': confidence,
            'location': location
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/gallery/clear', methods=['POST'])
@login_required
def clear_gallery():
    mongo.db.gallery.delete_many({'user_id': current_user.get_id()})
    return jsonify({'success': True})

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(405)
def method_not_allowed(error):
    return render_template('405.html'), 405

if __name__ == '__main__':
    app.run(debug=True)











