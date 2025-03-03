# Generated by Django 3.1.7 on 2021-05-21 10:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_auto_20210520_1150'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userdetails',
            name='date_of_birth',
        ),
        migrations.RemoveField(
            model_name='userdetails',
            name='gender',
        ),
        migrations.CreateModel(
            name='UserDetailPercentage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Updated At')),
                ('updated_by', models.IntegerField(blank=True, null=True, verbose_name='Updated by')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Is Deleted')),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('basic_detail', models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Basic Detail Percentage')),
                ('climbing_detail', models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Climbing Detail Percentage')),
                ('biometric_detail', models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Biometric Detail Percentage')),
                ('overall_detail', models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Overall Detail Percentage')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user_detail_percentage', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'UserDetailPercentage',
                'verbose_name_plural': 'UserDetailPercentages',
            },
        ),
        migrations.CreateModel(
            name='UserBiometricData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Updated At')),
                ('updated_by', models.IntegerField(blank=True, null=True, verbose_name='Updated by')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Is Deleted')),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('height', models.FloatField(null=True, verbose_name='Height (in inch)')),
                ('wingspan', models.FloatField(null=True, verbose_name='Wingspan (in inch)')),
                ('ape_index', models.FloatField(null=True, verbose_name='Ape Index')),
                ('gender', models.IntegerField(choices=[(0, 'Not Selected'), (1, 'Male'), (2, 'Female'), (3, 'Transgender')], default=0, verbose_name='Gender')),
                ('birthday', models.DateField(null=True, verbose_name='Birthday')),
                ('weight', models.FloatField(null=True, verbose_name='Wingspan (in lbs)')),
                ('shoe_size', models.IntegerField(null=True, verbose_name='Shoe Size (Us)')),
                ('hand_size', models.IntegerField(null=True, verbose_name='Shoe Size (in inch)')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user_biometric', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'UserBiometricData',
                'verbose_name_plural': 'UserBiometricDatas',
            },
        ),
    ]
