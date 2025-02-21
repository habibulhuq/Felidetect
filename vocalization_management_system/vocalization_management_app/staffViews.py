from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import OriginalAudioFile, Database, ProcessingLog, StaffProfile, Spectrogram, DetectedNoiseAudioFile

@login_required
def staff_home(request):
    """
    Staff home view showing recent processing activity and audio files
    """
    # Get counts for dashboard
    total_files = OriginalAudioFile.objects.count()
    processing_files = Database.objects.filter(status='Processing').count()
    processed_files = Database.objects.filter(status='Processed').count()
    failed_files = Database.objects.filter(status='Failed').count()
    
    # Get recent processing logs
    recent_logs = ProcessingLog.objects.select_related('audio_file').order_by('-timestamp')[:10]
    
    # Get files currently being processed
    processing_files_details = Database.objects.filter(
        status='Processing'
    ).select_related('audio_file')
    
    # Get all audio files with their processing status
    audio_files = OriginalAudioFile.objects.prefetch_related(
        'database_entry'
    ).order_by('-upload_date')
    
    context = {
        'page_title': 'Staff Dashboard',
        'total_files': total_files,
        'processing_files': processing_files,
        'processed_files': processed_files,
        'failed_files': failed_files,
        'recent_logs': recent_logs,
        'processing_files_details': processing_files_details,
        'audio_files': audio_files,
    }
    
    return render(request, "staff_template/staff_home.html", context)

@login_required
def view_audio_analysis(request):
    if request.user.user_type != '2':  # Restrict access to staff only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')
    return render(request, "staff_template/view_audio_analysis.html")

@login_required
def view_spectrograms(request, file_id):
    """
    View for displaying spectrograms and classified clips for a specific audio file
    """
    try:
        # Get the original audio file
        audio_file = get_object_or_404(OriginalAudioFile, file_id=file_id)
        
        # Get all spectrograms for this file
        spectrograms = Spectrogram.objects.filter(audio_file=audio_file)
        
        # Get all detected clips (likely matches only)
        detected_clips = DetectedNoiseAudioFile.objects.filter(
            original_file=audio_file
        ).order_by('start_time')
        
        # Get processing logs
        processing_logs = ProcessingLog.objects.filter(
            audio_file=audio_file
        ).order_by('-timestamp')[:10]  # Get last 10 logs
        
        context = {
            'audio_file': audio_file,
            'spectrograms': spectrograms,
            'detected_clips': detected_clips,
            'processing_logs': processing_logs,
            'page_title': 'View Spectrograms'
        }
        
        return render(request, 'staff_template/view_spectrograms.html', context)
        
    except Exception as e:
        messages.error(request, f"Error viewing spectrograms: {str(e)}")
        return redirect('staff_home')