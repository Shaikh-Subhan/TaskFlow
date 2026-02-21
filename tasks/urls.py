from django.urls import path
from . import views

urlpatterns = [
    path('tasks/',views.tasks, name='tasks'),
    path('addtask/',views.addtask, name='addtask')
]