from django.shortcuts import render
from tasks.models import Task

def home(request):
    return render(request, 'index.html')

def dashboard(request):
    tasks = Task.objects.filter(is_completed = False)
    contex = {
        'tasks':tasks,
    }
    return render(request, 'dashboard.html',contex)