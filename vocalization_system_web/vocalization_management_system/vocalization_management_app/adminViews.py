from asyncio.log import logger
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from .models import CustomUser, AdminProfile
from .forms import UserRegistrationForm, AudioUploadForm
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from .models import OriginalAudioFile, ProcessedAudioFile, Spectrogram, Waveform, DetectedNoiseAudioFile, Database
from .forms import AudioUploadForm
from .audio_processing import process_audio
from django.utils.timezone import now
from .models import Spectrogram
import os 
import logging

@login_required
def create_user(request):
    if request.user.user_type != '1':  # Only Admin can create users
        messages.error(request, "Access Denied! Only Admins can create new users.")
        return redirect('admin_home')

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New user created successfully!")
            return redirect('manage_staff')  
        else:
            messages.error(request, "Error creating user. Please check the form.")
    else:
        form = UserRegistrationForm()

    return render(request, "admin_template/create_user.html", {"form": form})

@login_required
def admin_home(request):
    if request.user.user_type != '1':  # Restrict access to admin only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')
    return render(request, "admin_template/admin_home.html")


@login_required
def upload_audio(request):
    spectrograms = Spectrogram.objects.all()  # Fetch processed spectrograms

    if request.method == 'POST':
        form = AudioUploadForm(request.POST, request.FILES)
        if form.is_valid():
            audio_file = form.save(commit=False)

            # Ensure the user has an AdminProfile
            if hasattr(request.user, 'adminprofile'):
                audio_file.uploaded_by = request.user.adminprofile
            else:
                messages.error(request, "Only admins can upload audio files.")
                return redirect('upload_audio')

            # Set default recording date if not provided
            if not audio_file.recording_date:
                audio_file.recording_date = now()

            audio_file.save()

            # Save the uploaded file
            file_path = default_storage.save(
                f'audio/{audio_file.audio_file.name}', 
                ContentFile(request.FILES['audio_file'].read())
            )

            logger.info(f"File {audio_file.audio_file_name} saved at {file_path}. Triggering process_audio()...")

            # Run the processing algorithm
            process_audio(file_path, audio_file)

            logger.info(f"Processing completed for {audio_file.audio_file_name}.")

            messages.success(request, "Audio uploaded successfully and processing started!")
            return redirect('upload_audio')
        else:
            messages.error(request, "Error uploading file. Please check the form.")
    else:
        form = AudioUploadForm()

    return render(request, 'admin_template/upload_audio.html', {'form': form, 'spectrograms': spectrograms})




@login_required
def manage_staff(request):
    if request.user.user_type != '1':  # Restrict access to admin only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')

    staff_users = CustomUser.objects.filter(user_type='2')  # Fetch all staff users
    return render(request, "admin_template/manage_staff.html", {"staff_users": staff_users})

@login_required
def upload_audio(request):
    if request.user.user_type != '1':  # Ensure only Admin can access
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')

    if request.method == "POST":
        form = AudioUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Audio file uploaded successfully!")
            return redirect('upload_audio')
        else:
            messages.error(request, "Error uploading file. Please check the form.")
    
    else:
        form = AudioUploadForm()

    return render(request, "admin_template/upload_audio.html", {"form": form})