# Generated migration for database optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0007_task_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='priority',
            field=models.CharField(choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], max_length=10, default='Low'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='task',
            name='task',
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='task',
            name='deadline',
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Completed', 'Completed')], db_index=True, default='Pending', max_length=20),
        ),
        migrations.AlterModelOptions(
            name='task',
            options={'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='task',
            index=models.Index(fields=['user', 'status'], name='tasks_task_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='task',
            index=models.Index(fields=['user', 'deadline'], name='tasks_task_user_deadline_idx'),
        ),
    ]
