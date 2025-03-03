# Generated by Django 3.1.7 on 2021-05-19 10:16

import accounts.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gyms', '0003_auto_20210512_0619'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreLoadedTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Updated At')),
                ('updated_by', models.IntegerField(blank=True, null=True, verbose_name='Updated by')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Is Deleted')),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('uploaded_template', models.CharField(max_length=255, verbose_name='Uploaded Template')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
            ],
            options={
                'verbose_name': 'PreLoadedTemplate',
                'verbose_name_plural': 'PreLoadedTemplates',
            },
            managers=[
                ('objects', accounts.models.ActiveUserManager()),
                ('all_objects', accounts.models.ActiveObjectsManager()),
            ],
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Updated At')),
                ('updated_by', models.IntegerField(blank=True, null=True, verbose_name='Updated by')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Is Deleted')),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('thumbnail', models.CharField(max_length=255, verbose_name='Thumbnail')),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('start_date', models.DateTimeField(verbose_name='Start Date')),
                ('description', models.CharField(blank=True, max_length=500, null=True, verbose_name='Description')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                ('gym', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gym_event', to='gyms.gymdetails')),
            ],
            options={
                'verbose_name': 'Event',
                'verbose_name_plural': 'Events',
            },
            managers=[
                ('objects', accounts.models.ActiveUserManager()),
                ('all_objects', accounts.models.ActiveObjectsManager()),
            ],
        ),
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Updated At')),
                ('updated_by', models.IntegerField(blank=True, null=True, verbose_name='Updated by')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Is Deleted')),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('banner', models.CharField(max_length=255, verbose_name='Banner')),
                ('template', models.CharField(max_length=255, verbose_name='Template')),
                ('picture', models.CharField(max_length=255, verbose_name='Picture')),
                ('title', models.CharField(max_length=300, verbose_name='Title')),
                ('sub_title', models.CharField(max_length=300, verbose_name='Subtitle')),
                ('priority', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                ('gym', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gym_announcement', to='gyms.gymdetails')),
            ],
            options={
                'verbose_name': 'Announcement',
                'verbose_name_plural': 'Announcements',
            },
            managers=[
                ('objects', accounts.models.ActiveUserManager()),
                ('all_objects', accounts.models.ActiveObjectsManager()),
            ],
        ),
    ]
