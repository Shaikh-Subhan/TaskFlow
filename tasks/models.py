from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q

class Task(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    )
    PRIORITY_CHOICES = (
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    task = models.CharField(max_length=100, db_index=True)
    discription = models.CharField(max_length=250, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    duration = models.IntegerField(default=30)
    deadline = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'deadline']),
        ]

    def __str__(self):
        return self.task
    
    def search(self, query):
        """Search task by name or description"""
        return Q(task__icontains=query) | Q(discription__icontains=query)
