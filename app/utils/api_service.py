# app/utils/api_service.py
import requests
import time
import json
import re
from threading import Thread, Event
from flask import current_app
from app import db
from app.models import APIConfig, Participant, Draw, APIResponseLog
from datetime import datetime

class APIService:
    def __init__(self):
        self.is_running = False
        self.polling_thread = None
        self.polling_event = Event()
        self._app = None
    
    @property
    def app(self):
        if self._app is None:
            from app import create_app
            self._app = create_app()
        return self._app
    
    def start_polling(self):
        """Start polling the external API"""
        if self.is_running:
            current_app.logger.warning("API service is already running")
            return False
        
        try:
            self.is_running = True
            self.polling_event.clear()
            self.polling_thread = Thread(target=self._polling_worker)
            self.polling_thread.daemon = True
            self.polling_thread.start()
            current_app.logger.info("API polling service started")
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to start API polling: {e}")
            self.is_running = False
            return False
    
    def stop_polling(self):
        """Stop polling the external API"""
        try:
            self.is_running = False
            self.polling_event.set()
            if self.polling_thread and self.polling_thread.is_alive():
                self.polling_thread.join(timeout=10)
            current_app.logger.info("API polling service stopped")
            return True
        except Exception as e:
            current_app.logger.error(f"Error stopping API polling: {e}")
            return False
    
    def _polling_worker(self):
        """Background worker that polls the API with proper session management"""
        while self.is_running and not self.polling_event.is_set():
            try:
                with self.app.app_context():
                    self._fetch_from_api()
               
                refresh_interval = 300  # default 5 minutes
                with self.app.app_context():
                    api_config = APIConfig.query.first()
                    if api_config and api_config.refresh_interval:
                        refresh_interval = api_config.refresh_interval * 60
                
                self.polling_event.wait(refresh_interval)
                    
            except Exception as e:
                current_app.logger.error(f"API polling worker error: {e}")
                self.polling_event.wait(300)
    
    def _fetch_from_api(self):
        """Fetch data from the external API with proper error handling"""
        try:
            api_config = APIConfig.query.first()
            if not api_config or not api_config.is_active or not api_config.endpoint_url:
                current_app.logger.debug("API service not configured or inactive")
                return
            
            # Validate endpoint URL
            if not self._validate_endpoint_url(api_config.endpoint_url):
                current_app.logger.error(f"Invalid endpoint URL: {api_config.endpoint_url}")
                return
            
            response_log = APIResponseLog(
                api_config_id=api_config.id,
                request_url=api_config.endpoint_url,
                request_method='GET',
                timestamp=datetime.utcnow()
            )
          
            response = self._make_api_request(api_config, response_log)
            
            if response and response.status_code == 200:
                self._process_successful_response(response, api_config, response_log)
            else:
                self._log_failed_response(response, response_log)
                
        except Exception as e:
            current_app.logger.error(f"Unexpected error in API fetch: {e}")
            db.session.rollback()
    
    def _validate_endpoint_url(self, url):
        """Validate the endpoint URL"""
        try:
            import re
            regex = re.compile(
                r'^(?:http|ftp)s?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            return re.match(regex, url) is not None
        except Exception:
            return False
    
    def _make_api_request(self, api_config, response_log):
        """Make the actual API request with proper headers and timeout"""
        try:
            headers = {
                'User-Agent': 'RaffleSystem/1.0',
                'Accept': 'application/json'
            }
            
            # Setup authentication
            if api_config.auth_method == 'api_key' and api_config.api_key:
                headers['Authorization'] = f'Bearer {api_config.api_key}'
            elif api_config.auth_method == 'basic_auth' and api_config.api_key:
                headers['Authorization'] = f'Basic {api_config.api_key}'
            elif api_config.auth_method == 'none':
                # No authentication needed
                pass
            
            current_app.logger.info(f"Making API request to: {api_config.endpoint_url}")
            
            # Make API request with timeout
            response = requests.get(
                api_config.endpoint_url,
                headers=headers,
                timeout=(10, 30)  # (connect_timeout, read_timeout)
            )
            
            return response
            
        except requests.exceptions.Timeout:
            error_msg = "API request timed out"
            current_app.logger.error(error_msg)
            response_log.error_message = error_msg
            response_log.success = False
            self._safe_commit_response_log(response_log)
            return None
            
        except requests.exceptions.ConnectionError:
            error_msg = "API connection failed - network error"
            current_app.logger.error(error_msg)
            response_log.error_message = error_msg
            response_log.success = False
            self._safe_commit_response_log(response_log)
            return None
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            current_app.logger.error(error_msg)
            response_log.error_message = error_msg
            response_log.success = False
            self._safe_commit_response_log(response_log)
            return None
    
    def _process_successful_response(self, response, api_config, response_log):
        """Process a successful API response"""
        try:
            data = response.json()
            response_log.response_status = response.status_code
            response_log.response_headers = json.dumps(dict(response.headers))
            response_log.response_body = json.dumps(data, ensure_ascii=False)
            
            current_app.logger.info(f"API response received with status {response.status_code}")
            
            # Process the response data
            added_count = self._process_api_response(data)
            response_log.participants_added = added_count
            response_log.success = True
            
            # Update last sync time
            api_config.last_sync = datetime.utcnow()
            
            # Commit the changes
            self._safe_commit_response_log(response_log)
            
            current_app.logger.info(f"Successfully processed API response, added {added_count} participants")
            
        except ValueError as e:
            # JSON parsing error
            error_msg = f"Failed to parse JSON response: {str(e)}"
            current_app.logger.error(error_msg)
            response_log.error_message = error_msg
            response_log.response_body = response.text[:1000]  # Store first 1000 chars
            response_log.success = False
            self._safe_commit_response_log(response_log)
            
        except Exception as e:
            error_msg = f"Error processing API response: {str(e)}"
            current_app.logger.error(error_msg)
            response_log.error_message = error_msg
            response_log.success = False
            self._safe_commit_response_log(response_log)
    
    def _log_failed_response(self, response, response_log):
        """Log a failed API response"""
        try:
            if response:
                response_log.response_status = response.status_code
                response_log.response_headers = json.dumps(dict(response.headers))
                
                try:
                    error_data = response.json()
                    response_log.response_body = json.dumps(error_data, ensure_ascii=False)
                    response_log.error_message = f"HTTP {response.status_code}: {error_data}"
                except ValueError:
                    response_log.response_body = response.text[:1000]
                    response_log.error_message = f"HTTP {response.status_code}"
            else:
                response_log.error_message = "No response received"
            
            response_log.success = False
            self._safe_commit_response_log(response_log)
            
            current_app.logger.warning(f"API request failed: {response_log.error_message}")
            
        except Exception as e:
            current_app.logger.error(f"Error logging failed response: {e}")
    
    def _safe_commit_response_log(self, response_log):
        """Safely commit response log with error handling"""
        try:
            db.session.add(response_log)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to commit response log: {e}")
    
    def _process_api_response(self, data):
        """Process the API response with improved error handling and batching"""
        try:
            api_config = APIConfig.query.first()
            if not api_config:
                current_app.logger.warning("No API configuration found")
                return 0
            
            default_draw_id = api_config.default_draw_id
            
            # Extract participants data
            participants_data = self._extract_participants_data(data)
            
            if not participants_data:
                current_app.logger.info("No participant data found in API response")
                return 0
            
            current_app.logger.info(f"Processing {len(participants_data)} participant entries from API")
            
            # Use batch processing for better performance
            added_count = self._batch_process_participants(participants_data, default_draw_id)
            
            return added_count
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing API data: {e}")
            return 0
    
    def _batch_process_participants(self, participants_data, default_draw_id):
        """Process participants in batches for better performance"""
        added_count = 0
        batch_size = 50  # Process in batches to avoid memory issues
        valid_participants = []
        
        for i, participant_data in enumerate(participants_data):
            try:
                phone_number = self._extract_and_validate_phone(participant_data)
                draw_id = self._extract_draw_id(participant_data, default_draw_id)
                
                if not phone_number or not draw_id:
                    continue
                
                # Validate draw exists
                if not Draw.query.get(draw_id):
                    current_app.logger.warning(f"Draw {draw_id} not found, skipping participant")
                    continue
                
                valid_participants.append({
                    'phone_number': phone_number,
                    'draw_id': draw_id,
                    'source': 'api',
                    'is_verified': True,
                    'added_at': datetime.utcnow()
                })
                
            except Exception as e:
                current_app.logger.warning(f"Error processing participant data at index {i}: {e}")
                continue
        
        # Process in batches
        for i in range(0, len(valid_participants), batch_size):
            batch = valid_participants[i:i + batch_size]
            added_count += self._process_participant_batch(batch)
        
        return added_count
    
    def _process_participant_batch(self, participant_batch):
        """Process a batch of participants with duplicate checking"""
        if not participant_batch:
            return 0
        
        try:
            # Extract phone numbers and draw IDs for duplicate checking
            phone_numbers = [p['phone_number'] for p in participant_batch]
            draw_ids = [p['draw_id'] for p in participant_batch]
            
            # Check for existing participants in batch
            existing_participants = Participant.query.filter(
                Participant.phone_number.in_(phone_numbers),
                Participant.draw_id.in_(draw_ids)
            ).with_entities(Participant.phone_number, Participant.draw_id).all()
            
            # Create set of existing participant keys
            existing_keys = {f"{p.phone_number}-{p.draw_id}" for p in existing_participants}
            
            # Filter out duplicates
            new_participants = []
            for participant_data in participant_batch:
                participant_key = f"{participant_data['phone_number']}-{participant_data['draw_id']}"
                if participant_key not in existing_keys:
                    new_participants.append(Participant(**participant_data))
            
            # Bulk insert new participants
            if new_participants:
                db.session.bulk_save_objects(new_participants)
                db.session.commit()
                current_app.logger.info(f"Added {len(new_participants)} new participants from API batch")
                return len(new_participants)
            else:
                current_app.logger.debug("No new participants to add from this batch")
                return 0
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing participant batch: {e}")
            return 0
    
    def _extract_and_validate_phone(self, participant_data):
        """Extract and validate phone number from participant data"""
        phone_fields = ['phone_number', 'phone', 'msisdn', 'number', 'contact']
        
        for field in phone_fields:
            if field in participant_data and participant_data[field]:
                raw_phone = str(participant_data[field]).strip()
                if not raw_phone:
                    continue
                
                # Clean and validate phone number
                cleaned_phone = re.sub(r'\D', '', raw_phone)  # Remove non-digits
                
                # Basic validation
                if len(cleaned_phone) >= 9 and len(cleaned_phone) <= 15:
                    return cleaned_phone
                else:
                    current_app.logger.debug(f"Invalid phone number length: {cleaned_phone}")
                    return None
        
        return None
    
    def _extract_participants_data(self, data):
        """Extract participants data from various API response formats"""
        if not data:
            return []
        
        current_app.logger.debug(f"Extracting participants from API response format: {type(data)}")
        
        # Format 1: Simple array of phone numbers
        if isinstance(data, list) and all(isinstance(item, str) for item in data):
            return [{"phone_number": phone} for phone in data]
        
        # Format 2: Array of objects
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            participants = []
            for item in data:
                participant = {}
                
                # Extract phone number
                phone_fields = ['phone_number', 'phone', 'msisdn', 'number', 'contact']
                for field in phone_fields:
                    if field in item and item[field]:
                        participant['phone_number'] = str(item[field])
                        break
                
                # Extract draw ID if present
                draw_fields = ['draw_id', 'draw', 'raffle_id', 'campaign_id']
                for field in draw_fields:
                    if field in item and item[field]:
                        try:
                            participant['draw_id'] = int(item[field])
                        except (ValueError, TypeError):
                            pass
                        break
                
                if 'phone_number' in participant:
                    participants.append(participant)
            
            return participants
        
        # Format 3: Object with nested data
        elif isinstance(data, dict):
            # Check for common nested structures
            nested_fields = ['data', 'results', 'participants', 'items', 'entries']
            for field in nested_fields:
                if field in data and isinstance(data[field], list):
                    return self._extract_participants_data(data[field])
            
            # Check for simple phone_numbers array
            if 'phone_numbers' in data and isinstance(data['phone_numbers'], list):
                return self._extract_participants_data(data['phone_numbers'])
        
        current_app.logger.warning(f"Unrecognized API response format: {type(data)}")
        return []
    
    def _extract_draw_id(self, participant_data, default_draw_id):
        """Extract draw ID from participant data"""
        draw_fields = ['draw_id', 'draw', 'raffle_id', 'campaign_id']
        
        for field in draw_fields:
            if field in participant_data and participant_data[field]:
                try:
                    draw_id = int(participant_data[field])
                    # Validate draw exists
                    if Draw.query.get(draw_id):
                        return draw_id
                    else:
                        current_app.logger.warning(f"Draw ID {draw_id} not found in database")
                except (ValueError, TypeError) as e:
                    current_app.logger.debug(f"Invalid draw ID format: {participant_data[field]} - {e}")
                    continue
        
        return default_draw_id

# Global API service instance
api_service = APIService()