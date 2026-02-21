from django.shortcuts import render,redirect
from . models import Task

def tasks(request):
    tasks = Task.objects.filter(is_completed = False).order_by('deadline')
    contex = {
        'tasks':tasks,
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
