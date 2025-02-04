from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import StaffProfile

@login_required
def staff_home(request):
    if request.user.user_type != '2':  # Restrict access to staff only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')
    return render(request, "staff_template/staff_home.html")

@login_required
def view_audio_analysis(request):
    if request.user.user_type != '2':  # Restrict access to staff only
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')
    return render(request, "staff_template/view_audio_analysis.html")