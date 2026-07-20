from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages 
from .models import ContactMessage
def home(request):
    return render(request, 'pages/home.html')

def about(request):
    return render(request, 'pages/about.html')

def features(request):
    return render(request, 'pages/features.html')




def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        if not name or not email or not message:
            messages.error(request, "All fields are required")
            return redirect('contact')

        ContactMessage.objects.create(
            name=name,
            email=email,
            message=message
        )

        messages.success(request, "Message sent successfully!")
        return redirect('contact')
    
    return render(request, 'pages/contact.html')

def documentation(request):
    return render(request, 'pages/documentation.html')

def help_page(request):
    return render(request, 'pages/help.html')

def blog(request):
    return render(request, 'pages/blog.html')

def privacy(request):
    return render(request, 'pages/privacy.html')

def terms(request):
    return render(request, 'pages/terms.html')
