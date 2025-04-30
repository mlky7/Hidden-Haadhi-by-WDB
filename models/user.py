from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import os
import uuid

class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data

    def get_id(self):
        return str(self.user_data.get('_id'))

    @property
    def is_authenticated(self):
        return True

    @staticmethod
    def save_avatar(avatar_file):
        if not avatar_file:
            return 'avatar.jpg'
        
        # Generate unique filename
        filename = f"{uuid.uuid4()}{os.path.splitext(avatar_file.filename)[1]}"
        upload_path = os.path.join('static', 'images', 'avatars', filename)
        
        # Ensure upload directory exists
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        
        # Save the file
        avatar_file.save(upload_path)
        return f"images/avatars/{filename}"  # Return relative path from static folder

    @staticmethod
    def create_user(db, name, email, password, location='', avatar_file=None):
        avatar_path = User.save_avatar(avatar_file)
        
        user = {
            'name': name,
            'email': email,
            'password': generate_password_hash(password),
            'joined_date': datetime.now(),
            'location': location,
            'profile_image': avatar_path
        }
        return db.users.insert_one(user)

    @staticmethod
    def get_by_email(db, email):
        user_data = db.users.find_one({'email': email})
        return User(user_data) if user_data else None

    @staticmethod
    def get_by_id(db, user_id):
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None

    def check_password(self, password):
        return check_password_hash(self.user_data['password'], password)

    @property
    def joined_date_formatted(self):
        return self.user_data['joined_date'].strftime('%B %Y')

    @property
    def name(self):
        return self.user_data.get('name', '')

    @property
    def location(self):
        return self.user_data.get('location', '')

    @property
    def joined_date(self):
        return self.user_data.get('joined_date')

    @property
    def profile_image(self):
        return self.user_data.get('profile_image', 'images/avatars/default-avatar.png')

    def to_dict(self):
        return {
            'name': self.name,
            'location': self.location,
            'joined_date': self.joined_date,
            'profile_image': self.profile_image
        }


