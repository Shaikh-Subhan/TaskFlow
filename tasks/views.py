from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction

from .models import Task

# Define valid status constants
VALID_STATUSES = ('Pending', 'In Progress', 'Completed')

@login_required(login_url='login')
def addtask(request):
    """Create a new task for the current user"""
    if request.method == "POST":
        task_name = request.POST.get('task')
        task_priority = request.POST.get('priority')
        task_deadline = request.POST.get('deadline') or None
        task_duration = int(request.POST.get('duration') or 30)
        
        # Create task efficiently
        Task.objects.create(
            user=request.user,
            task=task_name,
            priority=task_priority,
            deadline=task_deadline,
            duration=task_duration
        )
        
        # Schedule all pending tasks for the user after creating new task
        Task.schedule_tasks(request.user)
        
        return redirect('tasks') 
    return redirect('tasks')

@login_required(login_url='login')
def update_status(request, task_id, new_status):
    """Update task status with timestamp tracking"""
    if new_status not in VALID_STATUSES:
        return redirect('tasks')
    
    # Get task (filtered by user for security)
    task = get_object_or_404(Task, id=task_id, user=request.user)
    
    # Use transaction for atomic update
    with transaction.atomic():
        task.status = new_status
        task.started_at = timezone.now() if new_status == 'In Progress' else None
        task.save(update_fields=['status', 'started_at', 'updated_at'])
    
    # Redirect to appropriate tab
    tab_map = {
        'In Progress': '#progress-tab',
        'Completed': '#completed-tab',
        'Pending': '#pending-tab',
    }
    return redirect(reverse('tasks') + tab_map.get(new_status, ''))

@login_required(login_url='login')
def delete_task(request, task_id):
    """Delete a task (user-specific)"""
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.delete()
    return redirect('tasks')

@login_required(login_url='login')
def edit_task(request, task_id):
    """Edit task details"""
    if request.method == "POST":
        task = get_object_or_404(Task, id=task_id, user=request.user)
        
        # Update fields
        task.task = request.POST.get('task')
        task.priority = request.POST.get('priority')
        task.duration = int(request.POST.get('duration') or task.duration)
        new_deadline = request.POST.get('deadline')
        
        if new_deadline:
            task.deadline = new_deadline
        
        # Optimized save - only update changed fields
        task.save(update_fields=['task', 'priority', 'duration', 'deadline', 'updated_at'])
        return redirect('tasks')
        
    return redirect('tasks')