from django.urls import path
from . import views

urlpatterns = [
    path('tasks/',views.tasks, name='tasks'),
    path('addtask/',views.addtask, name='addtask'),
    path('update_status/<int:task_id>/<str:new_status>/', views.update_status, name='update_status'),
    path('delete_task/<int:task_id>/',views.delete_task,name='delete_task'),
    path('edit_task/<int:task_id>/', views.edit_task, name='edit_task'),
]