# Generated by Django 3.1.7 on 2021-05-12 06:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gyms', '0002_gymlayout_layoutsection_sectionwall_wallroute'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='gymlayout',
            options={'ordering': ['id'], 'verbose_name': 'GymLayout', 'verbose_name_plural': 'GymLayouts'},
        ),
        migrations.AlterModelOptions(
            name='layoutsection',
            options={'ordering': ['id'], 'verbose_name': 'LayoutSection', 'verbose_name_plural': 'LayoutSections'},
        ),
        migrations.AlterModelOptions(
            name='sectionwall',
            options={'ordering': ['id'], 'verbose_name': 'SectionWall', 'verbose_name_plural': 'SectionWalls'},
        ),
        migrations.AlterModelOptions(
            name='wallroute',
            options={'ordering': ['id'], 'verbose_name': 'WallRoute', 'verbose_name_plural': 'WallRoutes'},
        ),
    ]
