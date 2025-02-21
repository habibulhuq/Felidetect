from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import CustomUser, OriginalAudioFile, Database, ProcessingLog, DetectedNoiseAudioFile, Spectrogram, AdminProfile
from django.core.files.storage import FileSystemStorage
import os
from .audio_processing import process_audio
from django.utils.timezone import now
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
import logging
from .forms import AudioUploadForm

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
    """
    Admin home view showing dashboard statistics and audio files
    """
    if request.user.user_type != '1':  # Restrict access to admin only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')

    # Get counts for dashboard
    total_files = OriginalAudioFile.objects.count()
    processing_files = Database.objects.filter(status='Processing').count()
    processed_files = Database.objects.filter(status='Processed').count()
    failed_files = Database.objects.filter(status='Failed').count()
    
    # Get processing files details
    processing_files_details = Database.objects.filter(
        status='Processing'
    ).select_related('audio_file').order_by('-audio_file__upload_date')
    
    # Get recent processing logs
    recent_logs = ProcessingLog.objects.select_related('audio_file').order_by('-timestamp')[:10]
    
    # Get recent audio files
    audio_files = OriginalAudioFile.objects.select_related('uploaded_by').prefetch_related(
        'database_entry'
    ).order_by('-upload_date')[:10]
    
    context = {
        'total_files': total_files,
        'processing_files': processing_files,
        'processed_files': processed_files,
        'failed_files': failed_files,
        'processing_files_details': processing_files_details,
        'recent_logs': recent_logs,
        'audio_files': audio_files,
        'page_title': 'Admin Dashboard'
    }
    
    return render(request, 'admin_template/admin_home.html', context)


@login_required
def upload_audio(request):
    """
    View for uploading new audio files
    """
    if request.user.user_type != '1':  # Restrict access to admin only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')
        
    # Get or create AdminProfile for the user
    admin_profile, created = AdminProfile.objects.get_or_create(user=request.user)
        
    if request.method == 'POST':
        form = AudioUploadForm(request.POST, request.FILES)         
        if form.is_valid():
            try:
                # Save the audio file
                audio_file = form.save(commit=False)
                audio_file.upload_date = now()
                audio_file.uploaded_by = admin_profile
                audio_file.audio_file_name = request.FILES['audio_file'].name
                audio_file.save()
                
                # Create media directories if they don't exist
                media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media')
                audio_dir = os.path.join(media_dir, 'audio_files')
                os.makedirs(audio_dir, exist_ok=True)
                
                # Get the full path to save the file
                file_path = os.path.join(audio_dir, audio_file.audio_file_name)
                
                # Save the uploaded file
                with open(file_path, 'wb+') as destination:
                    for chunk in request.FILES['audio_file'].chunks():
                        destination.write(chunk)
                
                # Create database entry for processing status
                Database.objects.create(
                    audio_file=audio_file,
                    status='Processing',
                )
                
                # Create initial processing log
                ProcessingLog.objects.create(
                    audio_file=audio_file,
                    timestamp=now(),
                    level='INFO',
                    message=f'Audio file "{audio_file.audio_file_name}" uploaded successfully.'
                )
                
                # Process the audio file
                process_audio(file_path, audio_file)
                
                messages.success(request, 'Audio file uploaded successfully!')
                return redirect('admin_home')
                
            except Exception as e:
                messages.error(request, f'Error uploading file: {str(e)}')
                return redirect('upload_audio')
    else:
        form = AudioUploadForm()
    
    # Get list of uploaded files with details
    audio_files = OriginalAudioFile.objects.select_related('uploaded_by').prefetch_related(
        'database_entry'
    ).order_by('-upload_date')
    
    context = {
        'form': form,
        'audio_files': audio_files,
        'page_title': 'Upload Audio'
    }
    
    return render(request, 'admin_template/upload_audio.html', context)


@login_required
def manage_staff(request):
    if request.user.user_type != '1':  # Restrict access to admin only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')

    staff_users = CustomUser.objects.filter(user_type='2')  # Fetch all staff users
    return render(request, "admin_template/manage_staff.html", {"staff_users": staff_users})

@login_required
def view_spectrograms(request, file_id):
    """
    View for displaying spectrograms and classified clips for a specific audio file
    """
    if request.user.user_type != '1':  # Restrict access to admin only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')
    
    # Get the audio file
    audio_file = get_object_or_404(OriginalAudioFile, file_id=file_id)
    
    # Get all spectrograms for this file
    spectrograms = Spectrogram.objects.filter(audio_file=audio_file)
    
    # Get all detected noise clips
    detected_noises = DetectedNoiseAudioFile.objects.filter(original_file=audio_file)
    
    # Get processing logs
    processing_logs = ProcessingLog.objects.filter(audio_file=audio_file).order_by('-timestamp')
    
    # Get processing status
    processing_status = Database.objects.filter(audio_file=audio_file).first()
    
    context = {
        'audio_file': audio_file,
        'spectrograms': spectrograms,
        'detected_noises': detected_noises,
        'processing_logs': processing_logs,
        'processing_status': processing_status,
    }
    
    return render(request, 'admin_template/view_spectrograms.html', context)