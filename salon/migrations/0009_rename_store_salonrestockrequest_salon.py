# Generated by Django 5.0.6 on 2024-10-02 10:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('salon', '0008_salonrestockrequest_salonrestockrequestitem'),
    ]

    operations = [
        migrations.RenameField(
            model_name='salonrestockrequest',
            old_name='store',
            new_name='salon',
        ),
    ]