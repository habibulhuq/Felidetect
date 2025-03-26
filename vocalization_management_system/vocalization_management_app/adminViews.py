from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
import logging

from .models import CustomUser, OriginalAudioFile, Database, ProcessingLog, DetectedNoiseAudioFile, Spectrogram, AdminProfile
from .forms import UserRegistrationForm, AudioUploadForm
from .audio_processing import update_audio_metadata, process_pending_audio_files, get_processing_status
from .tasks import process_pending_audio_files, get_processor_status
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import json

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

    # Get processing status data
    status_data = get_processing_status()
    
    # Get pending files details
    pending_files_details = Database.objects.filter(
        status='Pending'
    ).select_related('audio_file').order_by('-audio_file__upload_date')
    
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
        'total_files': status_data['total'],
        'pending_files': status_data['pending'],
        'processing_files': status_data['processing'],
        'processed_files': status_data['processed'],
        'failed_files': status_data['failed'],
        'processor_status': status_data['processor_status'],
        'pending_files_details': pending_files_details,
        'processing_files_details': processing_files_details,
        'recent_logs': recent_logs,
        'audio_files': audio_files,
        'page_title': 'Admin Dashboard'
    }
    
    return render(request, 'admin_template/admin_home.html', context)


@login_required
def upload_audio(request):
    if not request.user.is_authenticated or request.user.user_type != '1':
        return redirect('login')
    
    # Get recent audio files for display
    audio_files = OriginalAudioFile.objects.all().order_by('-upload_date')[:10]
    
    if request.method == 'POST':
        form = AudioUploadForm(request.POST)
        
        if form.is_valid():
            # Get form data
            animal_type = form.cleaned_data['animal_type']
            zoo = form.cleaned_data['zoo']
            folder_upload = form.cleaned_data.get('folder_upload', False)
            
            # Get files from request.FILES
            files = request.FILES.getlist('audio_files')
            
            if not files:
                messages.error(request, "No files were selected for upload.")
                return redirect('upload_audio')
            
            # Count valid files
            valid_files = [f for f in files if f.name.lower().endswith('.wav')]
            if not valid_files:
                messages.error(request, "No valid .wav files were selected. Please upload .wav files only.")
                return redirect('upload_audio')
            
            # Track upload statistics
            total_files = len(files)
            valid_count = len(valid_files)
            invalid_count = total_files - valid_count
            processed_count = 0
            
            # Process each valid file
            for audio_file in valid_files:
                try:
                    # Create a new OriginalAudioFile instance
                    try:
                        admin_profile = AdminProfile.objects.get(user=request.user)
                    except AdminProfile.DoesNotExist:
                        # Create admin profile if it doesn't exist
                        admin_profile = AdminProfile.objects.create(user=request.user)
                        
                    original_audio = OriginalAudioFile(
                        audio_file=audio_file,
                        audio_file_name=audio_file.name,
                        animal_type=animal_type,
                        zoo=zoo,
                        upload_date=now(),
                        uploaded_by=admin_profile
                    )
                    original_audio.save()
                    
                    # Create a database entry with Pending status
                    db_entry = Database(
                        audio_file=original_audio,
                        status='Pending'
                    )
                    db_entry.save()
                    
                    # Create initial processing log
                    ProcessingLog.objects.create(
                        audio_file=original_audio,
                        timestamp=now(),
                        level='INFO',
                        message=f'Audio file "{audio_file.name}" uploaded successfully.'
                    )
                    
                    # Update metadata
                    update_audio_metadata(original_audio)
                    
                    processed_count += 1
                    
                except Exception as e:
                    logging.error(f"Error uploading file {audio_file.name}: {str(e)}")
                    messages.error(request, f"Error uploading {audio_file.name}: {str(e)}")
            
            # Generate success message
            if processed_count > 0:
                messages.success(request, f"Successfully uploaded {processed_count} audio files. {invalid_count} files were skipped (not .wav format).")
                
                # Trigger processing if there are valid files
                process_pending_audio_files()
            else:
                messages.warning(request, "No files were successfully uploaded. Please try again.")
            
            return redirect('upload_audio')
        else:
            messages.error(request, "Form validation failed. Please check your inputs.")
    else:
        form = AudioUploadForm()
    
    context = {
        'form': form,
        'audio_files': audio_files
    }
    
    return render(request, 'admin_template/upload_audio.html', context)


@login_required
def process_audio_files(request):
    """
    View for processing pending audio files
    """
    if request.user.user_type != '1':  # Restrict access to admin only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')
    
    # Get pending files count before processing
    pending_count = Database.objects.filter(status='Pending').count()
    
    if pending_count == 0:
        messages.info(request, "No pending audio files to process.")
        return redirect('admin_home')
    
    try:
        # Process all pending audio files
        processed_count, failed_count = process_pending_audio_files()
        
        if processed_count > 0:
            messages.success(request, f"Successfully processed {processed_count} audio files.")
        
        if failed_count > 0:
            messages.warning(request, f"Failed to process {failed_count} audio files. Check logs for details.")
            
    except Exception as e:
        messages.error(request, f"Error during batch processing: {str(e)}")
    
    return redirect('admin_home')


@login_required
def manage_staff(request):
    if request.user.user_type != '1':  # Restrict access to admin only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')

    staff_users = CustomUser.objects.filter(user_type='2')  # Fetch all staff users
    return render(request, "admin_template/manage_staff.html", {"staff_users": staff_users})

@login_required
def view_spectrograms(request, file_id):
    if not request.user.is_authenticated or request.user.user_type != '1':
        return redirect('login')
    
    # Get the audio file
    audio_file = get_object_or_404(OriginalAudioFile, pk=file_id)
    
    # Get all spectrograms for this file
    spectrograms = Spectrogram.objects.filter(audio_file=audio_file)
    
    # Get all detected noise clips
    detected_noises = DetectedNoiseAudioFile.objects.filter(original_audio=audio_file)
    
    # Get processing logs
    processing_logs = ProcessingLog.objects.filter(audio_file=audio_file).order_by('-timestamp')
    
    # Get processing status
    processing_status = Database.objects.filter(original_audio=audio_file).first()
    
    # Calculate total impulses
    total_impulses = sum(noise.saw_count for noise in detected_noises)
    
    # Prepare chart data
    chart_labels = []
    chart_data = []
    for noise in detected_noises:
        if hasattr(noise.start_time, 'strftime'):
            # If it's a datetime.time object
            chart_labels.append(noise.start_time.strftime("%H:%M:%S"))
        else:
            # If it's a float (seconds)
            hours, remainder = divmod(int(noise.start_time), 3600)
            minutes, seconds = divmod(remainder, 60)
            chart_labels.append(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        chart_data.append(noise.saw_count)
    
    # Prepare data for the template
    clips_data = []
    for noise in detected_noises:
        # Find the corresponding spectrogram if it exists
        # Handle both datetime.time and float formats for start/end times
        matching_specs = []
        for spec in spectrograms:
            # Convert times to seconds for comparison if needed
            noise_start = noise.start_time
            noise_end = noise.end_time
            spec_start = spec.clip_start_time
            spec_end = spec.clip_end_time
            
            # Convert datetime.time to seconds if needed
            if hasattr(noise_start, 'hour'):
                noise_start = noise_start.hour * 3600 + noise_start.minute * 60 + noise_start.second + noise_start.microsecond/1000000
            if hasattr(noise_end, 'hour'):
                noise_end = noise_end.hour * 3600 + noise_end.minute * 60 + noise_end.second + noise_end.microsecond/1000000
            if hasattr(spec_start, 'hour'):
                spec_start = spec_start.hour * 3600 + spec_start.minute * 60 + spec_start.second + spec_start.microsecond/1000000
            if hasattr(spec_end, 'hour'):
                spec_end = spec_end.hour * 3600 + spec_end.minute * 60 + spec_end.second + spec_end.microsecond/1000000
            
            # Compare as floats
            if abs(float(noise_start) - float(spec_start)) < 0.1 and abs(float(noise_end) - float(spec_end)) < 0.1:
                matching_specs.append(spec)
        
        spec = matching_specs[0] if matching_specs else None
        
        # Format display times
        if hasattr(noise.start_time, 'strftime'):
            display_start = noise.start_time.strftime("%H:%M:%S")
            display_end = noise.end_time.strftime("%H:%M:%S")
        else:
            # Convert seconds to formatted time string
            start_hours, start_remainder = divmod(int(noise.start_time), 3600)
            start_minutes, start_seconds = divmod(start_remainder, 60)
            display_start = f"{start_hours:02d}:{start_minutes:02d}:{start_seconds:02d}"
            
            end_hours, end_remainder = divmod(int(noise.end_time), 3600)
            end_minutes, end_seconds = divmod(end_remainder, 60)
            display_end = f"{end_hours:02d}:{end_minutes:02d}:{end_seconds:02d}"
        
        clips_data.append({
            'audio_clip': noise,
            'spectrogram': spec,
            'start_time': noise.start_time,
            'end_time': noise.end_time,
            'display_start': display_start,
            'display_end': display_end
        })
    
    # Get the full audio spectrogram if it exists
    full_spectrogram = spectrograms.filter(is_full_audio=True).first()
    
    context = {
        'audio_file': audio_file,
        'clips_data': clips_data,
        'full_spectrogram': full_spectrogram,
        'processing_logs': processing_logs,
        'processing_status': processing_status,
        'detected_noises': detected_noises,
        'total_impulses': total_impulses,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data)
    }
    
    return render(request, 'admin_template/view_spectrograms.html', context)

@login_required
def generate_excel_report(request, file_id=None):
    """
    View for manually generating Excel reports for processed audio files
    """
    if request.user.user_type not in ['1', '2']:  # Restrict access to admin and staff
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')
    
    try:
        if file_id:
            # Generate Excel for a specific file
            from .excel_generator import generate_excel_report_for_processed_file
            audio_file = OriginalAudioFile.objects.get(pk=file_id)
            
            # Check if the file has been processed
            db_entry = audio_file.database_entry.first()
            if not db_entry or db_entry.status != 'Processed':
                messages.warning(request, f"Cannot generate Excel report: File '{audio_file.audio_file_name}' is not fully processed.")
                return redirect('admin_home')
            
            excel_path = generate_excel_report_for_processed_file(file_id)
            if excel_path:
                messages.success(request, f"Excel report for '{audio_file.audio_file_name}' generated successfully.")
            else:
                messages.error(request, f"Failed to generate Excel report for '{audio_file.audio_file_name}'.")
        else:
            # Generate Excel for all processed files without Excel reports
            from .excel_generator import generate_excel_reports_for_processed_files
            success_count, failed_count = generate_excel_reports_for_processed_files()
            
            if success_count > 0:
                messages.success(request, f"Successfully generated {success_count} Excel reports.")
            
            if failed_count > 0:
                messages.warning(request, f"Failed to generate {failed_count} Excel reports. Check logs for details.")
            
            if success_count == 0 and failed_count == 0:
                messages.info(request, "No files need Excel reports generated.")
    
    except Exception as e:
        messages.error(request, f"Error generating Excel reports: {str(e)}")
    
    # Redirect back to the referring page or admin home
    return redirect(request.META.get('HTTP_REFERER', 'admin_home'))