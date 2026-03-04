from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.db.models import Sum, Q, Count
from datetime import datetime, timedelta

from tasks.models import Task

# Constants
ALLOWED_ROLES = {'student', 'teacher', 'corporate', 'entrepreneur'}
TASK_STATUSES = ('Pending', 'In Progress', 'Completed')

def home(request):
    return render(request, 'index.html')

def get_user_task_stats(user):
    """Get task statistics for a user - optimized with single query"""
    stats = Task.objects.filter(user=user).aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='Pending')),
        in_progress=Count('id', filter=Q(status='In Progress')),
        completed=Count('id', filter=Q(status='Completed')),
        total_duration=Sum('duration', filter=Q(status='Completed')) or 0,
    )
    return {
        'total_tasks': stats['total'],
        'pending_count': stats['pending'],
        'in_progress_count': stats['in_progress'],
        'completed_count': stats['completed'],
        'total_time_minutes': stats['total_duration'],
    }

@login_required(login_url='login')
def tasks(request):
    """Get all user tasks with optional search filter"""
    search_query = request.GET.get('search', '').strip()
    user_tasks = Task.objects.filter(user=request.user)
    
    # Apply search filter if provided
    if search_query:
        user_tasks = user_tasks.filter(Q(task__icontains=search_query) | Q(discription__icontains=search_query))
    
    # Split by status in application layer (more efficient than separate queries)
    pending_tasks = user_tasks.filter(status='Pending').order_by('deadline')
    in_progress_tasks = user_tasks.filter(status='In Progress')
    completed_tasks = user_tasks.filter(status='Completed')
    
    context = {
        'tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'search_query': search_query,
    }
    return render(request, 'tasks.html', context)

@login_required(login_url='login')
def dashboard(request):
    """Get dashboard data for current user"""
    user_tasks = Task.objects.filter(user=request.user)
    stats = get_user_task_stats(request.user)
    
    # Get specific task querysets
    pending_tasks = user_tasks.filter(status='Pending')
    completed_tasks = user_tasks.filter(status='Completed')
    
    # Get high priority tasks
    high_priority_tasks = pending_tasks.filter(priority='High').order_by('deadline')[:5]
    
    # Get upcoming tasks (next 7 days)
    today = datetime.now().date()
    upcoming_tasks = pending_tasks.filter(
        deadline__gte=today,
        deadline__lte=today + timedelta(days=7)
    ).order_by('deadline')
    
    # Get priority breakdown for pending tasks
    priority_stats = pending_tasks.values('priority').annotate(count=Count('id'))
    priority_breakdown = {
        'High': next((p['count'] for p in priority_stats if p['priority'] == 'High'), 0),
        'Medium': next((p['count'] for p in priority_stats if p['priority'] == 'Medium'), 0),
        'Low': next((p['count'] for p in priority_stats if p['priority'] == 'Low'), 0),
    }
    
    # Calculate completion percentage
    total = stats['total_tasks']
    completion_percentage = (stats['completed_count'] / total * 100) if total > 0 else 0
    total_time_hours = (stats['total_time_minutes'] or 0) / 60
    
    context = {
        'high_priority_tasks': high_priority_tasks,
        'upcoming_tasks': upcoming_tasks,
        'total_tasks': stats['total_tasks'],
        'pending_count': stats['pending_count'],
        'in_progress_count': stats['in_progress_count'],
        'completed_count': stats['completed_count'],
        'completion_percentage': round(completion_percentage, 1),
        'total_time_hours': round(total_time_hours, 1),
        'high_priority_count': priority_breakdown['High'],
        'medium_priority_count': priority_breakdown['Medium'],
        'low_priority_count': priority_breakdown['Low'],
    }
    return render(request, 'dashboard.html', context)

def validate_registration(uname, email, password, confirm_password, role):
    """Validate registration data"""
    if not uname or not email or not password:
        return 'Please fill out all required fields'
    
    if not role or role not in ALLOWED_ROLES:
        return 'Please select a valid role'
    
    if password != confirm_password:
        return 'Passwords do not match'
    
    if User.objects.filter(username=uname).exists():
        return 'Username already exists'
    
    if User.objects.filter(email=email).exists():
        return 'Email already exists'
    
    return None

def register(request):
    if request.method == 'POST':
        uname = request.POST.get('username')
        role = request.POST.get('role')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        error = validate_registration(uname, email, password, confirm_password, role)
        if error:
            messages.error(request, error)
            return render(request, 'signup.html')

        # Create user
        user = User.objects.create_user(username=uname, email=email, password=password)
        user.first_name = role
        user.save()

        # Authenticate and login
        user_auth = authenticate(request, username=uname, password=password)
        if user_auth is not None:
            auth_login(request, user_auth)
            messages.success(request, f"Welcome, {uname}! Registration successful")
            return redirect('dashboard')
        else:
            messages.error(request, 'Registration succeeded but automatic login failed. Please log in.')
            return redirect('login')

    return render(request, 'signup.html')

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

def get_status_tasks(request, status):
    """Get tasks for a specific status with statistics"""
    stats = get_user_task_stats(request.user)
    user_tasks = Task.objects.filter(user=request.user)
    status_tasks = user_tasks.filter(status=status)
    
    return {
        'tasks': status_tasks,
        'pending_count': stats['pending_count'],
        'in_progress_count': stats['in_progress_count'],
        'completed_count': stats['completed_count'],
        'current_status': status,
    }

@login_required(login_url='login')
def inprogress(request):
    """Show in-progress tasks"""
    context = get_status_tasks(request, 'In Progress')
    return render(request, 'inprogress.html', context)

@login_required(login_url='login')
def completed(request):
    """Show completed tasks"""
    context = get_status_tasks(request, 'Completed')
    return render(request, 'completed.html', context)

@login_required(login_url='login')
def analytics(request):
    """Show analytics for user tasks"""
    stats = get_user_task_stats(request.user)
    total = stats['total_tasks']
    completion_percentage = (stats['completed_count'] / total * 100) if total > 0 else 0
    
    context = {
        'total_tasks': stats['total_tasks'],
        'completed_count': stats['completed_count'],
        'in_progress_count': stats['in_progress_count'],
        'pending_count': stats['pending_count'],
        'completion_percentage': round(completion_percentage, 1),
    }
    return render(request, 'analytics.html', context)
