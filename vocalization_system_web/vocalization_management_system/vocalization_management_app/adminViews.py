from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import CustomUser, OriginalAudioFile, Database, ProcessingLog, DetectedNoiseAudioFile, Spectrogram
from django.core.files.storage import FileSystemStorage
import os
from .audio_processing import process_audio
from django.utils.timezone import now
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
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
    # Get processing statistics
    total_files = OriginalAudioFile.objects.count()
    processing_files = Database.objects.filter(status='Processing').count()
    processed_files = Database.objects.filter(status='Processed').count()
    failed_files = Database.objects.filter(status='Failed').count()
    
    # Get recent processing logs
    recent_logs = ProcessingLog.objects.select_related('audio_file').order_by('-timestamp')[:10]
    
    # Get files currently being processed
    processing_files_details = Database.objects.filter(
        status='Processing'
    ).select_related('audio_file').order_by('-audio_file__upload_date')
    
    context = {
        'total_files': total_files,
        'processing_files': processing_files,
        'processed_files': processed_files,
        'failed_files': failed_files,
        'recent_logs': recent_logs,
        'processing_files_details': processing_files_details,
    }
    
    return render(request, "admin_template/admin_home.html", context)


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

            logging.info(f"File {audio_file.audio_file_name} saved at {file_path}. Triggering process_audio()...")

            # Run the processing algorithm
            process_audio(file_path, audio_file)

            logging.info(f"Processing completed for {audio_file.audio_file_name}.")

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

def admin_view_spectrograms(request, file_id=None):
    """
    Admin view to display spectrograms and extracted clips with search functionality
    """

    context = {}
    
    if file_id:
        # Get specific file and its clips
        original_file = get_object_or_404(OriginalAudioFile, file_id=file_id)
        context['original_file'] = original_file
        
        # Get full audio spectrogram
        full_spectrogram = original_file.spectrograms.filter(is_full_audio=True).first()
        context['full_spectrogram'] = full_spectrogram
        
        # Get all clip spectrograms and detected noises for this file
        clip_spectrograms = original_file.spectrograms.filter(
            is_full_audio=False
        ).order_by('clip_start_time')
        
        detected_noises = original_file.detected_noises.all().order_by('start_time')
        
        # Combine spectrograms with their audio clips
        clips_data = []
        for spec, noise in zip(clip_spectrograms, detected_noises):
            clips_data.append({
                'spectrogram': spec,
                'audio_clip': noise,
                'start_time': spec.clip_start_time,
                'end_time': spec.clip_end_time,
            })
        
        context['clips_data'] = clips_data
        
        # Get processing status
        processing_status = original_file.database_entry.first()
        context['processing_status'] = processing_status
        
    else:
        # Get search query
        search_query = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '')
        animal_type_filter = request.GET.get('animal_type', '')
        
        # Base query
        audio_files = OriginalAudioFile.objects.all()
        
        # Apply search if provided
        if search_query:
            audio_files = audio_files.filter(
                audio_file_name__icontains=search_query
            )
        
        # Apply filters if provided
        if status_filter:
            audio_files = audio_files.filter(database_entry__status=status_filter)
        if animal_type_filter:
            audio_files = audio_files.filter(animal_type=animal_type_filter)
            
        # Order by upload date
        audio_files = audio_files.order_by('-upload_date')
        
        context.update({
            'audio_files': audio_files,
            'search_query': search_query,
            'status_filter': status_filter,
            'animal_type_filter': animal_type_filter,
        })
    
    return render(request, 'admin_template/view_spectrograms.html', context)

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