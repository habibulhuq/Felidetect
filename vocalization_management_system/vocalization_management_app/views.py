from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
import os
import logging
from .audio_processing import update_audio_metadata
from .EmailBackEnd import EmailBackEnd
from .tasks import process_pending_audio_files
import json
from django.utils.safestring import mark_safe
from .models import CustomUser, OriginalAudioFile, DetectedNoiseAudioFile, Spectrogram, Database, ProcessingLog
from .forms import AudioUploadForm

# Create a logger
logger = logging.getLogger(__name__)

def home(request):
    return redirect('login')

def loginPage(request):
    if request.user.is_authenticated:
        if request.user.user_type == '1':
            return redirect('admin_home')
        else:
            return redirect('staff_home')
    return render(request, "login.html")

def doLogin(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        if not username or not password:
            messages.error(request, "Please provide both username and password")
            return redirect('login')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            if user.user_type == '1':  # Admin
                return redirect('admin_home')
            else:  # Staff
                return redirect('staff_home')
        else:
            messages.error(request, "Invalid username or password")
            return redirect('login')
    
    return redirect('login')

def registerPage(request):
    return render(request, 'register.html')  

def doRegister(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        # Check if email is already registered
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect('register')

        # **Set `username` as email to avoid UNIQUE constraint error**
        user = CustomUser.objects.create(
            username=email,
            email=email,
            full_name=full_name,
            password=make_password(password),
            user_type=user_type
        )
        user.save()

        messages.success(request, "Registration successful! You can now log in.")
        return redirect('login')
    else:
        return redirect('register')


def get_user_details(request):
    if request.user.is_authenticated:
        return HttpResponse(f"User: {request.user.email}, User Type: {request.user.user_type}")
    else:
        return HttpResponse("Please Login First")

def logout_user(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('login')

def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in after password change
            messages.success(request, "Your password has been changed successfully!")
            return redirect('staff_home')  # Redirect to staff home
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, "staff_template/change_password.html", {'form': form})

@login_required
def view_extracted_clips(request, file_id=None):
    """
    View to display extracted clips and their spectrograms
    """
    context = {}
    
    if file_id:
        # Get specific file and its clips
        original_file = get_object_or_404(OriginalAudioFile, file_id=file_id)
        context['original_file'] = original_file
        
        # Get full audio spectrogram
        full_spectrogram = original_file.spectrograms.filter(is_full_audio=True).first()
        context['full_spectrogram'] = full_spectrogram
        
        # Get all clip spectrograms for this file
        clip_spectrograms = original_file.spectrograms.filter(
            is_full_audio=False
        ).order_by('clip_start_time')
        
        context['clip_spectrograms'] = clip_spectrograms
        
        # Get processing status
        processing_status = original_file.database_entry.first()
        context['processing_status'] = processing_status
        
    else:
        # Get all processed files
        processed_files = OriginalAudioFile.objects.filter(
            database_entry__status="Processed"
        ).order_by('-upload_date')
        
        context['processed_files'] = processed_files
    
    return render(request, 'staff_template/view_clips.html', context)

@login_required
def view_spectrograms(request, file_id):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get the audio file
    audio_file = get_object_or_404(OriginalAudioFile, pk=file_id)
    
    # Get all spectrograms for this file
    spectrograms = Spectrogram.objects.filter(audio_file=audio_file)
    
    # Get all detected noise clips
    detected_noises = DetectedNoiseAudioFile.objects.filter(original_file=audio_file)
    
    # Get processing logs
    processing_logs = ProcessingLog.objects.filter(audio_file=audio_file).order_by('-timestamp')
    
    # Get processing status
    processing_status = Database.objects.filter(audio_file=audio_file).first()
    
    # Calculate total impulses
    total_impulses = sum(noise.saw_count for noise in detected_noises)
    
    # Check if Excel file exists
    has_excel = bool(audio_file.analysis_excel)
    
    # Prepare chart data for visualization
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
    
    # If Excel file exists, read it to display in the page
    excel_data = None
    if audio_file.analysis_excel:
        try:
            import pandas as pd
            excel_path = audio_file.analysis_excel.path
            excel_data = pd.read_excel(excel_path).to_html(classes='table table-striped', index=False)
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}")
    
    context = {
        'original_file': audio_file,
        'clips_data': clips_data,
        'full_spectrogram': full_spectrogram,
        'processing_logs': processing_logs,
        'processing_status': processing_status,
        'detected_noises': detected_noises,
        'total_impulses': total_impulses,
        'has_excel': has_excel,
        'excel_data': excel_data,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data)
    }
    
    return render(request, 'common/view_spectrograms.html', context)

@login_required
def view_spectrograms_list(request):
    """
    View to display a list of all audio files with their spectrograms
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get all audio files
    audio_files = OriginalAudioFile.objects.all().order_by('-upload_date')
    
    # Get recent processing logs
    recent_logs = ProcessingLog.objects.all().order_by('-timestamp')[:20]
    
    # Handle search and filtering
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    
    if search_query:
        audio_files = audio_files.filter(audio_file_name__icontains=search_query)
    
    if status_filter:
        audio_files = audio_files.filter(database_entry__status=status_filter)
    
    if date_filter:
        # Parse date filter and apply
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d')
            audio_files = audio_files.filter(upload_date__date=date_obj.date())
        except Exception as e:
            logger.error(f"Error parsing date filter: {str(e)}")
    
    context = {
        'audio_files': audio_files,
        'recent_logs': recent_logs,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_filter': date_filter
    }
    
    return render(request, 'common/view_spectrograms.html', context)

@login_required
def view_analysis(request, file_id):
    """
    View to display detailed analysis and Excel data for a specific audio file
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get the audio file
    audio_file = get_object_or_404(OriginalAudioFile, file_id=file_id)
    
    # Get processing status
    processing_status = Database.objects.filter(audio_file=audio_file).first()
    
    # Get all detected noise clips
    detected_noises = DetectedNoiseAudioFile.objects.filter(original_file=audio_file).order_by('start_time')
    
    # Get processing logs
    processing_logs = ProcessingLog.objects.filter(audio_file=audio_file).order_by('-timestamp')
    
    # Calculate total impulses
    total_impulses = sum(noise.saw_count for noise in detected_noises)
    
    # Check if Excel file exists
    has_excel = bool(audio_file.analysis_excel)
    
    # Prepare chart data for visualization
    chart_labels = []
    chart_data = []
    for noise in detected_noises:
        # Format the start time for display
        if hasattr(noise.start_time, 'strftime'):
            # If it's a datetime.time object
            formatted_time = noise.start_time.strftime("%H:%M:%S")
        else:
            # If it's a float (seconds)
            hours, remainder = divmod(int(noise.start_time), 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        chart_labels.append(formatted_time)
        chart_data.append(noise.saw_count)
    
    # If Excel file exists, read it to display in the page
    excel_data = None
    if has_excel:
        try:
            import pandas as pd
            import io
            
            # Read the Excel file into a pandas DataFrame
            excel_file = audio_file.analysis_excel.read()
            df = pd.read_excel(io.BytesIO(excel_file))
            # Convert DataFrame to HTML table
            excel_data = df.to_html(classes='table table-striped', index=False)
        except Exception as e:
            messages.error(request, f"Error reading Excel file: {str(e)}")
    
    context = {
        'original_file': audio_file,
        'processing_status': processing_status,
        'detected_noises': detected_noises,
        'processing_logs': processing_logs,
        'total_impulses': total_impulses,
        'has_excel': has_excel,
        'excel_data': excel_data,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data)
    }
    
    return render(request, 'common/view_analysis.html', context)
    
def view_timelines(request):
    if request.method == 'POST':
        animal_habitat = request.POST['animal_habitat']
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        # TODO: implement timeline generation logic here
        timeline = ''  # placeholder for timeline generation
        return render(request, 'common/view_timelines.html', {'timeline': timeline})
    else:
        animal_habitats = []  # empty list for now
        return render(request, 'common/view_timelines.html', {'animal_habitats': animal_habitats})


def download_excel(request, file_id):
    """
    View to download the Excel analysis file for a specific audio file
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get the audio file
    audio_file = get_object_or_404(OriginalAudioFile, file_id=file_id)
    
    # Check if Excel file exists
    if not audio_file.analysis_excel:
        messages.error(request, "Excel analysis file not found for this audio.")
        return redirect('view_spectrograms', file_id=file_id)
    
    # Prepare the response with the Excel file
    response = HttpResponse(
        audio_file.analysis_excel.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(audio_file.analysis_excel.name)}"'
    
    return response

@login_required
def upload_audio(request):
    """View for uploading audio files"""
    if request.method == 'POST':
        form = AudioUploadForm(request.POST, request.FILES)
        if form.is_valid():
            animal_type = form.cleaned_data['animal_type']
            zoo = form.cleaned_data['zoo']
            uploaded_files = request.FILES.getlist('audio_files')
            
            # Track upload statistics
            upload_stats = {
                'total': len(uploaded_files),
                'successful': 0,
                'failed': 0,
                'invalid_format': 0,
                'file_names': []
            }
            
            for uploaded_file in uploaded_files:
                # Validate file format (.wav only)
                if not uploaded_file.name.lower().endswith('.wav'):
                    upload_stats['invalid_format'] += 1
                    continue
                
                try:
                    # Create a new OriginalAudioFile instance
                    audio_file = OriginalAudioFile()
                    audio_file.audio_file = uploaded_file
                    audio_file.audio_file_name = uploaded_file.name
                    audio_file.animal_type = animal_type
                    if zoo:
                        audio_file.zoo = zoo
                    audio_file.upload_date = timezone.now()
                    audio_file.save()
                    
                    # Create database entry with Pending status
                    database_entry = Database(audio_file=audio_file, status='Pending')
                    database_entry.save()
                    
                    # Update metadata for the file
                    file_path = audio_file.audio_file.path
                    update_audio_metadata(file_path, audio_file)
                    
                    # Track successful upload
                    upload_stats['successful'] += 1
                    upload_stats['file_names'].append(uploaded_file.name)
                except Exception as e:
                    logger.error(f"Error uploading file {uploaded_file.name}: {str(e)}")
                    upload_stats['failed'] += 1
            
            # Create success message with upload statistics
            if upload_stats['successful'] > 0:
                success_message = f"Successfully uploaded {upload_stats['successful']} audio file(s). "
                if upload_stats['invalid_format'] > 0:
                    success_message += f"{upload_stats['invalid_format']} file(s) were skipped (not .wav format). "
                if upload_stats['failed'] > 0:
                    success_message += f"{upload_stats['failed']} file(s) failed to upload due to errors."
                messages.success(request, success_message)
                
                # Automatically process the uploaded files
                process_pending_audio_files()
                
                return redirect('upload_audio')
            else:
                if upload_stats['invalid_format'] > 0:
                    messages.error(request, f"No files were uploaded. {upload_stats['invalid_format']} file(s) were skipped because they were not in .wav format.")
                else:
                    messages.error(request, "No files were uploaded. Please try again.")
    else:
        form = AudioUploadForm()
    
    # Get all uploaded audio files for the current user
    audio_files = OriginalAudioFile.objects.all().order_by('-upload_date')
    
    context = {
        'form': form,
        'audio_files': audio_files,
    }
    return render(request, 'admin_template/upload_audio.html', context)
