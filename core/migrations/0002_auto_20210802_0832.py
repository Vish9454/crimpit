# Generated by Django 3.1.7 on 2021-08-02 08:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='expopaymenturl',
            options={'verbose_name': 'Export Payment Url', 'verbose_name_plural': 'Export Payment Urls'},
        ),
        migrations.AlterIndexTogether(
            name='expopaymenturl',
            index_together=set(),
        ),
    ]
