from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


#signuplogic
def signup_view(request):
    if request.method == 'POST':

        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # 🔴 EMPTY FIELD CHECK
        if not username or not email or not password1 or not password2:
            messages.error(request, "Please fill all fields")
            return redirect('signup')

        # 🔴 USERNAME EXISTS
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('signup')

        # 🔴 EMAIL EXISTS
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect('signup')

        # 🔴 PASSWORD MATCH
        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect('signup')

        # 🔴 PASSWORD LENGTH (IMPORTANT)
        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters")
            return redirect('signup')

        # ✅ CREATE USER
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        login(request, user)

        return render(request, 'accounts/signup.html', {
            "success": True
        })

    return render(request, 'accounts/signup.html')

# loginlogic
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')  # change later
        else:
            messages.error(request, "Invalid credentials")
            return redirect('login')

    return render(request, 'accounts/login.html')

#logoutlogic
def logout_view(request):
    logout(request)
    return redirect('login')
