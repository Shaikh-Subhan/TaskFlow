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
        Algorithm:
        1. Get all pending tasks for the user sorted by deadline (urgent first) and priority
        2. Get user's daily available time
        3. For each day starting from today, allocate tasks based on available time
        4. If a task won't fit in current day, reschedule to next day
        5. Respect deadline constraints - don't schedule after deadline
        """
        from django.db.models import Case, When, Value, IntegerField
        today = datetime.now().date()
        
        # Get or create user profile
        try:
            profile = user.profile
        except:
            profile = UserProfile.objects.create(user=user)
        
        available_minutes_per_day = int(profile.available_hours_per_day * 60)
        
        if force_reschedule:
            # Clear scheduled_date for all Pending tasks so they are recalculated
            cls.objects.filter(user=user, status='Pending').update(scheduled_date=None)

        # 1. Pre-fill daily_schedule with time from tasks that are ALREADY scheduled for today or future
        already_scheduled = cls.objects.filter(
            user=user,
            status__in=['Pending', 'In Progress'],
            scheduled_date__isnull=False,
            scheduled_date__gte=today
        )
        
        daily_schedule = {}
        for t in already_scheduled:
            if t.scheduled_date not in daily_schedule:
                daily_schedule[t.scheduled_date] = 0
            daily_schedule[t.scheduled_date] += t.duration
        
        # 2. Get all pending tasks that STILL need scheduling
        # Use Case/When to properly sort Priority: High -> Medium -> Low
        pending_tasks = cls.objects.filter(
            user=user, 
            status='Pending',
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
            
            # Start searching from today
            current_date = today
            # Try to find a day with available time
            while True:
                # If we breached the deadline and it's a hard deadline, FORCE it onto the deadline
                if current_date > deadline and task.is_hard_deadline:
                    task.scheduled_date = deadline
                    scheduled = True
                    break
                    
                # Initialize daily time if not exists
                if current_date not in daily_schedule:
                    daily_schedule[current_date] = 0
                
                # Check if task fits in current day
                used_time = daily_schedule[current_date]
                if used_time + task_duration <= available_minutes_per_day:
                    # Schedule task for this day
                    task.scheduled_date = current_date
                    scheduled = True
                    break
                else:
                    # If it doesn't fit, but today IS the deadline and it's a hard deadline, FORCE it
                    if current_date == deadline and task.is_hard_deadline:
                        task.scheduled_date = deadline
                        scheduled = True
                        break
                    
                    # Otherwise, move to next day (flexible tasks push past deadline if needed)
                    current_date += timedelta(days=1)
            
            task.save(update_fields=['scheduled_date'])
            if task.scheduled_date not in daily_schedule:
                daily_schedule[task.scheduled_date] = 0
            daily_schedule[task.scheduled_date] += task_duration
        
        return True
    
    @classmethod
    def get_today_schedule(cls, user):
        """Get today's scheduled tasks with time breakdown"""
        today = datetime.now().date()
        
        try:
            profile = user.profile
        except:
            profile = UserProfile.objects.create(user=user)
        
        available_minutes = int(profile.available_hours_per_day * 60)
        
        # Get tasks scheduled for today
        today_tasks = cls.objects.filter(
            user=user,
            scheduled_date=today,
            status__in=['Pending', 'In Progress']
        ).order_by('-priority')
        
        # Calculate time metrics
        total_duration = sum(task.duration for task in today_tasks)
        tasks_count = today_tasks.count()
        available_hours = profile.available_hours_per_day
        used_time = total_duration
        remaining_minutes = available_minutes - total_duration
        
        return {
            'tasks': today_tasks,
            'available_minutes': available_minutes,
            'available_hours': available_hours,
            'used_minutes': used_time,
            'used_hours': round(used_time / 60, 2),
            'remaining_minutes': remaining_minutes,
            'remaining_hours': round(remaining_minutes / 60, 2),
            'tasks_count': tasks_count,
            'is_overbooked': remaining_minutes < 0,
            'overbooked_minutes': abs(remaining_minutes) if remaining_minutes < 0 else 0,
        }
