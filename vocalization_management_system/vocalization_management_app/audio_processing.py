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
import pandas as pd
import re

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
        
        saw_call_segments = find_events_within_threshold(y, sr)
        
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

def seconds_to_timestamp(seconds):
    """
    Converts seconds to a timestamp in HH:MM:SS format, with seconds rounded to two decimal places.
    Parameters:
    - seconds (float): The number of seconds to convert.
    Returns:
    - str: The timestamp in HH:MM:SS.SS format.
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02}:{int(minutes):02}:{seconds:05.2f}"

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
        event_time_str = seconds_to_timestamp(event_time_seconds)

        # Extract valid frequencies and magnitudes
        valid_frequencies = frequencies[valid_indices]
        valid_magnitudes = magnitudes_at_time[valid_indices]

        # Filter frequencies between 15 and 300 Hz
        freq_mask = (valid_frequencies < max_freq) & (valid_frequencies > min_freq)
        valid_frequencies = valid_frequencies[freq_mask]
        valid_magnitudes = valid_magnitudes[freq_mask]

        # Process events more efficiently
        for freq, mag in zip(valid_frequencies, valid_magnitudes):
            if last_event_time_seconds is None:
                # First event, add to dataset
                event_data.append([file_path, event_time_str, event_time_str, mag, freq, 1])
                last_event_time_seconds = event_time_seconds

            else:
                # Check if the event is within the 5-second window and more than .1 seconds later
                time_diff = event_time_seconds - last_event_time_seconds

                if time_diff <= time_threshold and time_diff > .1:  # Events within 5 seconds are merged
                    # Extend the duration of the last event
                    event_data[-1][2] = seconds_to_timestamp(event_time_seconds)
                    # increase count of impulses
                    event_data[-1][5] += 1

                    # checks if impulses are greater than 3
                    if int(event_data[-1][5]) > 2:  # Ensure that count is an integer before comparison
                      # if its 3, create an event based off of impulse data
                      if int(event_data[-1][5]) < 4:
                        callset.append([file_path, event_data[-1][1], event_data[-1][2], event_data[-1][3], event_data[-1][4], 1])

                        # if more than 3
                      elif int(event_data[-1][5]) % 3 == 0:
                        # Extend the duration of the last call
                        callset[-1][2] = event_data[-1][2]
                        # set count of calls to impulse divided by 3
                        callset[-1][5] = int(event_data[-1][5]) / 3

                elif time_diff > time_threshold:
                    # Add new event
                    event_data.append([file_path, event_time_str, event_time_str, mag, freq, 1])

                # updates last event time
                last_event_time_seconds = event_time_seconds

    # Append all collected events to dataset at once
    dataset.extend(event_data)

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