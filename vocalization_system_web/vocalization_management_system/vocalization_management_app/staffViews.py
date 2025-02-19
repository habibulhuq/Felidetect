from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import OriginalAudioFile, Database, ProcessingLog, StaffProfile, ProcessingLog

@login_required
def staff_home(request):
    if request.user.user_type != '2':  # Restrict access to staff only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')
    
    # Get processing statistics
    total_files = OriginalAudioFile.objects.count()
    processing_files = Database.objects.filter(status='Processing').count()
    processed_files = Database.objects.filter(status='Processed').count()
    
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
        'recent_logs': recent_logs,
        'processing_files_details': processing_files_details,
    }
    
    return render(request, "staff_template/staff_home.html", context)

@login_required
def view_audio_analysis(request):
    if request.user.user_type != '2':  # Restrict access to staff only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')
    return render(request, "staff_template/view_audio_analysis.html")