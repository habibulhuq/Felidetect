import os
import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import ProcessedAudioFile, DetectedNoiseAudioFile, Spectrogram, Waveform, Database
from scipy.signal import stft
from scipy.io import wavfile as wav


def process_audio(file_path, original_audio):
    """
    Process the uploaded audio file:
    - Extract saw calls
    - Save processed clips into ProcessedAudioFile and DetectedNoiseAudioFile tables
    - Generate spectrograms and waveforms
    - Update database status
    """
    
    # Load audio file
    y, sr = librosa.load(file_path, sr=None)

    # Perform audio processing (Replace with actual saw call detection algorithm)
    saw_call_segments = detect_saw_calls(y, sr)

    # Save extracted clips and create database entries
    for i, (start, end) in enumerate(saw_call_segments):
        clip_filename = f"{original_audio.audio_file_name}_clip_{i}.wav"
        clip_path = f'processed_audio/{clip_filename}'
        
        # Extract and save the clip
        librosa.output.write_wav(clip_path, y[int(start * sr):int(end * sr)], sr)
        
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
            detected_noise_file_path=clip_path,
            start_time=start,
            end_time=end,
            saw_count=len(saw_call_segments),
            saw_call_count=len(saw_call_segments),
            file_size_mb=os.path.getsize(clip_path) / (1024 * 1024)
        )

    # Generate and save spectrograms
    spectrogram_path = generate_spectrogram(y, sr, original_audio.audio_file_name)
    Spectrogram.objects.create(audio_file=original_audio, image_path=spectrogram_path)

    # Generate and save waveforms
    waveform_path = generate_waveform(y, sr, original_audio.audio_file_name)
    Waveform.objects.create(audio_file=original_audio, image_path=waveform_path)

    # Update database status
    Database.objects.create(audio_file=original_audio, status="Processed")

    print(f"Processing completed for {file_path}")

def detect_saw_calls(sample_rate, audio_data):
    """
    Detects saw calls in an audio file using STFT analysis.
    
    Parameters:
    - sample_rate (int): Sampling rate of the audio file.
    - audio_data (numpy array): Audio signal data.
    
    Returns:
    - saw_call_timestamps (list of tuples): List of (start_time, end_time) tuples for detected saw calls.
    """

    dataset = []  # List to store detected events
    
    # Call the threshold-based detection function
    find_events_within_threshhold(
        file_path="sample_audio.wav",  # Placeholder (Not needed in function but required for consistency)
        dataset=dataset,
        min_mag=3500,  
        max_mag=10000,  
        min_freq=15,  
        max_freq=300,  
        segment_duration=0.1,  
        time_threshold=5  
    )

    # Extract timestamps for detected saw calls
    saw_call_timestamps = [(event[1], event[2]) for event in dataset]  # Start & End times
    
    return saw_call_timestamps

def find_events_within_threshhold(file_path, dataset, min_mag=3500, max_mag=10000, min_freq=15, max_freq=300, segment_duration=.1, time_threshold=5):
    """
    Reads a WAV audio file, computes its STFT to find major magnitude events over time,
    and stores events that exceed a magnitude threshold.

    Parameters:
    - file_path (str): Path to the WAV file.
    - dataset (list): List of lists to store events ([file_path, start, end, magnitude, frequency, count]).
    - min_mag (float): The magnitude minimum for event detection (default is 3500).
    - max_mag (float): The magnitude maximum for event detection (default is 10000).
    - min_freq (float): The minimum frequency for event detection (default is 15hz).
    - max_freq (float): The maximum frequency for event detection (default is 300hz).
    - segment_duration (float): Duration of each STFT segment in seconds (default is 0.1s).
    - time_threshold (float): Time threshold in seconds for merging events (default is 5s).
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
                    # increase count of calls
                    event_data[-1][5] += 1
                elif time_diff > time_threshold:
                    # Add new event
                    event_data.append([file_path, event_time_str, event_time_str, mag, freq, 1])
                # updates last event time
                last_event_time_seconds = event_time_seconds

    # Append all collected events to dataset at once
    dataset.extend(event_data)
    
def seconds_to_timestamp(seconds):
    """
    Converts seconds to a timestamp in HH:MM:SS format, with seconds rounded to two decimal places.
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02}:{int(minutes):02}:{seconds:05.2f}"

def generate_spectrogram(y, sr, filename):
    """
    Generate a spectrogram from the audio signal.
    """
    plt.figure(figsize=(10, 4))
    D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
    librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='log')
    plt.colorbar(format='%+2.0f dB')
    plt.title('Spectrogram')
    
    spectrogram_path = f'spectrograms/{filename}.png'
    plt.savefig(spectrogram_path)
    plt.close()
    
    return spectrogram_path

def generate_waveform(y, sr, filename):
    """
    Generate a waveform from the audio signal.
    """
    plt.figure(figsize=(10, 4))
    librosa.display.waveshow(y, sr=sr)
    plt.title('Waveform')
    
    waveform_path = f'waveforms/{filename}.png'
    plt.savefig(waveform_path)
    plt.close()
    
    return waveform_path
