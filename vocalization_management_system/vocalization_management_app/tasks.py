import time
import threading
import logging
import os
from django.utils import timezone
from django.db import transaction
from .models import Database, ProcessingLog, OriginalAudioFile
from .audio_processing import process_audio
from .excel_generator import generate_excel_report_for_processed_file

# Configure logging
logger = logging.getLogger(__name__)

# Global variables to control the background processor
processor_running = False
processor_thread = None
processing_interval = 10  # seconds between checking for new files


def get_pending_audio_files():
    """
    Get all audio files that have been uploaded but not yet processed
    Returns a queryset of OriginalAudioFile objects with status 'Pending'
    """
    return OriginalAudioFile.objects.filter(database_entry__status='Pending')


def mark_file_as_processing(audio_file):
    """
    Mark a file as currently being processed
    """
    with transaction.atomic():
        db_entry = Database.objects.select_for_update().get(audio_file=audio_file)
        if db_entry.status != 'Pending':
            return False  # File is no longer pending, skip it
        
        db_entry.status = 'Processing'
        db_entry.processing_start_time = timezone.now()
        db_entry.save()
        
        # Log the start of processing
        ProcessingLog.objects.create(
            audio_file=audio_file,
            message=f"Started processing file: {audio_file.audio_file_name}",
            level="INFO"
        )
        return True


def process_single_file(audio_file):
    """
    Process a single audio file and update its status
    Returns True if processing was successful, False otherwise
    """
    try:
        # Mark the file as processing
        if not mark_file_as_processing(audio_file):
            return False  # File was already being processed or is not pending
        
        # Process the audio file
        file_path = audio_file.audio_file.path
        success = process_audio(file_path, audio_file)
        
        if success:
            # Generate Excel report after successful processing
            excel_path = generate_excel_report_for_processed_file(audio_file.file_id)
            
            if excel_path:
                ProcessingLog.objects.create(
                    audio_file=audio_file,
                    message=f"Excel report generated after processing: {os.path.basename(excel_path)}",
                    level="SUCCESS"
                )
            else:
                ProcessingLog.objects.create(
                    audio_file=audio_file,
                    message="Failed to generate Excel report after processing",
                    level="WARNING"
                )
        
        return success
    except Exception as e:
        # Log the error
        ProcessingLog.objects.create(
            audio_file=audio_file,
            message=f"Unexpected error during processing: {str(e)}",
            level="ERROR"
        )
        
        # Update database entry to Failed status
        try:
            db_entry = Database.objects.get(audio_file=audio_file)
            db_entry.status = 'Failed'
            db_entry.processing_end_time = timezone.now()
            db_entry.save()
        except Exception:
            pass
        
        return False


def process_pending_files_continuously():
    """
    Continuously process pending audio files one by one
    This function runs in a separate thread
    """
    global processor_running
    
    logger.info("Background audio processor started")
    
    while processor_running:
        try:
            # Get the next pending file
            pending_files = get_pending_audio_files()
            
            if pending_files.exists():
                # Process one file at a time
                audio_file = pending_files.first()
                logger.info(f"Processing file: {audio_file.audio_file_name}")
                
                # Process the file
                success = process_single_file(audio_file)
                
                if success:
                    logger.info(f"Successfully processed file: {audio_file.audio_file_name}")
                else:
                    logger.warning(f"Failed to process file: {audio_file.audio_file_name}")
            else:
                # No pending files, log and wait
                logger.info("No pending files to process. Waiting for new uploads.")
            
            # Sleep for a while before checking again
            time.sleep(processing_interval)
            
        except Exception as e:
            logger.error(f"Error in background processor: {str(e)}")
            time.sleep(processing_interval)  # Sleep and try again
    
    logger.info("Background audio processor stopped")


def start_background_processor():
    """
    Start the background processing thread if it's not already running
    """
    global processor_running, processor_thread
    
    if processor_running and processor_thread and processor_thread.is_alive():
        logger.info("Background processor is already running")
        return False
    
    processor_running = True
    processor_thread = threading.Thread(target=process_pending_files_continuously)
    processor_thread.daemon = True  # Thread will exit when main program exits
    processor_thread.start()
    
    logger.info("Started background audio processor")
    return True


def stop_background_processor():
    """
    Stop the background processing thread
    """
    global processor_running, processor_thread
    
    if not processor_running or not processor_thread:
        logger.info("Background processor is not running")
        return False
    
    processor_running = False
    processor_thread.join(timeout=5.0)  # Wait for thread to finish
    processor_thread = None
    
    logger.info("Stopped background audio processor")
    return True


def get_processor_status():
    """
    Get the current status of the background processor
    """
    global processor_running, processor_thread
    
    if processor_running and processor_thread and processor_thread.is_alive():
        return "Running"
    else:
        return "Stopped"


def process_pending_audio_files_batch():
    """
    Process all pending audio files in a batch (one by one)
    This is for manual triggering of processing
    Returns a tuple of (processed_count, failed_count)
    """
    pending_files = get_pending_audio_files()
    processed_count = 0
    failed_count = 0
    
    for audio_file in pending_files:
        # Process the file
        success = process_single_file(audio_file)
        
        if success:
            processed_count += 1
        else:
            failed_count += 1
    
    return processed_count, failed_count


def process_pending_audio_files():
    """
    Process all pending audio files in a batch (one by one)
    This is a wrapper function for process_pending_audio_files_batch that can be called from views
    """
    # Start processing in a separate thread to avoid blocking the request
    threading.Thread(target=process_pending_audio_files_batch).start()
    return {'status': 'Processing started in background'}
