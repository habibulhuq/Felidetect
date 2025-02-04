from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse
from django.contrib import messages
from .EmailBackEnd import EmailBackEnd
from .models import CustomUser

def home(request):
    return redirect('login')

def loginPage(request):
    return render(request, 'login.html')

def doLogin(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        user = EmailBackEnd.authenticate(
            request, username=request.POST.get("email"), password=request.POST.get("password")
        )
        if user is not None:
            login(request, user)

            # Redirect based on user type
            if user.user_type == "1":  # Admin
                return redirect("admin_home")
            elif user.user_type == "2":  # Staff
                return redirect("staff_home")
            else:
                messages.error(request, "Invalid Login!")
                return redirect("login")
        else:
            messages.error(request, "Invalid Login Credentials!")
            return redirect("login")
        
def registerPage(request):
    return render(request, 'register.html')  # Create a register.html template

def doRegister(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type')  # "1" for Admin, "2" for Staff

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        # Check if email is already registered
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect('register')

        # Create the user
        user = CustomUser.objects.create(
            email=email,
            full_name=full_name,
            password=make_password(password),  # Hash password
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
    return redirect('login')