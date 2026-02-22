from django.shortcuts import render,redirect,get_object_or_404
from . models import Task
from django.urls import reverse
from django.utils import timezone

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

def addtask(request):
    if request.method == "POST":
        task_name = request.POST.get('task')
        task_priority = request.POST.get('priority')
        task_deadline = request.POST.get('deadline')
        task_duration = request.POST.get('duration')

        if task_deadline == '':
            task_deadline = None
        if task_duration == '':
            task_duration = 30
            
        Task.objects.create(
            task=task_name,
            priority=task_priority,
            deadline=task_deadline,
            duration=task_duration
        )
        return redirect('tasks') 
    return redirect('tasks')

def update_status(request, task_id, new_status):
    valid_statuses = ['Pending', 'In Progress', 'Completed']
    if new_status in valid_statuses:
        task = get_object_or_404(Task, id=task_id)
        task.status = new_status
        if new_status == 'In Progress':
            task.started_at = timezone.now()
        else:
            task.started_at = None
        task.save()
        if new_status == 'In Progress':
            return redirect(reverse('tasks') + '#progress-tab')
        elif new_status == 'Completed':
            return redirect(reverse('tasks') + '#completed-tab')
        else:
            return redirect(reverse('tasks') + '#pending-tab')
    return redirect('tasks')

def delete_task(request, task_id):
    task = get_object_or_404(Task,id=task_id)
    task.delete()
    return redirect('tasks')

def edit_task(request, task_id):
    if request.method == "POST":
        task = get_object_or_404(Task, id=task_id)
        task.task = request.POST.get('task')
        task.priority = request.POST.get('priority')
        task.duration = request.POST.get('duration')
        new_deadline = request.POST.get('deadline')
        if new_deadline:
            task.deadline = new_deadline
        task.save()
        return redirect('tasks')
        
    return redirect('tasks')