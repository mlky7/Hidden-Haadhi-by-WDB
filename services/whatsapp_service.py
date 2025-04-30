from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from app_config.twilio_config import TWILIO_CONFIG
import time

class WhatsAppService:
    def __init__(self):
        try:
            self.client = Client(
                TWILIO_CONFIG['account_sid'],
                TWILIO_CONFIG['auth_token']
            )
            self.whatsapp_number = self._format_whatsapp_number(TWILIO_CONFIG['whatsapp_number'])
            self.MAX_LENGTH = 500  # Reduced to 500 characters
            print(f"WhatsApp Service initialized with number: {self.whatsapp_number}")
        except Exception as e:
            print(f"Error initializing WhatsApp Service: {str(e)}")
            raise

    def _format_whatsapp_number(self, number):
        """Format number to Twilio WhatsApp format"""
        number = ''.join(filter(str.isdigit, number))
        if len(number) == 10:  # Indian number without country code
            number = f'91{number}'
        if not number.startswith('+'):
            number = f'+{number}'
        return number

    def split_message(self, message):
        """Split long messages into smaller parts with strict 500 character limit"""
        if len(message) <= self.MAX_LENGTH:
            return [message]
        
        parts = []
        current_part = ""
        lines = message.split('\n')
        
        for line in lines:
            # If this line alone exceeds limit, split it into smaller chunks
            if len(line) > self.MAX_LENGTH:
                words = line.split()
                line_part = ""
                for word in words:
                    if len(line_part) + len(word) + 1 <= self.MAX_LENGTH:
                        line_part += (word + " ")
                    else:
                        if current_part:
                            if len(current_part + "\n" + line_part.strip()) <= self.MAX_LENGTH:
                                current_part += "\n" + line_part.strip()
                            else:
                                parts.append(current_part)
                                current_part = line_part.strip()
                        else:
                            parts.append(line_part.strip())
                        line_part = word + " "
                if line_part:
                    if current_part and len(current_part + "\n" + line_part.strip()) <= self.MAX_LENGTH:
                        current_part += "\n" + line_part.strip()
                    else:
                        if current_part:
                            parts.append(current_part)
                        current_part = line_part.strip()
            else:
                # Try to add the line to current part
                if current_part:
                    if len(current_part + "\n" + line) <= self.MAX_LENGTH:
                        current_part += "\n" + line
                    else:
                        parts.append(current_part)
                        current_part = line
                else:
                    current_part = line
        
        # Add the last part if there's anything left
        if current_part:
            parts.append(current_part)
        
        # Format parts with numbers
        formatted_parts = []
        total_parts = len(parts)
        
        for i, part in enumerate(parts, 1):
            header = f"*Travel Plan (Part {i}/{total_parts})*\n\n"
            if i == 1:
                # First part includes basic trip info
                formatted_parts.append(part)
            else:
                part_with_header = f"{header}{part}"
                # If adding header would exceed limit, adjust content
                if len(part_with_header) > self.MAX_LENGTH:
                    part = part[:self.MAX_LENGTH - len(header)]
                    formatted_parts.append(f"{header}{part}")
                else:
                    formatted_parts.append(part_with_header)
        
        # Final verification that no part exceeds limit
        for i, part in enumerate(formatted_parts):
            if len(part) > self.MAX_LENGTH:
                formatted_parts[i] = part[:self.MAX_LENGTH-3] + "..."
        
        return formatted_parts

    def format_itinerary(self, trip_data):
        """Format the trip data into a more concise message"""
        # Create a shorter header to leave more room for content
        message = f"""🌟 *Travel Plan*
📅 {trip_data['start_date']} to {trip_data['end_date']}
👥 {trip_data['travelers']} travelers
💰 Budget: {trip_data['budget']}

{trip_data['itinerary']}

------------------------
Hidden ಹಾದಿ 🌿"""
        return message

    def send_trip_plan(self, phone_number, trip_data):
        try:
            formatted_phone = self._format_whatsapp_number(phone_number)
            whatsapp_from = f'whatsapp:{self.whatsapp_number}'
            whatsapp_to = f'whatsapp:{formatted_phone}'
            
            # Debug logging
            print(f"Sending from: {whatsapp_from}")
            print(f"Sending to: {whatsapp_to}")
            
            # Verify sandbox status first
            try:
                # Send a test message first
                test_message = self.client.messages.create(
                    from_=whatsapp_from,
                    body="🌟 Preparing to send your travel plan...",
                    to=whatsapp_to
                )
                print(f"Test message status: {test_message.status}")
                time.sleep(2)  # Wait for test message
            
            except TwilioRestException as e:
                if e.code == 21608:  # Sandbox participant not found
                    return {
                        'success': False,
                        'error': "Please join our WhatsApp sandbox first. Send 'join <sandbox-code>' to our WhatsApp number.",
                        'error_code': 'SANDBOX_NOT_JOINED'
                    }
                raise  # Re-raise other Twilio exceptions
            
            # Format and split the message
            formatted_message = self.format_itinerary(trip_data)
            message_parts = self.split_message(formatted_message)
            
            responses = []
            print(f"Sending {len(message_parts)} message parts to {formatted_phone}")
            
            for i, part in enumerate(message_parts, 1):
                print(f"Sending part {i}/{len(message_parts)} (length: {len(part)})")
                if len(part) > self.MAX_LENGTH:
                    print(f"Warning: Part {i} exceeds {self.MAX_LENGTH} characters, truncating...")
                    part = part[:self.MAX_LENGTH-3] + "..."
                
                message = self.client.messages.create(
                    from_=whatsapp_from,
                    body=part,
                    to=whatsapp_to
                )
                print(f"Message {i} status: {message.status}")
                responses.append(message)
                time.sleep(3)  # Increased delay between messages
            
            # Verify final status of all messages
            all_statuses = []
            for msg in responses:
                updated_msg = self.client.messages(msg.sid).fetch()
                all_statuses.append(updated_msg.status)
                print(f"Message {msg.sid} final status: {updated_msg.status}")
            
            return {
                'success': True,
                'message_count': len(responses),
                'message_sids': [msg.sid for msg in responses],
                'message_statuses': all_statuses,
                'total_length': sum(len(part) for part in message_parts)
            }
            
        except TwilioRestException as e:
            print(f"Twilio error: {str(e)}")
            error_message = self._handle_twilio_error(e)
            return {
                'success': False,
                'error': error_message,
                'error_code': e.code
            }
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'error_code': 'UNKNOWN'
            }

    def _handle_twilio_error(self, e):
        """Enhanced error handling with more specific messages"""
        error_messages = {
            63007: ("Please follow these steps:\n"
                   "1. Go to Twilio Console > Messaging > Try it out > WhatsApp\n"
                   "2. Click 'Send a WhatsApp Message'\n"
                   "3. Follow the instructions to join your sandbox\n"
                   "4. Send the verification code to activate your number"),
            21211: "Invalid phone number format. Please enter a valid number.",
            21606: "You must join our WhatsApp sandbox first. Send 'join <sandbox-code>' to our WhatsApp number.",
            21608: "Your number is not registered in our sandbox. Please join first.",
            21614: "Invalid message content",
            21617: "Message is too long. It will be split into multiple parts.",
            20003: "Authentication error. Please check Twilio credentials.",
            20404: "Resource not found. Please verify WhatsApp number configuration."
        }
        
        error_code = getattr(e, 'code', None)
        return error_messages.get(error_code, str(e))






