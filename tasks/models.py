from django.db import models

class Task(models.Model):
    task = models.CharField(max_length=100)
    discription = models.CharField(max_length=250,blank=True)
    priority = models.CharField(max_length=10)
    duration = models.IntegerField(default=30)
    deadline = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.task
