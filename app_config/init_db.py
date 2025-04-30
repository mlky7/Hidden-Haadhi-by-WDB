from pymongo import MongoClient
from pymongo.errors import CollectionInvalid
import os
from dotenv import load_dotenv

load_dotenv()

def init_database():
    # Connect to MongoDB
    client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/karnataka_places'))
    db = client.karnataka_places

    # Create collections if they don't exist
    try:
        db.create_collection('users')
    except CollectionInvalid:
        print("Users collection already exists")

    try:
        db.create_collection('gallery')
    except CollectionInvalid:
        print("Gallery collection already exists")

    # Create indexes
    db.users.create_index('email', unique=True)
    db.gallery.create_index('user_id')

    # Create validation rules
    db.command({
        'collMod': 'users',
        'validator': {
            '$jsonSchema': {
                'bsonType': 'object',
                'required': ['name', 'email', 'password'],
                'properties': {
                    'name': {
                        'bsonType': 'string',
                        'description': 'must be a string and is required'
                    },
                    'email': {
                        'bsonType': 'string',
                        'pattern': '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$',
                        'description': 'must be a valid email address and is required'
                    },
                    'password': {
                        'bsonType': 'string',
                        'description': 'must be a string and is required'
                    },
                    'joined_date': {
                        'bsonType': 'date',
                        'description': 'must be a date'
                    },
                    'profile_image': {
                        'bsonType': 'string',
                        'description': 'must be a string'
                    }
                }
            }
        }
    })

    db.command({
        'collMod': 'gallery',
        'validator': {
            '$jsonSchema': {
                'bsonType': 'object',
                'required': ['user_id', 'image', 'prediction', 'confidence', 'timestamp'],
                'properties': {
                    'user_id': {
                        'bsonType': 'string',
                        'description': 'must be a string and is required'
                    },
                    'image': {
                        'bsonType': 'string',
                        'description': 'must be a base64 string and is required'
                    },
                    'prediction': {
                        'bsonType': 'string',
                        'description': 'must be a string and is required'
                    },
                    'confidence': {
                        'bsonType': 'string',
                        'description': 'must be a string and is required'
                    },
                    'timestamp': {
                        'bsonType': 'date',
                        'description': 'must be a date and is required'
                    }
                }
            }
        }
    })

    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()
