from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import messages
from .EmailBackEnd import EmailBackEnd
from .models import CustomUser
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from .models import OriginalAudioFile

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
def view_spectrograms(request, file_id=None):
    """
    Common view for both admin and staff to visualize spectrograms
    """
    user = request.user
    if file_id:
        audio_file = get_object_or_404(OriginalAudioFile, file_id=file_id)
        
        # Check if user has permission to view this file
        if not (user.user_type == '1' or  # Admin
                (user.user_type == '2' and audio_file.uploaded_by.admin.id == user.staff.admin.id)):  # Staff member's own files
            return HttpResponseForbidden("You don't have permission to view this file.")
        
        # Get processing status
        processing_status = audio_file.database_entry.first()
        
        # Get spectrograms
        spectrograms = audio_file.spectrograms.all()
        
        # Get detected noises
        detected_noises = audio_file.detected_noises.all()
        
        # Get processing logs
        processing_logs = audio_file.processing_logs.all().order_by('-timestamp')
        
        context = {
            'audio_file': audio_file,
            'processing_status': processing_status,
            'spectrograms': spectrograms,
            'detected_noises': detected_noises,
            'processing_logs': processing_logs,
        }
        
        return render(request, 'common/view_spectrograms.html', context)
    else:
        # List view - show all files the user has access to
        if user.user_type == '1':  # Admin
            audio_files = OriginalAudioFile.objects.all()
        else:  # Staff
            audio_files = OriginalAudioFile.objects.filter(uploaded_by=user.staff.admin)
            
        context = {
            'audio_files': audio_files,
        }
        return render(request, 'common/view_spectrograms.html', context)