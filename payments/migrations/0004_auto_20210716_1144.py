# Generated by Django 3.1.7 on 2021-07-16 11:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0003_transaction'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='customersubscription',
            options={'verbose_name': 'CustomerSubscription', 'verbose_name_plural': 'CustomerSubscriptions'},
        ),
        migrations.AlterModelOptions(
            name='transaction',
            options={'verbose_name': 'Transaction', 'verbose_name_plural': 'Transactions'},
        ),
        migrations.AlterIndexTogether(
            name='customersubscription',
            index_together=set(),
        ),
        migrations.AlterIndexTogether(
            name='transaction',
            index_together=set(),
        ),
    ]
