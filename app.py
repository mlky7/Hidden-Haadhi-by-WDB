import requests
from datetime import datetime
import google.generativeai as genai
import csv
import random
import time
import subprocess
import json
import platform
from bson.json_util import dumps
from bson import ObjectId
from bson.objectid import ObjectId
from services.whatsapp_service import WhatsAppService
from services.email_service import EmailService
import smtplib
from difflib import get_close_matches
from services.image_service import ImageService
from flask_pymongo import PyMongo
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import logging
import numpy as np
from PIL import Image
import io
import base64
from datetime import datetime
import sys
import os
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_cors import CORS
from models.user import User
from dotenv import load_dotenv
import tensorflow as tf
from tensorflow.keras.preprocessing.image import img_to_array
import numpy as np
import json
from services.speedtest_service import SpeedtestService


# Load class indices
try:
    with open("class_indices.json", "r") as f:
        CLASS_INDICES = json.load(f)
except FileNotFoundError:
    print("Warning: class_indices.json not found")
    CLASS_INDICES = {}

# Define known locations mapping
KNOWN_LOCATIONS = {
    "abbey_falls": "Kodagu, Karnataka",
    "baba_budangiri": "Chikkamagaluru, Karnataka",
    "bangalore_palace": "Bangalore, Karnataka",
    "brindavan_gardens": "Mysore, Karnataka",
    "chamundi_hills": "Mysore, Karnataka",
    "cubbon_park": "Bangalore, Karnataka",
    "hebbe_falls": "Chikkamagaluru, Karnataka",
    "lalbagh": "Bangalore, Karnataka",
    "mullayanagiri": "Chikkamagaluru, Karnataka",
    "mysore_palace": "Mysore, Karnataka",
    "rajas_seat": "Kodagu, Karnataka",
    "st_philomenas_church": "Mysore, Karnataka",
    "vidhana_soudha": "Bangalore, Karnataka"
}

def calculate_transport_emissions(transport, distance):
    # Emission factors in kg CO2 per km
    emission_factors = {
        'train': 0.041,
        'bus': 0.089,
        'car': 0.171,
        'electric_car': 0.053,
        'hybrid_car': 0.111,
        'plane_economy': 0.255,
        'plane_business': 0.399,
        'bicycle': 0
    }
    
    return round(distance * emission_factors.get(transport, 0), 2)

def calculate_accommodation_emissions(accommodation, nights):
    # Emission factors in kg CO2 per night
    emission_factors = {
        'hotel': 29.53,
        'hostel': 12.2,
        'eco_lodge': 8.0,
        'camping': 2.5
    }
    
    return round(nights * emission_factors.get(accommodation, 0), 2)

model_path = os.path.join('static', 'karnataka_places_model.h5')
tf_model = tf.keras.models.load_model(model_path)
speedtest_service = SpeedtestService()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Define Config class directly in app.py
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/karnataka_places')
    
    # Ensure MONGO_URI starts with mongodb://
    if MONGO_URI and not (MONGO_URI.startswith('mongodb://') or MONGO_URI.startswith('mongodb+srv://')):
        MONGO_URI = f'mongodb://{MONGO_URI}'
    
    # Gallery configuration
    UPLOAD_FOLDER = os.path.join('static', 'uploads', 'gallery')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size



app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24)  # Required for flash messages

# Load API keys
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
AIRQUALITY_API_KEY = os.getenv('AIRQUALITY_API_KEY')  # Get from OpenWeatherMap or similar service

def initialize_gemini():
    """Initialize the Gemini model with enhanced error handling"""
    if not GOOGLE_GEMINI_API_KEY:
        print("Warning: Gemini API key not found in environment variables")
        return None
    
    try:
        genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
        
        model_names = ['models/gemini-1.5-pro', 'models/gemini-1.5-pro-latest']
        
        for name in model_names:
            try:
                model = genai.GenerativeModel(name)
                
                # Test connection with a simple prompt
                try:
                    response = model.generate_content("Test connection")
                    if response and hasattr(response, 'text'):
                        print(f"Successfully connected to Gemini API using model: {name}")
                        return model
                except Exception as conn_error:
                    print(f"Connection test failed for {name}: {str(conn_error)}")
                    continue
                    
            except Exception as model_error:
                print(f"Failed to initialize model {name}: {str(model_error)}")
                continue
                
        return None
        
    except Exception as e:
        print(f"Failed to initialize Gemini API: {str(e)}")
        return None
model = initialize_gemini()

whatsapp_service = WhatsAppService()

email_service = EmailService()

image_service = ImageService()

def test_email_config():
    """Test email configuration on startup"""
    try:
        with smtplib.SMTP(email_service.smtp_server, email_service.smtp_port, timeout=5) as server:
            server.starttls(timeout=5)
            server.login(email_service.smtp_username, email_service.smtp_password)
            print("Email configuration test: SUCCESS")
            return True
    except smtplib.SMTPException as e:
        print(f"Email configuration test: FAILED - SMTP Error: {str(e)}")
        return False
    except TimeoutError:
        print("Email configuration test: FAILED - Connection timeout")
        return False
    except Exception as e:
        print(f"Email configuration test: FAILED - {str(e)}")
        return False

@app.route('/')
def home():
    return render_template('homepage.html')  # Changed to homepage.html

@app.route('/map')
def map():
    if not GOOGLE_MAPS_API_KEY:
        return render_template('error.html', error="Google Maps API key not configured")
    print(f"Using API key: {GOOGLE_MAPS_API_KEY[:10]}...") # Debug log (first 10 chars only)
    return render_template('map.html', api_key=GOOGLE_MAPS_API_KEY)

@app.route('/network-coverage')
def network_coverage():
    if not GOOGLE_MAPS_API_KEY:
        return render_template('error.html', 
                             error="Google Maps API key not configured")
    return render_template('network.html', 
                         api_key=GOOGLE_MAPS_API_KEY,
                         page_title="Network Coverage Checker")

@app.route('/calculate_footprint', methods=['GET', 'POST'])  # Change from calculate-footprint to calculate_footprint
def calculate_footprint():
    if request.method == 'POST':
        try:
            # Get form data
            transport = request.form.get('transport')
            distance = float(request.form.get('distance', 0))
            nights = int(request.form.get('nights', 0))
            accommodation = request.form.get('accommodation')
            
            # Calculate emissions
            transport_emissions = calculate_transport_emissions(transport, distance)
            accommodation_emissions = calculate_accommodation_emissions(accommodation, nights) if nights > 0 else 0
            total_emissions = round(transport_emissions + accommodation_emissions, 2)
            
            # Prepare data for email
            footprint_data = {
                'transport': transport,
                'distance': distance,
                'transport_emissions': transport_emissions,
                'accommodation': accommodation,
                'nights': nights,
                'accommodation_emissions': accommodation_emissions,
                'total_emissions': total_emissions,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return render_template('calculate_footprint.html',
                                distance=distance,
                                transport=transport,
                                accommodation=accommodation,
                                nights=nights,
                                transport_emissions=transport_emissions,
                                accommodation_emissions=accommodation_emissions,
                                total_emissions=total_emissions,
                                footprint_data=footprint_data)
                                
        except Exception as e:
            flash(f'Error calculating footprint: {str(e)}')
            return redirect(url_for('calculate_footprint'))
            
    return render_template('calculate_footprint.html')
def calculate_alternatives(distance, transport, transport_emissions):
    # Dictionary of transport modes with their display names and conditions
    transport_options = {
        'train': {
            'display': 'Train',
            'max_distance': 1000,
            'condition': lambda d: True  # Always show train if within distance
        },
        'bus': {
            'display': 'Bus',
            'max_distance': 500,
            'condition': lambda d: True  # Always show bus if within distance
        },
        'electric_car': {
            'display': 'Electric Car',
            'max_distance': None,  # No distance limit
            'condition': lambda d: transport in ['car', 'hybrid_car', 'plane_economy', 'plane_business']
        },
        'hybrid_car': {
            'display': 'Hybrid Car',
            'max_distance': None,  # No distance limit
            'condition': lambda d: transport == 'car' or transport.startswith('plane_')
        },
        'bicycle': {
            'display': 'Bicycle',
            'max_distance': None,  # No distance limit
            'condition': lambda d: True  # Always show bicycle as an option
        }
    }
    
    alternatives = []
    current_emissions = transport_emissions
    
    for mode, details in transport_options.items():
        # Skip if it's the current mode or if emissions would be higher
        if mode == transport or emission_factors[mode] >= current_emissions:
            continue
            
        # Check distance and condition requirements
        if (details['max_distance'] is None or distance <= details['max_distance']) and \
           details['condition'](distance):
            mode_emissions = distance * emission_factors[mode]
            savings = transport_emissions - mode_emissions
            
            alternatives.append({
                'mode': details['display'],
                'emissions': round(mode_emissions, 2),
                'savings': round(savings, 2),
                'reduction_percent': round((savings / transport_emissions) * 100, 1)
            })
    
    # Sort alternatives by emissions savings (highest first)
    alternatives.sort(key=lambda x: x['savings'], reverse=True)
    
    return alternatives

@app.route('/travel-planner', methods=['GET', 'POST'])
def travel_planner():
    global model
    
    if request.method == 'POST':
        if not model:
            flash('AI service is currently unavailable. Please try again later.')
            return render_template('travel_planner_form.html', 
                                error="AI service unavailable",
                                show_error=True)
        
        data = request.form
        destinations = request.form.getlist('destinations')
        eco_preferences = request.form.getlist('eco_preferences')
        
        if not destinations:
            flash('Please select at least one destination')
            return render_template('travel_planner_form.html')
        
        print(f"Generating plan for destinations: {destinations}")
        destinations_str = ", ".join(destinations)
        eco_preferences_str = ", ".join(eco_preferences) if eco_preferences else "No specific preferences"
        
        prompt = f"""
        Create a detailed eco-friendly travel itinerary for Karnataka covering these destinations: {destinations_str}
        
        Travel Details:
        - Travel dates: {data['start_date']} to {data['end_date']}
        - Number of travelers: {data['travelers']}
        - Group type: {data['group_type']}
        - Preferred mode of transport: {data['transport_mode']}
        - Budget range: {data['budget']}
        - Rest stop frequency: {data.get('rest_stops', 'Normal')}
        - Sustainability level: {data.get('sustainability_level', 'Medium')}
        
        Eco Preferences:
        {eco_preferences_str}
        
        Please provide a comprehensive itinerary including:
        1. Day-by-day schedule with optimal eco-friendly route between destinations
        2. Estimated travel time and distance between places
        3. Specific public transportation options and schedules
        4. Eco-friendly accommodation recommendations
        5. Rest stops and breaks
        6. Sustainable activities and experiences
        
        Format the response in HTML with clear headings, bullet points, and sections.
        """
        
        try:
            print("Sending request to Gemini...")
            response = model.generate_content(prompt)
            if not response or not response.text:
                raise Exception("Empty response from Gemini")
            
            itinerary = response.text
            print("Successfully generated itinerary")
            
            return render_template('travel_planner_form.html', 
                                    itinerary=itinerary, 
                                    form_data=data)
                                    
        except Exception as e:
            print(f"Error generating content: {str(e)}")
            # Attempt to reinitialize the model
            model = initialize_gemini()
            flash('Failed to generate travel plan. Please try again. If the problem persists, check your API key.')
            return render_template('travel_planner_form.html')
            
    return render_template('travel_planner_form.html')

def process_eco_itinerary(itinerary):
    """
    Process the itinerary to add sustainability indicators and formatting
    """
    # Format day headers
    itinerary = re.sub(
        r'Day \d+: ([^\n]+)\(([^)]+)\)',
        r'<div class="day-header"><span class="day-title">Day \g<1></span><span class="day-date">\g<2></span></div>',
        itinerary
    )

    # Format travel sections
    itinerary = re.sub(
        r'\* \*\*Travel:\*\* ([^\n]+)',
        r'<div class="travel-section"><strong>Travel:</strong> \1</div>',
        itinerary
    )

    # Format accommodation sections
    itinerary = re.sub(
        r'\* \*\*Accommodation:\*\* ([^\n]+)',
        r'<div class="accommodation-section"><strong>Accommodation:</strong> \1</div>',
        itinerary
    )

    # Format time blocks
    itinerary = re.sub(
        r'\* \*\*(Morning|Afternoon|Evening):\*\* ([^\n]+)',
        r'<div class="time-block"><strong>\1:</strong> \2</div>',
        itinerary
    )

    # Format activities
    itinerary = re.sub(
        r'\* \*\*Activities:\*\* ([^\n]+)',
        r'<div class="activities-section"><strong>Activities:</strong> \1</div>',
        itinerary
    )

    # Format important notes
    itinerary = re.sub(
        r'Important Notes:',
        r'<div class="notes-header">Important Notes:</div>',
        itinerary
    )

    # Format bullet points in notes
    itinerary = re.sub(
        r'\* \*\*([^:]+):\*\* ([^\n]+)',
        r'<div class="note-item"><strong>\1:</strong> \2</div>',
        itinerary
    )

    return itinerary

def process_day_content(content):
    """Helper function to process the content within each day"""
    # Process time blocks
    content = re.sub(
        r'•\s*\*\*(Morning|Afternoon|Evening):\*\*\s*(.*?)(?=•|\Z)',
        lambda m: f'''
            <div class="time-block">{m.group(1)}</div>
            <div class="activity-item">{m.group(2).strip()}</div>
        ''',
        content,
        flags=re.DOTALL
    )
    
    # Process regular activities
    content = re.sub(
        r'•\s*([^*].*?)(?=•|\Z)',
        lambda m: f'<div class="activity-item">{m.group(1).strip()}</div>',
        content,
        flags=re.DOTALL
    )
    
    return content

# Remove the old calculator route if it exists
# @app.route('/calculator')
# def calculator():
#     return render_template('calculator.html')  # This renders your calculator page

def handle_missing_keys():
    """Check if required API keys are present"""
    missing_keys = []
    if not GOOGLE_MAPS_API_KEY:
        missing_keys.append("Google Maps API key")
    if not GOOGLE_GEMINI_API_KEY:
        missing_keys.append("Google Gemini API key")
    return missing_keys

@app.route('/get-aqi/<lat>/<lon>')
def get_aqi(lat, lon):
    if not AIRQUALITY_API_KEY:
        return jsonify({
            "error": "AQI API key not configured"
        }), 400

    try:
        # Using OpenWeatherMap Air Pollution API
        url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={AIRQUALITY_API_KEY}"
        
        response = requests.get(url, timeout=5)  # Add timeout
        response.raise_for_status()  # Raise exception for bad status codes
        
        data = response.json()
        
        if 'list' not in data or not data['list']:
            return jsonify({
                "error": "No AQI data available for this location"
            }), 404
            
        aqi = data['list'][0]['main']['aqi']
        components = data['list'][0]['components']
        
        # AQI categories
        aqi_categories = {
            1: {"level": "Good", "color": "#009966"},
            2: {"level": "Fair", "color": "#ffde33"},
            3: {"level": "Moderate", "color": "#ff9933"},
            4: {"level": "Poor", "color": "#cc0033"},
            5: {"level": "Very Poor", "color": "#660099"}
        }
        
        return jsonify({
            "aqi": aqi,
            "category": aqi_categories[aqi]["level"],
            "color": aqi_categories[aqi]["color"],
            "components": components
        })
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching AQI data: {str(e)}")
        return jsonify({
            "error": "Failed to fetch AQI data from external service"
        }), 503
    except (KeyError, ValueError, TypeError) as e:
        print(f"Error processing AQI data: {str(e)}")
        return jsonify({
            "error": "Invalid data received from AQI service"
        }), 500
    except Exception as e:
        print(f"Unexpected error in get_aqi: {str(e)}")
        return jsonify({
            "error": "Internal server error"
        }), 500

@app.route('/packing-assistant', methods=['GET', 'POST'])
def packing_assistant():
    global model
    
    if request.method == 'POST':
        try:
            if not model:
                model = initialize_gemini()
                if not model:
                    flash('AI service is currently unavailable. Please try again later.')
                    return render_template('packing_assistant.html',
                                        error="AI service unavailable",
                                        show_error=True)
            
            data = request.form
            destinations = data.get('destination', '')
            duration = int((datetime.strptime(data.get('end_date'), '%Y-%m-%d') - 
                          datetime.strptime(data.get('start_date'), '%Y-%m-%d')).days)
            activities = request.form.getlist('activities[]')  # Note the [] in the name
            eco_preferences = request.form.getlist('eco_preferences[]')
            special_needs = request.form.getlist('special_needs[]')  # Note the [] in the name
            
            prompt = f"""
            Generate a detailed packing list for:
            
            Trip Duration: {duration} days
            Destination: {destinations}
            Number of Travelers: {data.get('travelers', '1')}
            Activities: {', '.join(activities) if activities else 'General tourism'}
            Eco Preferences: {', '.join(eco_preferences) if eco_preferences else 'Standard'}
            Special Needs: {', '.join(special_needs) if special_needs else 'None'}
            Season: {data.get('season', 'Not specified')}
            
            Please provide:
            1. Essential Items List (categorized)
            2. Eco-friendly alternatives for common items
            3. Weight estimation for each category
            4. Special considerations for the destination
            5. Packing tips for reducing carbon footprint
            
            Format the response in HTML with these sections:
            - <h3>Essential Items</h3>
            - <h3>Eco-friendly Alternatives</h3>
            - <h3>Special Considerations</h3>
            - <h3>Packing Tips</h3>
            
            Use <ul> and <li> for lists.
            Add 🌿 emoji for eco-friendly items.
            """
            
            print("Sending request to Gemini...")
            response = model.generate_content(prompt)
            if not response or not response.text:
                raise Exception("Empty response from AI")
            
            packing_list = response.text
            
            # Calculate estimated weight based on duration and number of travelers
            base_weight = 5  # Base weight in kg
            weight_per_day = 0.5  # Additional weight per day
            estimated_weight = base_weight + (duration * weight_per_day)
            weight_range = f"{round(estimated_weight - 1)}-{round(estimated_weight + 1)}"
            
            # Determine carbon impact based on eco preferences
            if eco_preferences and len(eco_preferences) >= 3:
                carbon_impact = "Low Impact 🌱"
            elif eco_preferences and len(eco_preferences) >= 1:
                carbon_impact = "Medium Impact 🌿"
            else:
                carbon_impact = "Standard Impact"
            
            print("Successfully generated packing list")
            
            return render_template('packing_assistant.html',
                                packing_list=packing_list,
                                weight_estimate=weight_range,
                                carbon_impact=carbon_impact,
                                form_data=data)
                                
        except Exception as e:
            print(f"Error generating packing list: {str(e)}")
            flash('Failed to generate packing list. Please try again.')
            return render_template('packing_assistant.html')
    
    return render_template('packing_assistant.html')

import logging
from datetime import datetime
import random

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/api/network-speed', methods=['POST'])
def network_speed():
    try:
        logger.debug("Received network speed request")
        
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
        
        lat = data.get('lat')
        lng = data.get('lng')
        provider = data.get('provider', 'Default')
        
        if lat is None or lng is None:
            logger.error("Missing coordinates in request")
            return jsonify({'error': 'Missing coordinates'}), 400
            
        logger.debug(f"Processing request for coordinates: {lat}, {lng}")
        
        try:
            # Try to use the SpeedtestService first
            speedtest_service = SpeedtestService()
            result = speedtest_service.run_speedtest(lat, lng, provider)
            return jsonify(result)
            
        except Exception as speedtest_error:
            logger.warning(f"Speedtest failed, falling back to mock data: {str(speedtest_error)}")
            
            # Fallback to mock data
            result = {
                'download_speed': round(random.uniform(10, 100), 2),
                'upload_speed': round(random.uniform(5, 50), 2),
                'ping': round(random.uniform(20, 150)),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'server_info': {
                    'name': 'Fallback Test Server',
                    'location': 'Mumbai, India'
                },
                'location_type': 'domestic' if (6.0 <= float(lat) <= 35.0 and 68.0 <= float(lng) <= 97.0) else 'international'
            }
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error in network_speed endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/network-servers', methods=['GET'])
def get_servers():
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        
        servers = speedtest_service.get_available_servers(lat, lng)
        return jsonify({
            'status': 'success',
            'servers': servers
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def generate_network_data():
    """Generate sample network data"""
    return {
        'download_speed': round(random.uniform(5, 50), 2),
        'upload_speed': round(random.uniform(2, 20), 2),
        'latency': round(random.uniform(20, 100), 2),
        'jitter': round(random.uniform(1, 10), 2),
        'network_type': random.choice(['4G', '5G']),
        'reliability': round(random.uniform(0.8, 1.0), 2)
    }

@app.route('/api/health')
def health_check():
    global model
    
    status = {
        'gemini_api': bool(model),
        'google_maps_api': bool(GOOGLE_MAPS_API_KEY),
        'air_quality_api': bool(AIRQUALITY_API_KEY)
    }
    
    return jsonify({
        'status': 'healthy' if all(status.values()) else 'degraded',
        'services': status,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/send-whatsapp', methods=['POST'])
def send_whatsapp():
    try:
        phone_number = request.form.get('phone_number')
        itinerary = request.form.get('itinerary')
        
        # Validate phone number
        if not phone_number or len(phone_number.strip()) != 10:
            flash('Please enter a valid 10-digit phone number')
            return redirect(url_for('travel_planner'))
        
        print(f"Processing WhatsApp request for number: {phone_number}")
        
        trip_data = {
            'start_date': request.form.get('start_date', ''),
            'end_date': request.form.get('end_date', ''),
            'travelers': request.form.get('travelers', '1'),
            'budget': request.form.get('budget', '0'),
            'itinerary': itinerary
        }
        
        result = whatsapp_service.send_trip_plan(phone_number, trip_data)
        
        if result['success']:
            message = f"Travel plan sent successfully! "
            if result.get('message_count', 1) > 1:
                message += f"Sent in {result['message_count']} parts."
            if 'message_statuses' in result:
                message += f"\nMessage status: {', '.join(result['message_statuses'])}"
            flash(message)
            print(f"WhatsApp send success: {result}")
        else:
            error = result.get('error', 'Unknown error')
            flash(f'Failed to send message: {error}')
            print(f"WhatsApp send error: {error}")
            
            # If sandbox joining is required, show special instructions
            if result.get('error_code') in ['SANDBOX_NOT_JOINED', '21606', '21608']:
                flash('Please join our WhatsApp sandbox first! Send "join <sandbox-code>" to our WhatsApp number.')
            
        return redirect(url_for('travel_planner'))
        
    except Exception as e:
        print(f"Error in send_whatsapp route: {str(e)}")
        flash(f'Error sending WhatsApp message: {str(e)}')
        return redirect(url_for('travel_planner'))

@app.route('/send-packing-list', methods=['POST'])
def send_packing_list():
    try:
        email = request.form.get('email')
        packing_list = request.form.get('packing_list')
        
        if not email or '@' not in email:
            return jsonify({
                'success': False,
                'error': 'Please enter a valid email address'
            })
        
        packing_data = {
            'id': str(int(time.time())),
            'duration': request.form.get('duration', ''),
            'destination': request.form.get('destination', ''),
            'travelers': request.form.get('travelers', '1'),
            'season': request.form.get('season', ''),
            'packing_list': packing_list,
            'weight_estimate': request.form.get('weight_estimate', ''),
            'carbon_impact': request.form.get('carbon_impact', '')
        }
        
        email_service = EmailService()
        result = email_service.send_packing_list(email, packing_data)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Packing list sent successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to send email')
            })
            
    except Exception as e:
        print(f"Error sending packing list: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while sending the email'
        })

@app.route('/send-travel-plan', methods=['POST'])
def send_travel_plan():
    try:
        email = request.form.get('email')
        itinerary = request.form.get('itinerary')
        destinations = request.form.getlist('destinations[]')  # Get list of destinations
        
        if not email or '@' not in email:
            flash('Please enter a valid email address')
            return redirect(url_for('travel_planner'))
        
        trip_data = {
            'id': str(int(time.time())),
            'start_date': request.form.get('start_date', ''),
            'end_date': request.form.get('end_date', ''),
            'travelers': request.form.get('travelers', '1'),
            'budget': request.form.get('budget', '0'),
            'itinerary': itinerary,
            'destinations': destinations  # Add destinations for route generation
        }
        
        result = email_service.send_travel_plan(email, trip_data)
        
        if result['success']:
            flash('Travel plan has been sent to your email!')
        else:
            flash(f'Failed to send email: {result.get("error", "Unknown error")}')
            
        return redirect(url_for('travel_planner'))
        
    except Exception as e:
        print(f"Error in send_travel_plan route: {str(e)}")
        flash(f'Error sending travel plan: {str(e)}')
        return redirect(url_for('travel_planner'))

@app.route('/send-route-details', methods=['POST'])
def send_route_details():
    try:
        email = request.form.get('email')
        route_details = request.form.get('route_details')
        origin = request.form.get('origin')
        destination = request.form.get('destination')
        mode = request.form.get('mode')
        route_summary = request.form.get('route_summary')  # Add this line
        
        if not email or '@' not in email:
            return jsonify({
                'success': False,
                'error': 'Please enter a valid email address'
            })
        
        # Generate Google Maps link
        maps_link = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode={mode.lower()}"
        
        route_data = {
            'id': str(int(time.time())),
            'origin': origin,
            'destination': destination,
            'mode': mode,
            'details': json.loads(route_details),
            'summary': route_summary,  # Add this line
            'maps_link': maps_link    # Add this line
        }
        
        result = email_service.send_route_details(email, route_data)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in send_route_details route: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/send-footprint', methods=['POST'])
def send_footprint():
    try:
        print("Starting send_footprint route handler")
        
        email = request.form.get('email')
        footprint_data_str = request.form.get('footprint_data')
        
        print(f"Received email: {email}")
        print(f"Received footprint data: {footprint_data_str}")

        if not email:
            print("Error: Email address is missing")
            return jsonify({
                'success': False, 
                'error': 'Please provide an email address'
            })

        if not footprint_data_str:
            print("Error: Footprint data is missing")
            return jsonify({
                'success': False, 
                'error': 'No footprint data provided'
            })

        try:
            footprint_data = json.loads(footprint_data_str)
            print("Successfully parsed footprint data:", footprint_data)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            return jsonify({
                'success': False, 
                'error': 'Invalid data format'
            })

        # Add required fields if missing
        footprint_data.update({
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        print("Sending email via email service...")
        result = email_service.send_footprint_details(email, footprint_data)
        print(f"Email service result: {result}")
        
        if result['success']:
            return jsonify({
                'success': True, 
                'message': 'Carbon footprint details have been sent to your email!'
            })
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"Email service error: {error_msg}")
            return jsonify({
                'success': False, 
                'error': f"Failed to send email: {error_msg}"
            })
            
    except Exception as e:
        print(f"Unexpected error in send_footprint route: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False, 
            'error': f"An error occurred: {str(e)}"
        })

def find_closest_image(target_filename, image_dir):
    """Find the closest matching image filename in the directory"""
    if os.path.exists(os.path.join(image_dir, target_filename)):
        return target_filename
        
    existing_files = [f for f in os.listdir(image_dir) if f.endswith('.jpg')]
    matches = get_close_matches(target_filename, existing_files, n=1, cutoff=0.6)
    return matches[0] if matches else None

@app.route('/api/places')
def get_places():
    try:
        json_path = os.path.join(app.static_folder, 'final_karnataka_hidden_gems.json')
        cached_images_dir = os.path.join(app.static_folder, 'cached_images')
        placeholder_image = url_for('static', filename='images/placeholder.jpg')
        
        if not os.path.exists(json_path):
            return jsonify({'error': 'Places data file not found'}), 404

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Process each place to add image URLs
        for city in data['cities']:
            for place in city['places']:
                # Create base filename
                city_part = city['city'].lower()
                place_part = place['name'].lower()
                
                # Create target filename
                target_filename = f"{city_part}_{place_part.replace(' ', '_')}.jpg"
                image_path = os.path.join(cached_images_dir, target_filename)
                
                # Check if image exists and is valid
                if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                    place['imageUrl'] = url_for('static', filename=f'cached_images/{target_filename}')
                else:
                    place['imageUrl'] = placeholder_image

        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error in get_places: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/ecostay')
def ecostay():
    # Load Google Maps API key from environment variable
    google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    return render_template('ecostay.html', google_maps_api_key=google_maps_api_key)

@app.route('/eco-stays')
def get_eco_stays():
    city = request.args.get('city', '').lower()
    
    try:
        # Load eco stays data
        json_path = os.path.join(app.static_folder, 'data', 'eco_stays.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if city not in data:
            return jsonify({'error': 'City not found'}), 404
            
        stays = data[city]
        cached_images_dir = os.path.join(app.static_folder, 'cached_images')
        placeholder_image = url_for('static', filename='images/placeholder.jpg')
        
        # Process each stay to ensure valid images
        for stay in stays:
            clean_name = "".join(c for c in stay['name'] if c.isalnum() or c in (' ', '-'))
            clean_location = "".join(c for c in stay['location'] if c.isalnum() or c in (' ', '-'))
            filename = f"{clean_name}_{clean_location}.jpg".lower().replace(' ', '_')
            image_path = os.path.join(cached_images_dir, filename)
            
            # Check if image exists and is valid
            if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                stay['image_url'] = url_for('static', filename=f'cached_images/{filename}')
            else:
                stay['image_url'] = placeholder_image
        
        return jsonify({'eco_stays': stays})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/eco-stays/cities')
def get_available_cities():
    try:
        # Load eco stays data
        with open(os.path.join(app.static_folder, 'data', 'eco_stays.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get list of cities from the JSON data
        cities = list(data.keys())
        
        return jsonify({
            'cities': cities
        })
        
    except Exception as e:
        app.logger.error(f"Error in get_available_cities: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
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
    "vidhana_soudha": "Bangalore"
}

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
    "vidhana_soudha": 12
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
    
    return render_template('gallery/register.html')

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
    return render_template('gallery/login.html')

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    gallery = mongo.db.gallery.find({'user_id': current_user.get_id()})
    return render_template('gallery/dashboard.html', 
                         user=current_user.to_dict(), 
                         gallery=list(gallery))
from flask_cors import CORS
import traceback

# Add CORS support
CORS(app)

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No image uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400

        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400

        # Read and preprocess the image
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        
        # Convert image to RGB if it's not
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Preprocess the image for the model
        img = img.resize((224, 224))  # Same size as training
        img_array = img_to_array(img)
        img_array = img_array / 255.0  # Same normalization as training
        img_array = np.expand_dims(img_array, axis=0)
        
        # Make prediction
        predictions = tf_model.predict(img_array)
        prediction_index = np.argmax(predictions[0])
        confidence = float(predictions[0][prediction_index])
        
        # Set confidence threshold
        if confidence < 0.5:  # You can adjust this threshold
            return jsonify({
                'success': False,
                'error': 'Cannot confidently classify this image. Please try a clearer image of a Karnataka landmark.'
            }), 400
            
        # Get prediction label
        prediction = None
        for landmark, idx in CLASS_INDICES.items():
            if idx == prediction_index:
                prediction = landmark
                break
        
        if not prediction:
            return jsonify({
                'success': False,
                'error': 'Could not classify the image'
            }), 400
        
        location = KNOWN_LOCATIONS.get(prediction, 'Unknown Location')
        
        # Save the original image data
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG', quality=85)
        img_data = f"data:image/jpeg;base64,{base64.b64encode(img_io.getvalue()).decode()}"
        
        # Store in MongoDB
        mongo.db.gallery.insert_one({
            'user_id': current_user.get_id(),
            'image': img_data,
            'prediction': prediction,
            'confidence': f"{confidence * 100:.2f}%",
            'location': location,
            'timestamp': datetime.now()
        })
        
        return jsonify({
            'success': True,
            'prediction': prediction.replace('_', ' ').title(),
            'confidence': f"{confidence * 100:.2f}%",
            'location': location
        }), 200
        
    except Exception as e:
        app.logger.error(f"Prediction error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing the image'
        }), 500

# Add this at the top of your file with other helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/gallery/clear', methods=['POST'])
@login_required
def clear_gallery():
    try:
        print("Clear gallery endpoint hit")  # Debug print
        result = mongo.db.gallery.delete_many({'user_id': current_user.get_id()})
        print(f"Deleted {result.deleted_count} documents")  # Debug print
        return jsonify({'success': True, 'message': f'Deleted {result.deleted_count} images'})
    except Exception as e:
        print(f"Error in clear_gallery: {str(e)}")  # Debug print
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test-mongo')
@login_required
def test_mongo():
    try:
        user_id = current_user.get_id()
        gallery_count = mongo.db.gallery.count_documents({'user_id': user_id})
        return jsonify({
            'success': True,
            'user_id': user_id,
            'gallery_count': gallery_count,
            'mongo_connected': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'mongo_connected': False
        })

if __name__ == '__main__':
    # Initialize Flask app configurations
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    try:
        # Load the TensorFlow model
        model_path = os.path.join('static', 'karnataka_places_model.h5')
        if os.path.exists(model_path):
            tf_model = tf.keras.models.load_model(model_path)
            print("TensorFlow model loaded successfully")
        else:
            print(f"Warning: Model file not found at {model_path}")
            tf_model = None
    except Exception as e:
        print(f"Error loading TensorFlow model: {str(e)}")
        tf_model = None

    # Test email configuration without blocking startup
    email_status = test_email_config()
    if not email_status:
        print("Warning: Email service may not work properly")
    
    # Initialize services
    missing_keys = handle_missing_keys()
    if missing_keys:
        print("Warning: Missing API keys:", ", ".join(missing_keys))
        print("Please check your .env file and add the missing keys.")
    
    if not model:
        print("Warning: Failed to initialize Gemini API after multiple attempts")
        print("The application will start, but AI features will be unavailable")
    
    # Start the Flask application
    try:
        app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down..")
    except Exception as e:
        print(f"Error starting the application: {str(e)}")














