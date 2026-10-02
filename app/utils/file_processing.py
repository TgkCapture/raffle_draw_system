# app/utils/file_processing.py
import pandas as pd
import csv
import os
import re
from flask import current_app
from app.models import Participant, Draw, db
from datetime import datetime

def process_csv_file(file_path, draw_id):
    """Process CSV file and add participants to draw with batch operations"""
    processing_details = {
        'total_rows': 0,
        'valid_participants': 0,
        'duplicates_skipped': 0,
        'invalid_entries': 0,
        'errors': [],
        'processing_time': 0
    }
    
    start_time = datetime.now()
    
    try:
        # Read all data first
        with open(file_path, 'r', encoding='utf-8') as file:
            # Try to detect delimiter
            sample = file.read(1024)
            file.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            df = pd.read_csv(file, delimiter=delimiter)
        
        processing_details['total_rows'] = len(df)
        
        if processing_details['total_rows'] == 0:
            return False, "CSV file is empty", processing_details
        
        # Assume first column contains phone numbers
        phone_column = df.columns[0]
        current_app.logger.info(f"Processing CSV with {len(df)} rows, using column: {phone_column}")
        
        # Extract and validate phone numbers in batch
        valid_participants_data = []
        invalid_count = 0
        
        for index, row in df.iterrows():
            try:
                raw_phone = str(row[phone_column]).strip()
                
                # Skip empty rows
                if pd.isna(raw_phone) or raw_phone == '':
                    invalid_count += 1
                    continue
                
                # Enhanced phone number validation
                validation_result = validate_phone_number(raw_phone)
                if not validation_result['is_valid']:
                    invalid_count += 1
                    processing_details['errors'].append(f"Row {index + 2}: {validation_result['error']}")
                    continue
                
                valid_participants_data.append({
                    'phone_number': validation_result['cleaned_number'],
                    'raw_phone': raw_phone
                })
                
            except Exception as e:
                invalid_count += 1
                processing_details['errors'].append(f"Row {index + 2}: Error processing - {str(e)}")
        
        processing_details['invalid_entries'] = invalid_count
        
        if not valid_participants_data:
            return False, "No valid phone numbers found in CSV file", processing_details
        
        # Batch process valid participants
        added_count, duplicates_count = _batch_process_participants(valid_participants_data, draw_id, 'csv_upload')
        
        processing_details['valid_participants'] = added_count
        processing_details['duplicates_skipped'] = duplicates_count
        
        # Calculate processing time
        processing_details['processing_time'] = (datetime.now() - start_time).total_seconds()
        
        message = generate_success_message(processing_details)
        return True, message, processing_details
        
    except Exception as e:
        db.session.rollback()
        processing_details['errors'].append(f"File processing error: {str(e)}")
        processing_details['processing_time'] = (datetime.now() - start_time).total_seconds()
        current_app.logger.error(f"Error processing CSV: {e}")
        return False, f"Error processing CSV file: {str(e)}", processing_details

def process_excel_file(file_path, draw_id):
    """Process Excel file and add participants to draw with batch operations"""
    processing_details = {
        'total_rows': 0,
        'valid_participants': 0,
        'duplicates_skipped': 0,
        'invalid_entries': 0,
        'errors': [],
        'processing_time': 0
    }
    
    start_time = datetime.now()
    
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        processing_details['total_rows'] = len(df)
        
        if processing_details['total_rows'] == 0:
            return False, "Excel file is empty", processing_details
        
        # Assume first column contains phone numbers
        phone_column = df.columns[0]
        current_app.logger.info(f"Processing Excel with {len(df)} rows, using column: {phone_column}")
        
        # Extract and validate phone numbers in batch
        valid_participants_data = []
        invalid_count = 0
        
        for index, row in df.iterrows():
            try:
                raw_phone = str(row[phone_column]).strip()
                
                # Skip empty rows
                if pd.isna(raw_phone) or raw_phone == '':
                    invalid_count += 1
                    continue
                
                # Enhanced phone number validation
                validation_result = validate_phone_number(raw_phone)
                if not validation_result['is_valid']:
                    invalid_count += 1
                    processing_details['errors'].append(f"Row {index + 2}: {validation_result['error']}")
                    continue
                
                valid_participants_data.append({
                    'phone_number': validation_result['cleaned_number'],
                    'raw_phone': raw_phone
                })
                
            except Exception as e:
                invalid_count += 1
                processing_details['errors'].append(f"Row {index + 2}: Error processing - {str(e)}")
        
        processing_details['invalid_entries'] = invalid_count
        
        if not valid_participants_data:
            return False, "No valid phone numbers found in Excel file", processing_details
        
        # Batch process valid participants
        added_count, duplicates_count = _batch_process_participants(valid_participants_data, draw_id, 'excel_upload')
        
        processing_details['valid_participants'] = added_count
        processing_details['duplicates_skipped'] = duplicates_count
        
        # Calculate processing time
        processing_details['processing_time'] = (datetime.now() - start_time).total_seconds()
        
        message = generate_success_message(processing_details)
        return True, message, processing_details
        
    except Exception as e:
        db.session.rollback()
        processing_details['errors'].append(f"File processing error: {str(e)}")
        processing_details['processing_time'] = (datetime.now() - start_time).total_seconds()
        current_app.logger.error(f"Error processing Excel: {e}")
        return False, f"Error processing Excel file: {str(e)}", processing_details

def _batch_process_participants(participants_data, draw_id, source):
    """Batch process participants with duplicate checking"""
    if not participants_data:
        return 0, 0
    
    try:
        # Extract phone numbers for batch duplicate checking
        phone_numbers = [p['phone_number'] for p in participants_data]
        
        # Check for existing participants in single query (using the new index)
        existing_participants = Participant.query.filter(
            Participant.draw_id == draw_id,
            Participant.phone_number.in_(phone_numbers)
        ).with_entities(Participant.phone_number).all()
        
        existing_numbers = {p[0] for p in existing_participants}
        
        # Prepare new participants for batch insert
        new_participants = []
        for participant_data in participants_data:
            phone_number = participant_data['phone_number']
            
            if phone_number in existing_numbers:
                continue  # Skip duplicates
            
            new_participants.append(Participant(
                phone_number=phone_number,
                draw_id=draw_id,
                source=source,
                is_verified=True,
                added_at=datetime.utcnow()
            ))
        
        # Batch insert using bulk_save_objects for better performance
        if new_participants:
            db.session.bulk_save_objects(new_participants)
            db.session.commit()
        
        added_count = len(new_participants)
        duplicates_count = len(participants_data) - added_count
        
        current_app.logger.info(f"Batch processed: {added_count} added, {duplicates_count} duplicates skipped")
        
        return added_count, duplicates_count
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in batch processing: {e}")
        raise

def validate_phone_number(phone):
    """
    Enhanced phone number validation
    Returns: {
        'is_valid': bool,
        'cleaned_number': str,
        'error': str (if invalid)
    }
    """
    if not phone or len(str(phone).strip()) == 0:
        return {
            'is_valid': False,
            'cleaned_number': '',
            'error': 'Empty phone number'
        }
    
    # Remove all non-digit characters except '+' at the beginning
    cleaned = re.sub(r'(?!^\+)\D', '', str(phone).strip())
    
    # Check if it's a valid length
    if len(cleaned) < 9:
        return {
            'is_valid': False,
            'cleaned_number': cleaned,
            'error': f'Phone number too short: {cleaned}'
        }
    
    # Check if it's too long (more than 15 digits including country code)
    if len(cleaned) > 15:
        return {
            'is_valid': False,
            'cleaned_number': cleaned,
            'error': f'Phone number too long: {cleaned}'
        }
    
    # Check if it contains only digits (except optional + at start)
    if not re.match(r'^\+?\d+$', cleaned):
        return {
            'is_valid': False,
            'cleaned_number': cleaned,
            'error': f'Invalid characters in phone number: {cleaned}'
        }
    
    # Common validation patterns
    # Remove leading zeros if present (except for country codes)
    if cleaned.startswith('0') and not cleaned.startswith('00'):
        cleaned = cleaned[1:]
    
    # Ensure it starts with country code for international numbers
    if cleaned.startswith('00'):
        cleaned = '+' + cleaned[2:]
    
    # For Malawi numbers, ensure they start with 265
    if cleaned.startswith('265') and not cleaned.startswith('+265'):
        cleaned = '+' + cleaned
    
    # If it's a local Malawi number without country code, add it
    if len(cleaned) == 9 and cleaned.isdigit():
        cleaned = '+265' + cleaned
    
    return {
        'is_valid': True,
        'cleaned_number': cleaned,
        'error': None
    }

def generate_success_message(processing_details):
    """Generate a detailed success message from processing details"""
    message_parts = []
    
    if processing_details['valid_participants'] > 0:
        message_parts.append(f"✅ {processing_details['valid_participants']} participants added")
    
    if processing_details['duplicates_skipped'] > 0:
        message_parts.append(f"⚠️ {processing_details['duplicates_skipped']} duplicates skipped")
    
    if processing_details['invalid_entries'] > 0:
        message_parts.append(f"❌ {processing_details['invalid_entries']} invalid entries")
    
    if processing_details['total_rows'] > 0:
        total_processed = (processing_details['valid_participants'] + 
                          processing_details['duplicates_skipped'] + 
                          processing_details['invalid_entries'])
        message_parts.append(f"📊 Processed {total_processed} of {processing_details['total_rows']} rows")
    
    if processing_details['processing_time'] > 0:
        message_parts.append(f"⏱️ Completed in {processing_details['processing_time']:.2f} seconds")
    
    return " | ".join(message_parts)

def is_valid_phone_number(phone):
    """Basic phone number validation (backward compatibility)"""
    validation_result = validate_phone_number(phone)
    return validation_result['is_valid']

def get_allowed_extensions():
    """Get allowed file extensions for upload"""
    return {'csv', 'xlsx', 'xls'}

def get_file_stats(file_path):
    """Get basic file statistics for UI display"""
    try:
        file_ext = file_path.split('.')[-1].lower()
        file_size = os.path.getsize(file_path) / 1024  # Size in KB
        
        if file_ext == 'csv':
            with open(file_path, 'r', encoding='utf-8') as file:
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                df = pd.read_csv(file, delimiter=delimiter)
        else:  # Excel
            df = pd.read_excel(file_path)
        
        stats = {
            'file_size_kb': round(file_size, 2),
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': df.columns.tolist(),
            'file_type': file_ext.upper()
        }
        
        return stats
    
    except Exception as e:
        current_app.logger.error(f"Error getting file stats: {e}")
        return None

def cleanup_uploaded_file(file_path):
    """Clean up uploaded file after processing"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            current_app.logger.info(f"Cleaned up uploaded file: {file_path}")
            return True
    except Exception as e:
        current_app.logger.error(f"Error cleaning up file {file_path}: {e}")
    
    return False