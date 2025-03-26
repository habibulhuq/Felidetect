from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .tasks import start_background_processor, stop_background_processor, get_processor_status

@login_required
@require_POST
def start_processor(request):
    """
    API endpoint to start the background audio processor
    """
    # Only admin and staff can start the processor
    if request.user.user_type not in ['1', '2']:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    success = start_background_processor()
    
    return JsonResponse({
        'success': success,
        'message': 'Background processor started' if success else 'Background processor is already running',
        'status': get_processor_status()
    })

@login_required
@require_POST
def stop_processor(request):
    """
    API endpoint to stop the background audio processor
    """
    # Only admin and staff can stop the processor
    if request.user.user_type not in ['1', '2']:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    success = stop_background_processor()
    
    return JsonResponse({
        'success': success,
        'message': 'Background processor stopped' if success else 'Background processor is not running',
        'status': get_processor_status()
    })

@login_required
def get_status(request):
    """
    API endpoint to get the current status of the background processor
    """
    # Only admin and staff can view the processor status
    if request.user.user_type not in ['1', '2']:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    from .audio_processing import get_processing_status
    
    status_data = get_processing_status()
    
    return JsonResponse({
        'success': True,
        'data': status_data
    })

@login_required
def get_file_logs(request, file_id):
    """
    API endpoint to get the processing logs for a specific file
    """
    from .models import OriginalAudioFile, ProcessingLog
    
    try:
        # Get the audio file
        audio_file = OriginalAudioFile.objects.get(id=file_id)
        
        # Get the processing logs for this file
        logs = ProcessingLog.objects.filter(audio_file=audio_file).order_by('-timestamp')[:20]
        
        # Format the logs for JSON response
        logs_data = [{
            'id': log.id,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'level': log.level,
            'message': log.message,
            # Include additional metadata for new changes
            'contains_timestamp': any(keyword in log.message.lower() for keyword in ['start=', 'end=', 'duration']),
            'contains_frequency': 'freq=' in log.message.lower(),
            'contains_magnitude': 'mag=' in log.message.lower(),
            'contains_impulses': 'impulses=' in log.message.lower()
        } for log in logs]
        
        return JsonResponse({
            'success': True,
            'data': logs_data
        })
    except OriginalAudioFile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Audio file not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
def get_recent_logs(request):
    """
    API endpoint to get recent processing logs for the admin dashboard
    """
    from .models import ProcessingLog
    
    # Only admin and staff can view the logs
    if request.user.user_type not in ['1', '2']:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    # Get recent logs
    logs = ProcessingLog.objects.select_related('audio_file').order_by('-timestamp')[:20]
    
    # Format the logs for JSON response
    logs_data = [{
        'id': log.id,
        'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'level': log.level,
        'message': log.message,
        'file_name': log.audio_file.audio_file_name if log.audio_file else 'System',
        'file_id': log.audio_file.file_id if log.audio_file else None,
        # Include additional metadata for new changes
        'contains_timestamp': any(keyword in log.message.lower() for keyword in ['start=', 'end=', 'duration']),
        'contains_frequency': 'freq=' in log.message.lower(),
        'contains_magnitude': 'mag=' in log.message.lower(),
        'contains_impulses': 'impulses=' in log.message.lower()
    } for log in logs]
    
    return JsonResponse({
        'success': True,
        'data': logs_data
    })
