import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
import time
import random

class ImageService:
    def __init__(self):
        load_dotenv()
        self.image_dir = os.path.join('static', 'cached_images')
        os.makedirs(self.image_dir, exist_ok=True)
        
        # Get API credentials from environment variables
        self.api_key = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY')
        self.search_engine_id = os.getenv('GOOGLE_CUSTOM_SEARCH_CX')  # Changed from GOOGLE_CUSTOM_SEARCH_ENGINE_ID
        
        if not self.api_key or not self.search_engine_id:
            raise ValueError("Google Custom Search API credentials not found in environment variables")
        
        self.backup_terms = {
            'hotel': ['hotel building', 'hotel exterior', 'hotel front view'],
            'resort': ['resort property', 'resort exterior', 'luxury resort'],
            'homestay': ['homestay house', 'guest house exterior', 'bed and breakfast'],
            'villa': ['villa exterior', 'luxury villa', 'vacation villa'],
            'cottage': ['cottage house', 'vacation cottage', 'rural cottage']
        }

    def search_image(self, query):
        """Search for an image using Google Custom Search API"""
        base_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'searchType': 'image',
            'imgSize': 'large',
            'imgType': 'photo',
            'num': 1
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'items' in data and len(data['items']) > 0:
                return data['items'][0]['link']
            return None
            
        except Exception as e:
            print(f"Error searching for image: {str(e)}")
            return None

    def download_and_save_image(self, image_url, cached_path):
        """Download and save an image from URL"""
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            with Image.open(BytesIO(response.content)) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                if max(img.size) > 1200:
                    img.thumbnail((1200, 1200))
                
                # Save with optimization
                img.save(cached_path, 'JPEG', quality=85, optimize=True)
            return True
            
        except Exception as e:
            print(f"Error downloading image: {str(e)}")
            return False

    def get_image_for_ecostay(self, stay_name, location):
        """Get image for an eco-stay using Google Custom Search"""
        
        # Create a clean filename
        filename = self._create_filename(stay_name, location)
        cached_path = os.path.join(self.image_dir, filename)
        
        # If image already exists, return its path
        if os.path.exists(cached_path):
            return os.path.join('cached_images', filename)
        
        # Generate search attempts
        search_attempts = [
            f"{stay_name} {location} hotel",
            f"{stay_name} {location} property",
            f"{stay_name} exterior {location}",
        ]
        
        # Add type-specific backup terms
        stay_type = self._determine_stay_type(stay_name.lower())
        if stay_type in self.backup_terms:
            search_attempts.extend([
                f"{stay_name} {term}" for term in self.backup_terms[stay_type]
            ])
        
        # Try each search term
        for search_term in search_attempts:
            try:
                # Search for image
                image_url = self.search_image(search_term)
                if not image_url:
                    continue
                
                # Download and save the image
                if self.download_and_save_image(image_url, cached_path):
                    return os.path.join('cached_images', filename)
                
                # Add delay between attempts
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                print(f"Error during attempt with '{search_term}': {str(e)}")
                continue
        
        return None

    def _create_filename(self, stay_name, location):
        """Create a clean filename from stay name and location"""
        clean_name = "".join(c for c in stay_name if c.isalnum() or c in (' ', '-'))
        clean_location = "".join(c for c in location if c.isalnum() or c in (' ', '-'))
        filename = f"{clean_name}_{clean_location}.jpg".lower()
        return filename.replace(' ', '_')

    def _determine_stay_type(self, stay_name):
        """Determine the type of stay based on the name"""
        if any(term in stay_name for term in ['hotel', 'ibis']):
            return 'hotel'
        elif any(term in stay_name for term in ['resort', 'spa']):
            return 'resort'
        elif any(term in stay_name for term in ['homestay', 'home stay', 'b&b']):
            return 'homestay'
        elif 'villa' in stay_name:
            return 'villa'
        elif 'cottage' in stay_name:
            return 'cottage'
        return 'hotel'  # default type

    def download_missing_images(self, json_data):
        """Download missing images from image_url in the JSON data"""
        downloaded = 0
        failed = 0
        
        for city, stays in json_data.items():
            print(f"\nProcessing {city}...")
            
            for stay in stays:
                # Skip if no image_url provided
                if not stay.get('image_url'):
                    continue
                
                # Create filename
                clean_name = "".join(c for c in stay['name'] if c.isalnum() or c in (' ', '-'))
                clean_location = "".join(c for c in stay['location'] if c.isalnum() or c in (' ', '-'))
                filename = f"{clean_name}_{clean_location}.jpg".lower().replace(' ', '_')
                cached_path = os.path.join(self.image_dir, filename)
                
                # Skip if image already exists
                if os.path.exists(cached_path):
                    continue
                
                print(f"Downloading image for: {stay['name']}")
                
                try:
                    # Download and save the image
                    if self.download_and_save_image(stay['image_url'], cached_path):
                        downloaded += 1
                        print(f"✓ Successfully downloaded image for {stay['name']}")
                    else:
                        failed += 1
                        print(f"✗ Failed to download image for {stay['name']}")
                    
                    # Add delay between downloads
                    time.sleep(random.uniform(1, 2))
                    
                except Exception as e:
                    failed += 1
                    print(f"✗ Error downloading image for {stay['name']}: {str(e)}")
                    continue
        
        return downloaded, failed

