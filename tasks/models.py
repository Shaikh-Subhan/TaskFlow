from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import datetime, timedelta

class UserProfile(models.Model):
    """User profile to store time availability and preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    available_hours_per_day = models.FloatField(default=4.0)  # Available working hours per day
    work_start_time = models.TimeField(default='09:00')  # When user starts work
    work_end_time = models.TimeField(default='17:00')  # When user ends work
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile - {self.available_hours_per_day}h/day"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

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
    description = models.CharField(max_length=250, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    duration = models.IntegerField(default=30)  # Duration in minutes
    deadline = models.DateField(null=True, blank=True, db_index=True)
    scheduled_date = models.DateField(null=True, blank=True)  # Date when task is scheduled to be done
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    accumulated_time_seconds = models.IntegerField(default=0)
    is_paused = models.BooleanField(default=False)
    is_hard_deadline = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'deadline']),
        ]

    def __str__(self):
        return self.task
    
    @property
    def duration_hours(self):
        """Duration expressed as hours (float)."""
        return round(self.duration / 60, 1)
    
    def search(self, query):
        """Search task by name or description"""
        return Q(task__icontains=query) | Q(description__icontains=query)
    
    @classmethod
    def schedule_tasks(cls, user, force_reschedule=False):
        """
        Intelligently schedule tasks based on available time and deadlines.
        Handles edge cases like overdue tasks, hard deadlines, and day rollovers.
        """
        from django.db.models import Case, When, Value, IntegerField
        today = datetime.now().date()
        
        try:
            profile = user.profile
        except:
            profile = UserProfile.objects.create(user=user)
        
        available_minutes_per_day = int(profile.available_hours_per_day * 60)
        
        # CRITICAL EDGE CASE 1: Auto-Rollover
        # Any incomplete task (Pending/In Progress) from the PAST MUST have its schedule cleared 
        # so the engine catches it and forces it onto today. Otherwise, they disappear into yesterday.
        cls.objects.filter(
            user=user,
            status__in=['Pending', 'In Progress'],
            scheduled_date__lt=today
        ).update(scheduled_date=None)
        
        if force_reschedule:
            # Wipe all future scheduling to rebuild from scratch
            cls.objects.filter(user=user, status__in=['Pending', 'In Progress']).update(scheduled_date=None)

        # Build daily schedule map of ALREADY scheduled tasks from TODAY onwards
        already_scheduled = cls.objects.filter(
            user=user,
            status__in=['Pending', 'In Progress'],
            scheduled_date__isnull=False,
            scheduled_date__gte=today
        )
        
        daily_schedule = {}
        for t in already_scheduled:
            daily_schedule[t.scheduled_date] = daily_schedule.get(t.scheduled_date, 0) + t.duration
        
        # Grab all the tasks that need computing (including the ones rolled over)
        pending_tasks = cls.objects.filter(
            user=user, 
            status__in=['Pending', 'In Progress'],
            scheduled_date__isnull=True
        ).annotate(
            priority_weight=Case(
                When(priority='High', then=Value(1)),
                When(priority='Medium', then=Value(2)),
                When(priority='Low', then=Value(3)),
                output_field=IntegerField(),
            )
        ).order_by('deadline', 'priority_weight')
        
        for task in pending_tasks:
            task_duration = task.duration  # in minutes
            deadline = task.deadline or (today + timedelta(days=365))  # 1 year default
            
            current_date = today
            while True:
                # CRITICAL EDGE CASE 2: Overdue Hard Deadlines
                # If today is past the deadline, and it's a hard deadline, it failed.
                # The engine MUST force it to TODAY so the user sees it prominently.
                if current_date >= deadline and task.is_hard_deadline:
                    task.scheduled_date = current_date
                    break
                    
                used_time = daily_schedule.get(current_date, 0)
                
                # Check if task perfectly fits in current_date
                if used_time + task_duration <= available_minutes_per_day:
                    task.scheduled_date = current_date
                    break
                else:
                    # It doesn't fit. But if current_date exactly matches the deadline, 
                    # and it's a hard deadline, we FORCE it (causing an Overbook alert).
                    if current_date == deadline and task.is_hard_deadline:
                        task.scheduled_date = current_date
                        break
                    
                    # Otherwise, this flexible task gets bumped to the next day.
                    current_date += timedelta(days=1)
            
            # Save the calculated date back to the database
            task.save(update_fields=['scheduled_date'])
            daily_schedule[task.scheduled_date] = daily_schedule.get(task.scheduled_date, 0) + task_duration
        
        return True
    
    @classmethod
    def get_today_schedule(cls, user):
        """Get today's scheduled tasks with time breakdown"""
        # CRITICAL EDGE CASE 3: Dynamic Rollover Execution
        # By dynamically calling the scheduler here, we guarantee that whenever the user
        # natively opens the app/dashboard tomorrow, all yesterday's tasks instantly roll over.
        cls.schedule_tasks(user)

        today = datetime.now().date()
        
        try:
            profile = user.profile
        except:
            profile = UserProfile.objects.create(user=user)
        
        available_minutes = int(profile.available_hours_per_day * 60)
        
        # Get tasks perfectly scheduled for today
        today_tasks = cls.objects.filter(
            user=user,
            scheduled_date=today,
            status__in=['Pending', 'In Progress']
        ).order_by('-priority')
        
        # Determine duration consumed by locally completed tasks TODAY
        completed_today_tasks = cls.objects.filter(
            user=user,
            scheduled_date=today,
            status='Completed'
        )
        
        # Calculate time metrics strictly
        pending_duration = sum(task.duration for task in today_tasks)
        completed_duration = sum(task.duration for task in completed_today_tasks)
        
        total_assigned_minutes = pending_duration + completed_duration
        
        tasks_count = today_tasks.count()
        available_hours = profile.available_hours_per_day
        remaining_minutes = available_minutes - total_assigned_minutes
        
        return {
            'tasks': today_tasks,
            'available_minutes': available_minutes,
            'available_hours': available_hours,
            'pending_minutes': pending_duration,
            'pending_hours': round(pending_duration / 60, 2),
            'completed_minutes': completed_duration,
            'completed_hours': round(completed_duration / 60, 2),
            'used_minutes': total_assigned_minutes,
            'used_hours': round(total_assigned_minutes / 60, 2),
            'remaining_minutes': remaining_minutes,
            'remaining_hours': round(remaining_minutes / 60, 2),
            'tasks_count': tasks_count,
            'is_overbooked': remaining_minutes < 0,
            'overbooked_minutes': abs(remaining_minutes) if remaining_minutes < 0 else 0,
        }
