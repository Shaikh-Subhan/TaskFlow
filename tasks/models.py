from django.db import models

class Task(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    )
    task = models.CharField(max_length=100)
    discription = models.CharField(max_length=250,blank=True)
    priority = models.CharField(max_length=10)
    duration = models.IntegerField(default=30)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.task
