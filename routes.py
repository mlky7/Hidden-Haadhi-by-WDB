from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime

gallery_bp = Blueprint('gallery', __name__, url_prefix='/gallery')

@gallery_bp.route('/')
def index():  # Changed from gallery_home to index
    return render_template('gallery/galleryhome.html')

@gallery_bp.route('/view')
@login_required
def view():
    gallery = current_app.mongo.db.gallery.find({'user_id': current_user.get_id()})
    return render_template('gallery/index.html', gallery=list(gallery))

@gallery_bp.route('/predict', methods=['POST'])
@login_required
def predict():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['file']
    if not file:
        return jsonify({'success': False, 'error': 'No file selected'})

    try:
        # Process image
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        
        # Convert to base64 for storage
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_data = f"data:image/jpeg;base64,{base64.b64encode(img_io.getvalue()).decode()}"
        
        # Store in MongoDB
        current_app.mongo.db.gallery.insert_one({
            'user_id': current_user.get_id(),
            'image': img_data,
            'prediction': 'Sample Prediction',  # Replace with actual prediction
            'confidence': '95%',  # Replace with actual confidence
            'location': 'Karnataka',  # Replace with actual location
            'timestamp': datetime.now()
        })
        
        return jsonify({
            'success': True,
            'prediction': 'Sample Prediction',
            'confidence': '95%',
            'location': 'Karnataka'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@gallery_bp.route('/clear', methods=['POST'])
@login_required
def clear_gallery():
    current_app.mongo.db.gallery.delete_many({'user_id': current_user.get_id()})
    return jsonify({'success': True})






