from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from .models import Task
from django.utils.dateparse import parse_datetime, parse_date
from datetime import datetime, time

from datetime import timedelta


# Define valid status constants
VALID_STATUSES = ('Pending', 'In Progress', 'Completed')

@login_required(login_url='login')
def addtask(request):
    if request.method == "POST":
        task_name = request.POST.get('task')
        task_description = request.POST.get('description', '')
        task_priority = request.POST.get('priority')
        task_duration = int(request.POST.get('duration') or 30)
        
        is_hard_deadline = request.POST.get('is_hard_deadline') == 'on'
        
        # --- DEADLINE LOGIC ---
        task_deadline_str = request.POST.get('deadline')
        task_deadline = None
        
        if task_deadline_str:
            parsed_dt = parse_datetime(task_deadline_str)
            if not parsed_dt:
                parsed_d = parse_date(task_deadline_str)
                if parsed_d:
                    parsed_dt = datetime.combine(parsed_d, time(23, 59))
            
            if parsed_dt:
                if timezone.is_naive(parsed_dt):
                    parsed_dt = timezone.make_aware(parsed_dt)
                
                # Throw an error if the date is in the past!
                if parsed_dt < timezone.now():
                    return redirect('tasks')
                
                task_deadline = parsed_dt
        # ----------------------

        Task.objects.create(
            user=request.user,
            task=task_name,
            description=task_description,
            priority=task_priority,
            deadline=task_deadline,
            duration=task_duration,
            is_hard_deadline=is_hard_deadline,
        )
        
        Task.schedule_tasks(request.user)
        
        return redirect('tasks') 
    return redirect('tasks')
@login_required(login_url='login')
def edit_task(request, task_id):
    if request.method == "POST":
        task = get_object_or_404(Task, id=task_id, user=request.user)
        
        task.task = request.POST.get('task')
        task.description = request.POST.get('description', task.description)
        task.priority = request.POST.get('priority')
        task.duration = int(request.POST.get('duration') or task.duration)
        
        task.is_hard_deadline = request.POST.get('is_hard_deadline') == 'on'
        # --- DEADLINE LOGIC ---
        new_deadline_str = request.POST.get('deadline')
        if new_deadline_str:
            parsed_dt = parse_datetime(new_deadline_str)
            if not parsed_dt:
                parsed_d = parse_date(new_deadline_str)
                if parsed_d:
                    parsed_dt = datetime.combine(parsed_d, time(23, 59))
            
            if parsed_dt:
                if timezone.is_naive(parsed_dt):
                    parsed_dt = timezone.make_aware(parsed_dt)
                
                # Throw an error if the date is in the past!
                if parsed_dt < timezone.now():
                    return redirect('tasks')
                
                task.deadline = parsed_dt
        # ----------------------
        
        task.save(update_fields=[
            'task', 'description', 'priority', 'duration', 
            'deadline', 'is_hard_deadline', 'updated_at'
        ])
        
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
        if new_status == 'In Progress':
            if task.status != 'In Progress':
                task.started_at = timezone.now()
                task.is_paused = False
        elif new_status == 'Completed':
            if task.started_at and not task.is_paused:
                delta = timezone.now() - task.started_at
                task.accumulated_time_seconds += int(delta.total_seconds())
                task.started_at = None
            task.is_paused = False
            
        task.status = new_status
        task.save(update_fields=['status', 'started_at', 'accumulated_time_seconds', 'is_paused', 'updated_at'])
    
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
def toggle_pause(request, task_id):
    """Pause or resume an in-progress task."""
    task = get_object_or_404(Task, id=task_id, user=request.user)
    
    if task.status != 'In Progress':
        return redirect(reverse('tasks') + '#progress-tab')
        
    with transaction.atomic():
        if task.is_paused:
            # Resuming
            task.started_at = timezone.now()
            task.is_paused = False
        else:
            # Pausing
            if task.started_at:
                delta = timezone.now() - task.started_at
                task.accumulated_time_seconds += int(delta.total_seconds())
            task.started_at = None
            task.is_paused = True
            
        task.save(update_fields=['started_at', 'accumulated_time_seconds', 'is_paused', 'updated_at'])
        
    return redirect(reverse('tasks') + '#progress-tab')
