from django.urls import path
from . import views

urlpatterns = [
    path('tasks/',views.tasks, name='tasks'),
    path('addtask/',views.addtask, name='addtask'),
    path('update_status/<int:task_id>/<str:new_status>/', views.update_status, name='update_status'),
]