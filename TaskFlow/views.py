from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from tasks.models import Task
def home(request):
    return render(request, 'index.html')

@login_required(login_url='login')
def tasks(request):
    pending_tasks = Task.objects.filter(status='Pending').order_by('deadline')
    in_progress_tasks = Task.objects.filter(status='In Progress')
    completed_tasks = Task.objects.filter(status='Completed')
    contex = {
        'tasks':pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
    }
    return render(request, 'tasks.html',contex)

@login_required(login_url='login')
def dashboard(request):
    tasks = Task.objects.filter(status = 'Pending')
    contex = {
        'tasks':tasks,
    }
    return render(request, 'dashboard.html',contex)

def register(request):
    if request.method == 'POST':
        uname = request.POST.get('username')
        role = request.POST.get('role')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not uname or not email or not password:
            messages.error(request, 'Please fill out all required fields')
            return render(request, 'signup.html')

        if not role:
            messages.error(request, 'Please select a role')
            return render(request, 'signup.html')

        allowed_roles = {'student', 'teacher', 'corporate', 'entrepreneur'}
        if role not in allowed_roles:
            messages.error(request, 'Invalid role selected')
            return render(request, 'signup.html')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'signup.html')

        if User.objects.filter(username=uname).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'signup.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'signup.html')

        user = User.objects.create_user(username=uname, email=email, password=password)
        user.first_name = role
        user.save()

        user_auth = authenticate(request, username=uname, password=password)
        if user_auth is not None:
            auth_login(request, user_auth)
            messages.success(request, f"Welcome, {uname}! Registration successful")
            return redirect('dashboard')
        else:
            messages.error(request, 'Registration succeeded but automatic login failed. Please log in.')
            return redirect('login')

    return render(request,'signup.html')

def login(request):
    if request.method == 'POST':
        uname = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=uname, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'login.html')

    return render(request, 'login.html')


@login_required(login_url='login')
def settings(request):
    return render(request, 'settings.html')


@login_required(login_url='login')
def logout(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('home')

@login_required(login_url='login')
def analytics(request):
    all_tasks = Task.objects.all()
    pending_tasks = all_tasks.filter(status='pending')
    in_progress_tasks = all_tasks.filter(status='in_progress')
    completed_tasks = all_tasks.filter(status='completed')
    
    total_tasks = all_tasks.count()
    completed_count = completed_tasks.count()
    in_progress_count = in_progress_tasks.count()
    pending_count = pending_tasks.count()
    
    completion_percentage = (completed_count / total_tasks * 100) if total_tasks > 0 else 0
    
    context = {
        'total_tasks': total_tasks,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'pending_count': pending_count,
        'completion_percentage': round(completion_percentage, 1),
    }
    return render(request, 'analytics.html', context)
