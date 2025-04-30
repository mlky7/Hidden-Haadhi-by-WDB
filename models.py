from datetime import datetime
from bson import ObjectId

class GalleryImage:
    def __init__(self, user_id, image_path, prediction=None, confidence=None, location=None):
        self.user_id = user_id
        self.image_path = image_path
        self.prediction = prediction
        self.confidence = confidence
        self.location = location
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'image_path': self.image_path,
            'prediction': self.prediction,
            'confidence': self.confidence,
            'location': self.location,
            'timestamp': self.timestamp
        }

    @staticmethod
    def from_dict(data):
        image = GalleryImage(
            user_id=data['user_id'],
            image_path=data['image_path'],
            prediction=data.get('prediction'),
            confidence=data.get('confidence'),
            location=data.get('location')
        )
        image.timestamp = data.get('timestamp', datetime.now())
        return image