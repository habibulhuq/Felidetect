from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
import json
import os
from vocalization_management_app.models import CustomUser, Staffs, AudioFile, DetectedSound, Feedback

def staff_home(request):
    staff = Staffs.objects.get(admin=request.user.id)
    audio_files = AudioFile.objects.filter(staff_id=staff.id)
    detected_sounds = DetectedSound.objects.filter(audio_file__in=audio_files)
    
    context = {
        "audio_files_count": audio_files.count(),
        "detected_sounds_count": detected_sounds.count(),
        "feedback_count": Feedback.objects.filter(staff_id=staff.id).count(),
    }
    return render(request, "staff_template/staff_home_template.html", context)

def staff_upload_audio(request):
    if request.method == "POST":
        audio_file = request.FILES['audio_file']
        fs = FileSystemStorage()
        filename = fs.save(audio_file.name, audio_file)
        uploaded_file_url = fs.url(filename)
        
        staff = Staffs.objects.get(admin=request.user.id)
        AudioFile.objects.create(staff_id=staff, file_name=filename, file_url=uploaded_file_url)
        
        messages.success(request, "Audio file uploaded successfully.")
        return redirect('staff_upload_audio')
    return render(request, "staff_template/upload_audio_template.html")

def staff_detect_sounds(request):
    audio_files = AudioFile.objects.filter(staff_id=request.user.id)
    context = {
        "audio_files": audio_files
    }
    return render(request, "staff_template/detect_sounds_template.html", context)

# @csrf_exempt
# def run_detection(request):
#     audio_file_id = request.POST.get('audio_file_id')
#     audio_file = AudioFile.objects.get(id=audio_file_id)
    
#     # Run detection logic here (pseudo code)
#     # detected_sounds = run_detection_algorithm(audio_file.file_url)
    
#     for sound in detected_sounds:
#         DetectedSound.objects.create(audio_file=audio_file, start_time=sound['start_time'], end_time=sound['end_time'], sound_type=sound['sound_type'])
    
#     return JsonResponse({"status": "success"})

def staff_verify_sounds(request):
    detected_sounds = DetectedSound.objects.filter(audio_file__staff_id=request.user.id)
    context = {
        "detected_sounds": detected_sounds
    }
    return render(request, "staff_template/verify_sounds_template.html", context)

@csrf_exempt
def update_sound_verification(request):
    sound_id = request.POST.get('sound_id')
    sound_type = request.POST.get('sound_type')
    
    detected_sound = DetectedSound.objects.get(id=sound_id)
    detected_sound.sound_type = sound_type
    detected_sound.save()
    
    return JsonResponse({"status": "success"})

def staff_feedback(request):
    staff = Staffs.objects.get(admin=request.user.id)
    feedback_data = Feedback.objects.filter(staff_id=staff)
    context = {
        "feedback_data": feedback_data
    }
    return render(request, "staff_template/staff_feedback_template.html", context)

def staff_feedback_save(request):
    if request.method == "POST":
        feedback_message = request.POST.get('feedback_message')
        staff = Staffs.objects.get(admin=request.user.id)
        
        Feedback.objects.create(staff_id=staff, feedback=feedback_message)
        messages.success(request, "Feedback submitted successfully.")
        return redirect('staff_feedback')
    return redirect('staff_feedback')

def staff_profile(request):
    user = CustomUser.objects.get(id=request.user.id)
    staff = Staffs.objects.get(admin=user)
    context = {
        "user": user,
        "staff": staff
    }
    return render(request, 'staff_template/staff_profile.html', context)

def staff_profile_update(request):
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        address = request.POST.get('address')
        
        try:
            customuser = CustomUser.objects.get(id=request.user.id)
            customuser.first_name = first_name
            customuser.last_name = last_name
            if password:
                customuser.set_password(password)
            customuser.save()
            
            staff = Staffs.objects.get(admin=customuser.id)
            staff.address = address
            staff.save()
            
            messages.success(request, "Profile updated successfully.")
            return redirect('staff_profile')
        except:
            messages.error(request, "Failed to update profile.")
            return redirect('staff_profile')
    return redirect('staff_profile')
