# Generated by Django 5.0.6 on 2024-07-17 13:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0045_remove_restockrequest_quantity'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='restockrequest',
            name='approved_by',
        ),
    ]
