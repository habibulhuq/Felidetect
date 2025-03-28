import os
import numpy as np
import librosa
from scipy.signal import stft
from scipy.io import wavfile as wav
from django.conf import settings
import pandas as pd
import re
from django.utils.timezone import now
from .models import ProcessedAudioFile, DetectedNoiseAudioFile, Database, ProcessingLog, OriginalAudioFile
from datetime import datetime, timedelta
import logging
import pandas as pd
from django.core.files.base import ContentFile
import io
import matplotlib as plt

def ensure_directory_exists(directory):
    """Ensure that a directory exists, create if it doesn't"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def parse_audio_filename(filename):
    """
    Parse the audio filename in the format SMM07257_20230201_171502.wav
    
    Breakdown:
    - SMM07257: Song Meter device identifier
        - SMM: Device type (Song Meter Micro)
        - 07257: Device unit number
    - 20230201: Recording date (YYYYMMDD)
    - 171502: Recording time (HHMMSS)
    
    Returns:
        tuple: (device_info, recording_datetime)
            device_info: dict containing:
                - device_type: str (e.g., 'SMM' for Song Meter Micro)
                - device_id: str (e.g., '07257')
                - full_device_id: str (e.g., 'SMM07257')
            recording_datetime: datetime object
    """
    try:
        # Remove file extension if present
        base_name = os.path.splitext(filename)[0]
        
        # Split the filename into components
        device_id, date_str, time_str = base_name.split('_')
        
        # Parse device information
        # Extract device type (first 3 characters) and unit number (rest of the string)
        device_type = device_id[:3]  # e.g., 'SMM'
        unit_number = device_id[3:]  # e.g., '07257'
        
        device_info = {
            'device_type': device_type,
            'device_id': unit_number,
            'full_device_id': device_id
        }
        
        # Parse date and time
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        hour = int(time_str[:2])
        minute = int(time_str[2:4])
        second = int(time_str[4:6])
        
        # Create datetime object
        recording_datetime = datetime(year, month, day, hour, minute, second)
        
        return device_info, recording_datetime
    except (ValueError, IndexError) as e:
        raise ValueError(
            "Invalid filename format. Expected format: SMM07257_20230201_171502.wav\n"
            "- First part should be device ID (e.g., SMM07257)\n"
            "- Second part should be date (YYYYMMDD)\n"
            "- Third part should be time (HHMMSS)\n"
            f"Error: {str(e)}"
        )

def update_audio_metadata(file_path, original_audio):
    """
    Update the metadata of the audio file based on its filename
    This function only updates metadata and doesn't process the audio content
    """
    try:
        # Create a log entry for the start of metadata update
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message="Starting metadata extraction",
            level="INFO"
        )
        
        #saw_call_segments = find_events_within_threshold(y, sr)
        # Get the filename from the path
        filename = os.path.basename(file_path)
        
        # Parse the filename to extract metadata
        try:
            device_info, recording_datetime = parse_audio_filename(filename)
            
            # Update the recording date in the database
            original_audio.recording_date = recording_datetime
            original_audio.save()
            
            # Log successful metadata extraction
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message=f"Successfully extracted metadata. Recording date: {recording_datetime}",
                level="SUCCESS"
            )
            
        except Exception as e:
            # Log error in metadata extraction
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message=f"Error parsing filename: {str(e)}",
                level="WARNING"
            )
        
        # Get file size in MB
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)  # Convert to MB
        
        # Update file size in the database
        original_audio.file_size_mb = file_size_mb
        original_audio.save()
        
        # Create database entry with Pending status if it doesn't exist
        db_entry, created = Database.objects.get_or_create(
            audio_file=original_audio,
            defaults={'status': 'Pending'}
        )
        
        # Log successful metadata update
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message="Metadata update completed successfully",
            level="SUCCESS"
        )
        
        return True
        
    except Exception as e:
        # Log error in metadata update
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message=f"Error updating metadata: {str(e)}",
            level="ERROR"
        )
        return False

def seconds_to_timestamp(seconds):
    """
    Converts seconds to a timestamp in HH:MM:SS.SS format, with seconds rounded to two decimal places.
    
    Parameters:
    - seconds (float): The number of seconds to convert.
    
    Returns:
    - str: The timestamp in HH:MM:SS.SS format.
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{seconds:06.2f}"

def timestamp_to_time_object(timestamp_str):
    """
    Converts a timestamp string in HH:MM:SS.SS format to a float representing seconds.
    
    Parameters:
    - timestamp_str (str): The timestamp string in HH:MM:SS.SS format.
    
    Returns:
    - float: The corresponding time in seconds.
    """
    # Parse the timestamp string
    hours, minutes, seconds = timestamp_str.split(':')
    hours = int(hours)
    minutes = int(minutes)
    seconds = float(seconds)
    
    # Convert to seconds
    total_seconds = hours * 3600 + minutes * 60 + seconds
    
    return total_seconds

def detect_saw_calls(audio_data, sample_rate):
    """
    Detects saw calls in the audio data using STFT analysis.
    
    Parameters:
    - audio_data (numpy.ndarray): The audio data.
    - sample_rate (int): The sample rate of the audio data.
    
    Returns:
    - list: A list of dictionaries containing information about detected saw calls:
            [{'start': start_time_str, 'end': end_time_str, 'magnitude': mag, 'frequency': freq, 'impulse_count': count}]
    """
    # Parameters for saw call detection
    min_mag = 3500
    max_mag = 10000
    min_freq = 15
    max_freq = 300
    segment_duration = 0.1
    time_threshold = 5
    
    # Convert audio data to float32 if not already
    audio_data = audio_data.astype(np.float32)
    
    # Remove DC offset by subtracting the mean
    audio_data -= np.mean(audio_data)
    
def find_events_within_threshold(file_path, dataset, callset, min_mag=3500, max_mag=10000, min_freq=15, max_freq=300, segment_duration=.1, time_threshold=5):
    
    """
    Reads a WAV audio file, computes its STFT to find major magnitude events over time,
    and stores events that exceed a magnitude threshold.

    Parameters:
    - file_path (str): Path to the WAV file.
    - dataset (list): List of lists to store impulses ([file_path, start, end, magnitude, frequency, count]).
    - callset (list): List of lists to store calls ([file_path, start, end, magnitude, frequency, count]).
    - min_mag (float): The magnitude minimum for event detection (default is 3500).
    - max_mag (float): The magnitude maximum for event detection (default is 10000).
    - min_freq (float): The minimum frequency for event detection (default is 15hz).
    - max_freq (float): The maximum frequency for event detection (default is 300hz).
    - segment_duration (float): Duration of each STFT segment in seconds (default is 0.1s).
    - time_threshold (float): Time threshold in seconds for merging events (default is 5s).

    Returns:
    - None
    """
    try:
        sample_rate, audio_data = wav.read(file_path)
    except Exception as e:
        print(f"Error: {file_path} is not an audio file or doesn't exist. ({e})")
        return

    # If stereo, take just one channel
    if len(audio_data.shape) == 2:
        audio_data = audio_data[:, 0]

    # Convert audio data to np.float32 for efficiency
    audio_data = audio_data.astype(np.float32)
    # Remove DC offset by subtracting the mean
    audio_data -= np.mean(audio_data)
    

    # Compute the STFT with a specified segment duration
    nperseg = int(segment_duration * sample_rate)
    frequencies, times, Zxx = stft(audio_data, fs=sample_rate, nperseg=nperseg)
    magnitude = np.abs(Zxx)  # Magnitude of the STFT result


    # Initialize variables for event detection
    last_event_time_seconds = None
    event_data = []
    # Iterate over each time frame, using np.where to find indices where magnitude exceeds threshold

    for time_idx in range(magnitude.shape[1]):
        # Filter for magnitudes above the threshold
        magnitudes_at_time = magnitude[:, time_idx]
        valid_indices = np.where(np.logical_and(magnitudes_at_time < max_mag, magnitudes_at_time > min_mag))[0]
        
        if valid_indices.size == 0:
            continue  # Skip if no magnitudes exceed the threshold
        
        event_time_seconds = times[time_idx]
        # Format with higher precision (2 decimal places for seconds)
        event_time_str = seconds_to_timestamp(event_time_seconds)
        
        # Extract valid frequencies and magnitudes
        valid_frequencies = frequencies[valid_indices]
        valid_magnitudes = magnitudes_at_time[valid_indices]
        
        # Filter frequencies between min_freq and max_freq Hz
        freq_mask = (valid_frequencies < max_freq) & (valid_frequencies > min_freq)
        valid_frequencies = valid_frequencies[freq_mask]
        valid_magnitudes = valid_magnitudes[freq_mask]
        
        # Process events
        for freq, mag in zip(valid_frequencies, valid_magnitudes):
            if last_event_time_seconds is None:
                # First event, add to dataset
                event_data.append({
                    'start': event_time_str,
                    'end': event_time_str,
                    'start_seconds': event_time_seconds,  # Store raw seconds for precise calculations
                    'end_seconds': event_time_seconds,    # Store raw seconds for precise calculations
                    'magnitude': float(mag),
                    'frequency': float(freq),
                    'impulse_count': 1
                })
                last_event_time_seconds = event_time_seconds
            else:
                # Check if the event is within the time threshold and more than 0.1 seconds later
                time_diff = event_time_seconds - last_event_time_seconds
                
                if time_diff <= time_threshold and time_diff > 0.1:  # Events within threshold are merged
                    # Extend the duration of the last event
                    event_data[-1]['end'] = event_time_str
                    event_data[-1]['end_seconds'] = event_time_seconds
                    # Calculate duration in seconds
                    duration = event_data[-1]['end_seconds'] - event_data[-1]['start_seconds']
                    # Increase count of impulses
                    event_data[-1]['impulse_count'] += 1
                    # Update magnitude and frequency if higher
                    if mag > event_data[-1]['magnitude']:
                        event_data[-1]['magnitude'] = float(mag)
                        event_data[-1]['frequency'] = float(freq)
                elif time_diff > time_threshold:
                    # Add new event
                    event_data.append({
                        'start': event_time_str,
                        'end': event_time_str,
                        'start_seconds': event_time_seconds,
                        'end_seconds': event_time_seconds,
                        'magnitude': float(mag),
                        'frequency': float(freq),
                        'impulse_count': 1
                    })
                
                # Update last event time
                last_event_time_seconds = event_time_seconds
    
    # Filter out events with less than 3 impulses (likely false positives)
    filtered_events = [event for event in event_data if event['impulse_count'] >= 3]
    
    return filtered_events


def generate_excel_report(original_audio, saw_calls):
    """
    Generate an Excel report for the detected saw calls.
    
    Parameters:
    - original_audio: OriginalAudioFile instance
    - saw_calls: List of dictionaries containing saw call data
    
    Returns:
    - Path to the saved Excel file
    """
    try:
        # Extract date from filename if available
        filename = original_audio.audio_file_name
        file_date = None
        try:
            device_info, recording_datetime = parse_audio_filename(filename)
            file_date = recording_datetime.date()
        except Exception as e:
            # Log error in date extraction but continue with report generation
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message=f"Warning: Could not extract date from filename: {str(e)}",
                level="WARNING"
            )
        
        # Create a DataFrame with the saw call data
        if saw_calls:
            data = []
            for call in saw_calls:
                row = {
                    'File': original_audio.audio_file_name,
                    'Start Time': call['start'],
                    'End Time': call['end'],
                    'Duration (s)': round(call['end_seconds'] - call['start_seconds'], 2),
                    'Frequency (Hz)': round(call['frequency'], 2),
                    'Magnitude': round(call['magnitude'], 2),
                    'Impulses': call['impulse_count']
                }
                
                # Add date if available
                if file_date:
                    row['Date'] = file_date.strftime('%Y-%m-%d')
                
                data.append(row)
            
            # Create DataFrame with ordered columns
            columns = ['File', 'Date', 'Start Time', 'End Time', 'Duration (s)', 'Frequency (Hz)', 'Magnitude', 'Impulses']
            df = pd.DataFrame(data)
            # Reorder columns, but only include those that exist
            available_columns = [col for col in columns if col in df.columns]
            df = df[available_columns]
        else:
            # Create empty DataFrame if no saw calls detected
            columns = ['File', 'Date', 'Start Time', 'End Time', 'Duration (s)', 'Frequency (Hz)', 'Magnitude', 'Impulses']
            df = pd.DataFrame(columns=columns)
        
        # Add file metadata
        metadata_df = pd.DataFrame([
            {'Property': 'File Name', 'Value': original_audio.audio_file_name},
            {'Property': 'Upload Date', 'Value': original_audio.upload_date.strftime('%Y-%m-%d %H:%M:%S')},
            {'Property': 'Recording Date', 'Value': original_audio.recording_date.strftime('%Y-%m-%d %H:%M:%S') if original_audio.recording_date else 'Unknown'},
            {'Property': 'File Size (MB)', 'Value': round(original_audio.file_size_mb, 2) if original_audio.file_size_mb else 'Unknown'},
            {'Property': 'Animal Type', 'Value': original_audio.get_animal_type_display()},
            {'Property': 'Total Saw Calls', 'Value': len(saw_calls)},
            {'Property': 'Total Impulses', 'Value': sum(call['impulse_count'] for call in saw_calls) if saw_calls else 0},
            {'Property': 'Analysis Date', 'Value': now().strftime('%Y-%m-%d %H:%M:%S')}
        ])
        
        # Create a BytesIO object to save the Excel file
        excel_file = io.BytesIO()
        
        # Create ExcelWriter object with the BytesIO object
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            df.to_excel(writer, sheet_name='Saw Calls', index=False)
            
            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for i, col in enumerate(worksheet.columns):
                    max_length = 0
                    column = col[0].column_letter
                    for cell in col:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column].width = adjusted_width
        
        # Reset the pointer to the beginning of the BytesIO object
        excel_file.seek(0)
        
        # Generate a filename for the Excel file
        excel_filename = f"{os.path.splitext(original_audio.audio_file_name)[0]}_analysis.xlsx"
        
        # Save the Excel file to the OriginalAudioFile model
        original_audio.analysis_excel.save(excel_filename, ContentFile(excel_file.read()), save=True)
        
        # Log successful Excel generation
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message=f"Generated Excel report: {excel_filename}",
            level="SUCCESS"
        )
        
        return original_audio.analysis_excel.path
        
    except Exception as e:
        # Log error in Excel generation
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message=f"Error generating Excel report: {str(e)}",
            level="ERROR"
        )
        return None

def process_audio(file_path, original_audio):
    """
    Process the uploaded audio file and store saw call timeframes.
    Uses improved STFT-based detection to accurately identify and log saw calls.
    """
    try:
        # Check if this file has already been processed
        db_entry = Database.objects.filter(audio_file=original_audio).first()
        
        if db_entry and db_entry.status == 'Processed':
            # Log that file is already processed
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message="File already processed. Skipping processing.",
                level="INFO"
            )
            return True
        
        # Update database entry to Processing status
        if db_entry:
            db_entry.status = 'Processing'
            db_entry.processing_start_time = now()
            db_entry.save()
        else:
            db_entry = Database.objects.create(
                audio_file=original_audio,
                status='Processing',
                processing_start_time=now()
            )
        
        # Log processing start
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message="Starting audio processing",
            level="INFO"
        )
        
        # Load the audio file
        try:
            # First try using scipy.io.wavfile for better compatibility with various WAV formats
            try:
                ProcessingLog.objects.create(
                    audio_file=original_audio,
                    message="Attempting to load audio with scipy.io.wavfile",
                    level="INFO"
                )
                sample_rate, audio_data = wav.read(file_path)
                
                # Convert to mono if stereo
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                
                ProcessingLog.objects.create(
                    audio_file=original_audio,
                    message=f"Loaded audio file with scipy.io.wavfile: {sample_rate}Hz, {len(audio_data)/sample_rate:.2f}s",
                    level="SUCCESS"
                )
            except Exception as e:
                # If scipy fails, try librosa
                ProcessingLog.objects.create(
                    audio_file=original_audio,
                    message=f"scipy.io.wavfile failed: {str(e)}. Trying librosa...",
                    level="WARNING"
                )
                
                audio_data, sample_rate = librosa.load(file_path, sr=None, mono=True)
                
                ProcessingLog.objects.create(
                    audio_file=original_audio,
                    message=f"Loaded audio file with librosa: {sample_rate}Hz, {len(audio_data)/sample_rate:.2f}s",
                    level="SUCCESS"
                )
            
            # Update file metadata if not already set
            if not original_audio.duration_seconds:
                duration_seconds = len(audio_data) / sample_rate
                original_audio.duration_seconds = duration_seconds
                original_audio.duration = seconds_to_timestamp(duration_seconds)
                original_audio.sample_rate = sample_rate
                original_audio.save()
                
                ProcessingLog.objects.create(
                    audio_file=original_audio,
                    message=f"Updated file metadata: Duration={original_audio.duration}, Sample Rate={sample_rate}Hz",
                    level="INFO"
                )
            
            # Detect saw calls using STFT analysis
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message="Starting saw call detection with STFT analysis",
                level="INFO"
            )
            
            saw_calls = detect_saw_calls(audio_data, sample_rate)
            
            # Filter out calls with less than 3 impulses (likely false positives)
            filtered_saw_calls = [call for call in saw_calls if call['impulse_count'] >= 3]
            
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message=f"Detected {len(filtered_saw_calls)} saw calls after filtering (minimum 3 impulses required)",
                level="SUCCESS"
            )
            
        except Exception as e:
            # Log error in saw call detection
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message=f"Error detecting saw calls: {str(e)}",
                level="ERROR"
            )
            
            # Update database entry to Failed status
            db_entry.status = 'Failed'
            db_entry.processing_end_time = now()
            db_entry.save()
            return False
        
        # Extract date from filename if available
        file_date = None
        try:
            device_info, recording_datetime = parse_audio_filename(original_audio.audio_file_name)
            # Update the recording date in the database if not already set
            if not original_audio.recording_date:
                original_audio.recording_date = recording_datetime
                original_audio.save()
            file_date = recording_datetime.date()
        except Exception as e:
            # Log warning but continue processing
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message=f"Warning: Could not extract date from filename: {str(e)}",
                level="WARNING"
            )
        
        # Store saw call timeframes
        saw_count = 0
        for saw_call in filtered_saw_calls:
            try:
                # Convert timestamp strings to time objects for database storage
                start_seconds = saw_call['start_seconds']
                end_seconds = saw_call['end_seconds']
                
                # Calculate hours, minutes, seconds for start time
                start_hours, start_remainder = divmod(int(start_seconds), 3600)
                start_minutes, start_seconds_int = divmod(start_remainder, 60)
                start_microseconds = int((start_seconds - int(start_seconds)) * 1000000)
                
                # Calculate hours, minutes, seconds for end time
                end_hours, end_remainder = divmod(int(end_seconds), 3600)
                end_minutes, end_seconds_int = divmod(end_remainder, 60)
                end_microseconds = int((end_seconds - int(end_seconds)) * 1000000)
                
                # Create time objects
                from datetime import time
                start_time_obj = time(start_hours, start_minutes, start_seconds_int, start_microseconds)
                end_time_obj = time(end_hours, end_minutes, end_seconds_int, end_microseconds)
                
                # Create detected noise entry
                DetectedNoiseAudioFile.objects.create(
                    original_file=original_audio,
                    detected_noise_file_path="",  # We're not creating actual files
                    start_time=start_time_obj,
                    end_time=end_time_obj,
                    saw_count=saw_call['impulse_count'],  # Number of impulses in this call
                    saw_call_count=1,  # Each entry represents one saw call
                    file_size_mb=0.0,  # No actual file
                    frequency=saw_call['frequency'],
                    magnitude=saw_call['magnitude']
                )
                saw_count += 1
                
                # Log individual saw call detection with precise timestamps
                ProcessingLog.objects.create(
                    audio_file=original_audio,
                    message=f"Detected saw call: Start={saw_call['start']}, End={saw_call['end']}, Duration={(end_seconds-start_seconds):.2f}s, Impulses={saw_call['impulse_count']}, Freq={saw_call['frequency']:.2f}Hz, Mag={saw_call['magnitude']:.2f}",
                    level="INFO"
                )
            except Exception as e:
                ProcessingLog.objects.create(
                    audio_file=original_audio,
                    message=f"Error storing saw call data: {str(e)}",
                    level="WARNING"
                )
        
        # If no saw calls were detected, log this explicitly
        if saw_count == 0:
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message="No saw calls detected in this audio file",
                level="INFO"
            )
        else:
            # Log successful storage of saw calls
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message=f"Successfully stored {saw_count} saw call timeframes",
                level="SUCCESS"
            )
        
        # Update database entry to Processed status
        db_entry.status = 'Processed'
        db_entry.processing_end_time = now()
        db_entry.save()
        
        # Log successful processing completion
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message="Audio processing completed successfully",
            level="SUCCESS"
        )
        
        return True
        
    except Exception as e:
        # Log error in processing
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message=f"Error processing audio file: {str(e)}",
            level="ERROR"
        )
        
        # Update database entry to Failed status
        db_entry = Database.objects.filter(audio_file=original_audio).first()
        if db_entry:
            db_entry.status = 'Failed'
            db_entry.processing_end_time = now()
            db_entry.save()
        
        return False

def create_calls_timeline(df):
    """
    Creates a timeline of detected call events from the DataFrame produced by find_events_within_threshold.

    Parameters:
    - df (pd.DataFrame): DataFrame containing columns ['File', 'Start', 'End', 'Magnitude', 'Frequency', 'Count']

    Returns:
    - calls_per_day (pd.DataFrame): Aggregated number of calls per day
    """
    # Ensure required columns exist
    if 'File' not in df.columns or 'Start' not in df.columns or 'Count' not in df.columns:
        raise ValueError("DataFrame must contain 'File', 'Start', and 'Count' columns.")

    # Extract date from Start timestamp
    df['date'] = pd.to_datetime(df['Start']).dt.date

    # Aggregate calls per day
    calls_per_day = df.groupby('date')['Count'].sum().reset_index()

    # Plot the timeline
    plt.figure(figsize=(10, 5))
    plt.plot(calls_per_day['date'], calls_per_day['Count'], marker='o', linestyle='-')
    plt.xlabel('Date')
    plt.ylabel('Number of Calls')
    plt.title('Calls Per Day Timeline')
    plt.xticks(rotation=45)
    plt.grid()
    plt.show()

    return calls_per_day


def get_pending_audio_files():
    """
    Get all audio files that have been uploaded but not yet processed
    """
    from .models import OriginalAudioFile, Database
    return OriginalAudioFile.objects.filter(database_entry__status='Pending')

def process_pending_audio_files():
    """
    Process all pending audio files one by one
    Returns a tuple of (processed_count, failed_count)
    """
    # Import here to avoid circular imports
    from .tasks import process_pending_audio_files_batch
    return process_pending_audio_files_batch()

def get_processing_status():
    """
    Get the current processing status counts
    """
    from .models import OriginalAudioFile, Database
    from .tasks import get_processor_status
    
    total_files = OriginalAudioFile.objects.count()
    pending_files = Database.objects.filter(status='Pending').count()
    processing_files = Database.objects.filter(status='Processing').count()
    processed_files = Database.objects.filter(status='Processed').count()
    failed_files = Database.objects.filter(status='Failed').count()
    
    return {
        'total': total_files,
        'pending': pending_files,
        'processing': processing_files,
        'processed': processed_files,
        'failed': failed_files,
        'processor_status': get_processor_status()
    }
