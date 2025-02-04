from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from .models import CustomUser, AdminProfile
from .forms import UserRegistrationForm, AudioUploadForm

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
            return redirect('manage_staff')  # Redirect to staff management page
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
    if request.user.user_type != '1':  # Restrict access to admin only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')

    if request.method == "POST":
        if request.FILES.get('audio_file'):
            audio_file = request.FILES['audio_file']
            fs = FileSystemStorage()
            filename = fs.save(audio_file.name, audio_file)
            messages.success(request, f"File {filename} uploaded successfully!")
        else:
            messages.error(request, "No file selected!")

    return render(request, "admin_template/upload_audio.html")

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