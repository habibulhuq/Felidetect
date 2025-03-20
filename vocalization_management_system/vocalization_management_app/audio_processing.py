import os
import numpy as np
import librosa
import librosa.display
# Force matplotlib to not use any Xwindows backend before importing pyplot
import matplotlib
matplotlib.use('Agg', force=True)
matplotlib.rcParams['figure.max_open_warning'] = 0  # Suppress max figure warning
import matplotlib.pyplot as plt
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import ProcessedAudioFile, DetectedNoiseAudioFile, Spectrogram, Waveform, Database, ProcessingLog
from scipy.signal import stft
from scipy.io import wavfile as wav
from django.conf import settings

def ensure_directory_exists(directory):
    """Ensure that a directory exists, create if it doesn't"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_media_path(subdir, filename):
    """Get the full path for a media file"""
    media_root = getattr(settings, 'MEDIA_ROOT', 'media')
    path = os.path.join(media_root, subdir, filename)
    ensure_directory_exists(os.path.dirname(path))
    return path

def process_audio(file_path, original_audio):
    """
    Process the uploaded audio file:
    - Extract saw calls
    - Save processed clips into ProcessedAudioFile and DetectedNoiseAudioFile tables
    - Generate spectrograms and waveforms
    - Update database status
    """
    try:
        # Load audio file
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message=f"Starting processing of {original_audio.audio_file_name}",
            level='INFO'
        )
        
        y, sr = librosa.load(file_path, sr=None)
        
        # Create processing status entry
        db_entry = Database.objects.create(
            audio_file=original_audio,
            status="Processing"
        )

        # Perform audio processing
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message="Detecting saw calls...",
            level='INFO'
        )
        
        saw_call_segments = detect_saw_calls(y, sr)
        
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message=f"Found {len(saw_call_segments)} potential saw calls",
            level='INFO'
        )

        # Create directory for processed files
        processed_dir = get_media_path('processed_audio', '')

        # Save extracted clips and create database entries
        for i, (start, end) in enumerate(saw_call_segments):
            ProcessingLog.objects.create(
                audio_file=original_audio,
                message=f"Processing clip {i+1}/{len(saw_call_segments)} ({start:.2f}s - {end:.2f}s)",
                level='INFO'
            )
            
            clip_filename = f"{original_audio.audio_file_name}_clip_{i}.wav"
            clip_path = get_media_path('processed_audio', clip_filename)
            
            # Extract and save the clip
            clip_data = y[int(start * sr):int(end * sr)]
            wav.write(clip_path, sr, clip_data)
            
            # Save clip to ProcessedAudioFile model
            processed_clip = ProcessedAudioFile.objects.create(
                audio_file_name=clip_filename,
                original_file=original_audio,
                recording_date=original_audio.recording_date,
                file_size_mb=os.path.getsize(clip_path) / (1024 * 1024)
            )
            
            # Save clip to DetectedNoiseAudioFile model
            DetectedNoiseAudioFile.objects.create(
                original_file=original_audio,
                detected_noise_file_path=os.path.join('processed_audio', clip_filename),
                start_time=start,
                end_time=end,
                saw_count=len(saw_call_segments),
                saw_call_count=len(saw_call_segments),
                file_size_mb=os.path.getsize(clip_path) / (1024 * 1024)
            )
            
            # Generate and save clip spectrogram
            spec_filename = f"{clip_filename}_spec.png"
            clip_spectrogram_path = generate_spectrogram(clip_data, sr, spec_filename)
            
            # Create spectrogram for the clip
            Spectrogram.objects.create(
                audio_file=original_audio,
                image_path=os.path.join('spectrograms', spec_filename),
                clip_start_time=start,
                clip_end_time=end
            )

        # Generate and save full audio spectrograms and waveforms
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message="Generating full audio spectrogram and waveform...",
            level='INFO'
        )
        
        spec_filename = f"{original_audio.audio_file_name}_full.png"
        spectrogram_path = generate_spectrogram(y, sr, spec_filename)
        Spectrogram.objects.create(
            audio_file=original_audio,
            image_path=os.path.join('spectrograms', spec_filename),
            is_full_audio=True
        )

        wave_filename = f"{original_audio.audio_file_name}.png"
        waveform_path = generate_waveform(y, sr, wave_filename)
        Waveform.objects.create(
            audio_file=original_audio,
            image_path=os.path.join('waveforms', wave_filename)
        )

        # Update database status to completed
        db_entry.status = "Processed"
        db_entry.save()
        
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message=f"Processing completed successfully for {original_audio.audio_file_name}",
            level='SUCCESS'
        )

        return True

    except Exception as e:
        error_message = f"Error processing {original_audio.audio_file_name}: {str(e)}"
        ProcessingLog.objects.create(
            audio_file=original_audio,
            message=error_message,
            level='ERROR'
        )
        
        if 'db_entry' in locals():
            db_entry.status = "Failed"
            db_entry.save()
        return False

def detect_saw_calls(audio_data, sample_rate):
    """
    Detects saw calls in an audio signal using STFT analysis.
    
    Parameters:
    - audio_data (numpy array): Audio signal data
    - sample_rate (int): Sampling rate of the audio
    
    Returns:
    - saw_call_timestamps (list of tuples): List of (start_time, end_time) tuples for detected saw calls
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

    # Remove DC offset
    audio_data = audio_data - np.mean(audio_data)

    # Compute STFT
    nperseg = int(segment_duration * sample_rate)
    f, t, Zxx = stft(audio_data, fs=sample_rate, nperseg=nperseg)

    # Get magnitude spectrum
    mag = np.abs(Zxx)

    # Find frequency bins within our range of interest
    freq_mask = (f >= min_freq) & (f <= max_freq)
    freq_indices = np.where(freq_mask)[0]

    # Initialize variables for event detection
    events = []
    current_event = None

    # Analyze each time point
    for i in range(len(t)):
        # Check if any frequency in our range exceeds the magnitude threshold
        magnitudes = mag[freq_indices, i]
        if np.any((magnitudes >= min_mag) & (magnitudes <= max_mag)):
            time = t[i]
            if current_event is None:
                current_event = [time, time]  # [start, end]
            else:
                current_event[1] = time  # Update end time
        elif current_event is not None:
            # Check if the gap is small enough to continue the current event
            if time - current_event[1] > time_threshold:
                events.append(current_event)
                current_event = None

    # Add the last event if there is one
    if current_event is not None:
        events.append(current_event)

    return events

def generate_spectrogram(y, sr, filename):
    """
    Generate a spectrogram from the audio signal.
    """
    try:
        # Create figure without using the global figure manager
        fig = plt.figure(figsize=(12, 8))
        librosa.display.specshow(librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max),
                               y_axis='log', x_axis='time')
        plt.colorbar(format='%+2.0f dB')
        plt.title('Spectrogram')
        
        # Save the spectrogram
        output_path = get_media_path('spectrograms', filename)
        plt.savefig(output_path, bbox_inches='tight')
        
        # Clean up
        plt.close(fig)
        plt.clf()
        
        return output_path
    except Exception as e:
        raise Exception(f"Error generating spectrogram: {str(e)}")
    finally:
        # Ensure cleanup
        plt.close('all')

def generate_waveform(y, sr, filename):
    """
    Generate a waveform from the audio signal.
    """
    try:
        # Create figure without using the global figure manager
        fig = plt.figure(figsize=(12, 4))
        librosa.display.waveshow(y, sr=sr)
        plt.title('Waveform')
        
        # Save the waveform
        output_path = get_media_path('waveforms', filename)
        plt.savefig(output_path, bbox_inches='tight')
        
        # Clean up
        plt.close(fig)
        plt.clf()
        
        return output_path
    except Exception as e:
        raise Exception(f"Error generating waveform: {str(e)}")
    finally:
        # Ensure cleanup
        plt.close('all')

from .models import OriginalAudioFile

def search_by_animal(animal_name: str):
    # function to return list of audio files by name, i.e "amur_leopard"
    try:
        # Fetch all audio files related to the given animal
        audio_files = OriginalAudioFile.objects.filter(animal_type=animal_name)
        
        # Return the list of audio files
        return audio_files
    except Exception as e:
        # In case of an error (e.g., invalid animal name or database error)
        print(f"Error: {str(e)}")
        return []
    
from .models import OriginalAudioFile

def search_by_zoo(zoo_name: str):
    # function to return list of audio files by name, i.e "beardsley"
    try:
        # Fetch all audio files related to the given zoo
        audio_files = OriginalAudioFile.objects.filter(zoo=zoo_name)
        
        # Return the list of audio files
        return audio_files
    except Exception as e:
        # In case of an error (e.g., invalid zoo name or database error)
        print(f"Error: {str(e)}")
        return []



